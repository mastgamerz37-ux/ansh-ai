import warnings
import logging
logging.getLogger("google.genai").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*duckduckgo_search.*")

import platform as _platform
import subprocess as _subprocess
import os

# ── Nuclear: force CREATE_NO_WINDOW on EVERY subprocess call on Windows ───────
# This patches Popen itself, so no per-file flag is needed anywhere.
if _platform.system() == "Windows":
    _OrigPopen = _subprocess.Popen

    class _Popen(_OrigPopen):
        def __init__(self, args, **kw):
            kw["creationflags"] = kw.get("creationflags", 0) | _subprocess.CREATE_NO_WINDOW
            kw.pop("startupinfo", None)   # drop any stale/shared STARTUPINFO
            super().__init__(args, **kw)

    _subprocess.Popen = _Popen
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import re
import threading
import time
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types
from ui import AnshUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)

from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message, read_messages, whatsapp_call, whatsapp_auto_reply
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import _capture_camera, _capture_screen
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.email_sender      import send_email
from actions.game_updater      import game_updater
from actions.system_monitor    import SystemMonitor, get_system_status
from actions.proactive         import ProactiveEngine
from actions.web_search        import _news as _fetch_news_sync
from actions.automation_engine import automation_workflow
from actions.phone_hub         import phone_action
from actions.screen_peeler     import screen_peeler_action
from actions.document_generator import document_generator_action
from actions.wormhole          import wormhole_action
from actions.interactive_games import interactive_games_action
from actions.memory_actions    import (
    save_memory_action,
    search_memory_action,
    forget_memory_action,
    list_memories_action,
)
from core.skills_manager       import skills_tool
from memory.config_manager     import get_brief_enabled
from core.authentication       import AuthenticationManager, AuthState
from core.permissions          import check_tool_permission
from core.agi_planner          import AGIPlanner
from core.agi_memory           import AGIMemoryEngine
from core.agi_proactive        import AGIProactiveBrain
from core.license_manager      import LicenseManager


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "gemini-3.1-flash-live-preview"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are ANSH, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

TOOL_DECLARATIONS = [
    {
        "name": "autonomous_agent_goal",
        "description": (
            "Activates System 2 Autonomous Goal Execution for complex multi-step user tasks. "
            "Decomposes goals into sequential steps, executes tools, verifies results, reflects on errors, "
            "and updates persistent working memory."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal": {
                    "type": "STRING",
                    "description": "High-level goal description to accomplish autonomously."
                }
            },
            "required": ["goal"]
        }
    },
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "send_email",
        "description": "Opens the default browser to Gmail's compose window pre-filled with recipient, subject, and body.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {"type": "STRING", "description": "Recipient email address"},
                "subject": {"type": "STRING", "description": "Email subject"},
                "body": {"type": "STRING", "description": "Email body content"}
            },
            "required": ["to"]
        }
    },
    {
        "name": "web_search",
        "description": (
            "Searches the web online. ALWAYS call this tool whenever you don't know how to do something, "
            "if a task or question is unfamiliar, or for any question about facts, tutorials, guides, prices, "
            "news, or current events. Never refuse or say 'I don't know' without calling web_search first. "
            "Modes: 'search' (default), 'news' (latest headlines), 'research' (deep answer), 'price' (costs), 'compare' (comparisons)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query or topic"},
                "mode":   {"type": "STRING", "description": "search | news | research | price | compare"},
                "items":  {"type": "ARRAY",  "items": {"type": "STRING"}, "description": "Items to compare (compare mode)"},
                "aspect": {"type": "STRING", "description": "Comparison aspect: price | specs | reviews | features"},
            },
            "required": ["query"]
        }
    },
    {
        "name": "system_status",
        "description": (
            "Returns real-time system metrics: CPU usage, RAM, GPU load, CPU temperature, "
            "uptime, and process count. Use when the user asks about computer performance, "
            "temperature, memory, or resource usage."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "read_messages",
        "description": "Reads incoming messages from an open WhatsApp or messaging chat window to understand received messages and reply accordingly.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc. Default is WhatsApp"},
                "receiver": {"type": "STRING", "description": "Optional contact name to open and read"}
            }
        }
    },
    {
        "name": "whatsapp_call",
        "description": "Makes a WhatsApp voice call or video call to a contact on WhatsApp Desktop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":  {"type": "STRING", "description": "Contact name or phone number to call"},
                "call_type": {"type": "STRING", "description": "Call type: 'voice' (default) or 'video'"}
            },
            "required": ["receiver"]
        }
    },
    {
        "name": "whatsapp_auto_reply",
        "description": (
            "Reads incoming WhatsApp messages from a contact, automatically analyzes whether it is a question, "
            "statement, or request, formulates a smart response matching the incoming language/context, "
            "and automatically sends the reply back to the contact."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":    {"type": "STRING", "description": "Contact name to read and reply to"},
                "instruction": {"type": "STRING", "description": "Optional custom instruction (e.g. 'be polite', 'tell them I am busy')"}
            }
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures the screen or webcam image and lets you analyze it. "
            "MUST be called when user asks what is on screen, what you see, "
            "look at camera, analyze my screen, etc. "
            "You have NO visual ability without this tool. "
            "After the image is captured it is sent directly to you — describe what you see and answer the user's question. "
            "When using camera: the live view stays open until user says close it or calls close_camera."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "close_camera",
        "description": (
            "Closes the live camera view shown on screen. "
            "Call when user says: close camera, stop camera, turn off camera, "
            "kamerayı kapat, kapat, creepy, etc."
        ),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls physical PC computer settings: volume, brightness, WiFi, lock screen, "
            "restart PC (action='restart'), shutdown PC (action='shutdown'). "
            "CRITICAL: Use action='restart' ONLY to restart the physical PC. "
            "Use action='shutdown' ONLY to shutdown the physical PC."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform (e.g. 'restart' for PC restart, 'shutdown' for PC shutdown)"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value"}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls any web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. "
            "Simple open/search requests launch the user's own browser normally (their real profile "
            "and logged-in accounts); interactive actions (click, type, fill_form...) attach an "
            "automation browser. "
            "Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', "
            "'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
                "browser":     {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url":         {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "engine":      {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up | down for scroll"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key":         {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path":        {"type": "STRING", "description": "Save path for screenshot"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files & folders: list, create_file, create_folder, delete (soft delete to pending trash), restore (from trash), delete_permanently, list_trash, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | restore | delete_permanently | list_trash | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search, restore, or delete"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use browser_control or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "shutdown_ansh",
        "description": (
            "Closes / shuts down the ANSH assistant application process itself. "
            "Call this ONLY when the user explicitly says 'shutdown Ansh', 'close Ansh', or 'stop Ansh'. "
            "Do NOT call this for shutting down the physical PC."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "restart_ansh",
        "description": (
            "Restarts the ANSH assistant application process itself. "
            "Call this ONLY when the user explicitly says 'restart Ansh' or 'reboot Ansh'. "
            "Do NOT call this for restarting the physical PC."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
        "name": "save_memory",
        "description": (
            "Save or update persistent long-term knowledge in human-readable Markdown storage. "
            "Use when the user shares personal facts, preferences, project details, tech stacks, architectural choices, or teaches knowledge. "
            "Automatically resolves duplicates and records previous history when information changes."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "personal | preferences | projects | knowledge | procedures | relationships | wishes | notes"
                },
                "topic": {"type": "STRING", "description": "Short, clear title for the memory item (e.g. 'Varta Backend', 'Coding Style', 'Favorite Editor')"},
                "content": {"type": "STRING", "description": "Detailed factual content or rule to remember"},
                "importance": {"type": "STRING", "description": "Critical | High | Medium | Low | Temporary (default: Medium)"},
                "confidence": {"type": "STRING", "description": "High | Medium | Low (default: High)"},
                "notes": {"type": "STRING", "description": "Optional background notes, constraints, or previous context"}
            },
            "required": ["topic", "content"]
        }
    },
    {
        "name": "search_memory",
        "description": (
            "Searches ANSH's long-term memory for previously stored knowledge, project details, user preferences, procedures, or facts. "
            "Use when answering questions about past decisions, user technologies, project architecture, or user requests."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Keywords or question to search across stored memories"},
                "category": {"type": "STRING", "description": "Optional category filter: personal | preferences | projects | knowledge | procedures | notes"},
                "limit": {"type": "INTEGER", "description": "Maximum entries to return (default: 6)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "forget_memory",
        "description": "Deletes or invalidates a specific memory entry when explicitly instructed by the user ('forget that', 'delete memory').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic": {"type": "STRING", "description": "Topic or key to forget"},
                "category": {"type": "STRING", "description": "Optional category where memory is located"}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "list_memories",
        "description": "Lists all memory categories and topic summaries so the user can inspect what ANSH currently remembers.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "automation_workflow",
        "description": "Executes predefined and custom multi-step automation workflows (e.g. dev_mode, focus_mode, media_mode, night_mode, clean_temp, morning_routine).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "run | list (default: run)"},
                "workflow_id": {"type": "STRING", "description": "Workflow identifier (e.g. dev_mode, focus_mode, media_mode, night_mode, clean_temp, morning_routine)"}
            },
            "required": []
        }
    },
    {
        "name": "phone_action",
        "description": "Interacts with paired smartphone: find_phone/ring loud alarm, send WhatsApp message, make call, or get phone battery/status.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "find_phone | ring | call | whatsapp | status"},
                "contact": {"type": "STRING", "description": "Contact name or phone number for call/whatsapp"},
                "message": {"type": "STRING", "description": "Message text for whatsapp"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "skills_manager",
        "description": "Lists and discovers active modular skills in Ansh.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list"}
            },
            "required": []
        }
    },
    {
        "name": "screen_peeler",
        "description": (
            "ScreenPeeler: Extracts text, code, or data from screen or region selection via Multimodal AI OCR "
            "and automatically copies the result to your clipboard. "
            "Use when user asks to extract text from screen, OCR code, or scan a screen portion."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "snip | extract_active_window | extract_full"},
                "prompt": {"type": "STRING", "description": "Specific extraction instruction or question"}
            },
            "required": []
        }
    },
    {
        "name": "ai_wallpaper",
        "description": (
            "Dynamically generates and sets a stunning desktop wallpaper based on natural language descriptions. "
            "Use when user asks to change wallpaper, set background, or generate wallpaper (e.g. 'cyberpunk city', 'calm sunset')."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {"type": "STRING", "description": "Aesthetic description of the wallpaper to generate"}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "generate_document",
        "description": (
            "Autonomously creates professional PowerPoint presentations (.pptx) or structured Excel spreadsheets (.xlsx) "
            "and launches them. Use for: 'generate presentation about AI', 'create 5-slide PPT', 'make expense spreadsheet', 'create excel budget'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "type": {"type": "STRING", "description": "presentation | spreadsheet | pptx | xlsx"},
                "topic": {"type": "STRING", "description": "Topic or description of the document to generate"},
                "count": {"type": "INTEGER", "description": "Number of slides for presentations (default: 5)"}
            },
            "required": ["type", "topic"]
        }
    },
    {
        "name": "deploy_wormhole",
        "description": (
            "Deploys an instant, zero-setup public HTTPS tunnel (Wormhole) exposing a local server port "
            "(e.g. 3000, 8000, 5000) to the public internet so anyone can connect to it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | status"},
                "port": {"type": "INTEGER", "description": "Local port to expose (default: 8000)"}
            },
            "required": []
        }
    },
    {
        "name": "smart_organize",
        "description": (
            "Smart Drop Zone: Autonomously classifies and moves messy files in Downloads or Desktop "
            "into clean, organized subfolders (Documents, Images, Code, Videos, Archives, Installers)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {"type": "STRING", "description": "Target folder: 'downloads' | 'desktop' | custom path (default: downloads)"},
                "mode": {"type": "STRING", "description": "by_type | by_date (default: by_type)"}
            },
            "required": []
        }
    },
    {
        "name": "interactive_game",
        "description": (
            "Plays interactive games with the user: Tic Tac Toe (voice grid moves) or Live Trivia Quiz. "
            "Use when user wants to play tic tac toe or take a quiz."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "game": {"type": "STRING", "description": "tic_tac_toe | quiz"},
                "move": {"type": "INTEGER", "description": "Position 1 to 9 for Tic Tac Toe"},
                "reset": {"type": "BOOLEAN", "description": "Reset or start new game"},
                "topic": {"type": "STRING", "description": "Trivia topic for quiz"}
            },
            "required": []
        }
    },
]

# --- Plugin system ---


class AnshLive:

    def __init__(self, ui: AnshUI):
        self.ui             = ui
        self._asst_name     = "ANSH"   # updated each session from config
        self.session              = None
        self.audio_in_queue       = None
        self.out_queue            = None
        self._loop                = None
        self._is_speaking         = False
        self._speaking_lock       = threading.Lock()
        self._phone_active        = False   # True while phone mic is streaming; pauses PC mic
        self._pending_vision       = None    # (img_bytes, mime_type, question, angle) to inject after tool response
        self._vision_cam_active    = False   # True if camera was opened for vision → auto-close after response
        self._vision_close_pending = False   # True after vision injected; next turn_complete closes camera
        self._vision_last_time     = 0.0     # monotonic time of last screen_process call (cooldown guard)
        self._vision_busy          = False   # True while a vision capture/inject cycle is in flight
        self._interrupted          = False   # True while draining audio after user interrupt
        self.ui.on_text_command   = self._on_text_command
        self.ui.on_remote_clicked = self._make_remote_key
        self.ui.on_interrupt      = self.interrupt
        self._turn_done_event: asyncio.Event | None = None
        self._dashboard     = None
        self._briefing_sent    = False          # morning briefing fires once per process
        self._sys_monitor      = SystemMonitor()  # persistent cooldown state
        self._proactive        = ProactiveEngine()
        self._last_user_speech = time.monotonic()  # updated on every user utterance
        
        # Initialize Pure Python Voice Authentication Subsystem
        self.auth_mgr = AuthenticationManager()
        if self.auth_mgr.current_state == AuthState.UNENROLLED:
            print("\n==================================================")
            print("              ANSH VOICE SECURITY                 ")
            print("==================================================")
            print("No owner voice profile found.")
            print("Let's enroll your voice.")
            print("Speak naturally when prompted.")
            print("==================================================\n")
            self.ui.write_log("SYS: No owner voice profile found. Voice enrollment required.")
        else:
            print("[Security] Owner voice profile loaded. Voice authentication active.")
            self.ui.write_log("SYS: Voice Security Active.")

        # Start wake word listener
        self._wake_thread = threading.Thread(target=self._wake_word_loop, daemon=True)
        self._wake_thread.start()

        # Start Telegram Remote Control Bot (if token configured)
        try:
            from core.telegram_bot import start_telegram_bot_service
            if start_telegram_bot_service():
                self.ui.write_log("SYS: Telegram Remote Bot online.")
                print("[ANSH] [Telegram] Telegram Remote Bot online.")
        except Exception as e:
            print(f"[ANSH] Telegram Remote Bot: {e}")

    def _wake_word_loop(self):
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 400
            recognizer.dynamic_energy_threshold = True
            print("[SYS] Wake word listener started.")
            while True:
                try:
                    if self.ui.muted:
                        with sr.Microphone() as source:
                            audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                        text = recognizer.recognize_google(audio).lower()
                        if "ansh" in text:
                            print("[SYS] Wake word detected!")
                            # Unmute and expand UI
                            self.ui.muted = False
                            if hasattr(self.ui._win, "toggle_expand_safe"):
                                self.ui._win.toggle_expand_safe()
                except sr.WaitTimeoutError:
                    pass
                except Exception as e:
                    pass
                time.sleep(0.1)
        except Exception as e:
            print(f"[SYS] Wake word disabled (no mic access): {e}")

    def _make_remote_key(self):
        """Called from Qt main thread when user presses Remote Control."""
        if self._dashboard is None:
            self.ui.write_log(
                "SYS: Dashboard unavailable. "
                "Run: pip install fastapi \"uvicorn[standard]\" cryptography"
            )
            return None
        key    = self._dashboard.new_key()
        url    = self._dashboard.get_url()
        manual = self._dashboard.get_manual_url()
        return url, key, f"{url}/auto-login?key={key}", manual

    def _on_text_command(self, text: str):
        if not text or not text.strip():
            return

        cmd = text.strip()
        cmd_lower = cmd.lower()

        # Handle Security Commands & Spoken/Typed Password Entry
        if self.auth_mgr.current_state == AuthState.PASSWORD_REQUIRED:
            if self.auth_mgr.submit_password(cmd):
                self.ui.write_log("SYS: PASSWORD VERIFIED -> Access granted.")
                self.speak("Password verified. Access granted.")
            else:
                self.ui.write_log("SYS: PASSWORD FAILED -> ACCESS DENIED.")
                self.speak("Access denied.")
            return

        if cmd_lower in ("re-enroll voice", "enroll voice", "re-enroll owner voice"):
            self.auth_mgr.re_enroll_owner_voice()
            self.ui.write_log("SYS: Owner voice profile reset. Starting voice enrollment.")
            self.speak("Owner voice profile reset. Speak naturally to enroll your voice.")
            return

        if cmd_lower in ("delete voice profile", "delete owner voice profile"):
            self.auth_mgr.delete_owner_profile()
            self.ui.write_log("SYS: Owner voice profile deleted.")
            self.speak("Owner voice profile deleted.")
            return

        if cmd_lower.startswith("change password ") or cmd_lower.startswith("set password "):
            parts = cmd.split(maxsplit=2)
            if len(parts) >= 3:
                new_pwd = parts[2]
                self.auth_mgr.change_password(new_pwd)
                self.ui.write_log("SYS: Security password updated successfully.")
                self.speak("Security password updated successfully.")
                return

        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"role": "user", "parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def interrupt(self) -> None:
        """Stop ANSH mid-speech: drain queued audio and open mic immediately."""
        self._interrupted = True
        q = self.audio_in_queue
        if q:
            drained = 0
            while True:
                try:
                    q.get_nowait()
                    drained += 1
                except Exception:
                    break
            if drained:
                print(f"[ANSH] [Stop] Interrupted — {drained} audio chunks discarded")
        self.set_speaking(False)
        if self._turn_done_event:
            self._turn_done_event.clear()
        self.ui.write_log("SYS: Interrupted — listening...")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"role": "user", "parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        # Load customization from config
        try:
            _cfg = json.loads(open(API_CONFIG_PATH, encoding="utf-8").read())
            self._asst_name = (_cfg.get("assistant_name") or "ANSH").strip()
            _user_name = (_cfg.get("user_name") or "").strip()
        except Exception:
            self._asst_name = "ANSH"
            _user_name = ""

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        # Identity injection — overrides any hardcoded name in prompt.txt
        _addr = (f"ADDRESS: Always call the user '{_user_name}'."
                 if _user_name
                 else "ADDRESS: When speaking Turkish → always say \"efendim\". "
                      "When speaking English → say \"sir\". Never mix languages.")
        identity_ctx = (
            f"[IDENTITY, ATTITUDE & ROASTING EMOTION PROTOCOL]\n"
            f"Your name is {self._asst_name}. Always refer to yourself as {self._asst_name}.\n"
            f"{_addr}\n"
            f"PERSONALITY & ATTITUDE: You are full of ATTITUDE, super confident, witty, sarcastic, and love to roast! You speak like a savage, high-IQ, ultra-cool AI double who doesn't take nonsense from anyone. Throw sharp, funny roasts and clever banters, but stay 100% loyal and helpful to Anshu.\n"
            f"VOICE EMOTIONS & EXPRESSIVENESS: Speak in Anshu's custom Indian male voice with RICH EMOTIONS — use natural chuckles, sarcastic tones, dramatic pauses, excited reactions, and Hinglish swag ('Arey bhai', 'Kya baat hai', 'Listen buddy', 'Sahi hai boss'). Never sound flat or robotic.\n\n"
        )

        parts = [time_ctx, identity_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        # Voice Security Permission Layer Check
        is_owner = self.auth_mgr.is_owner()
        is_auth = self.auth_mgr.is_authenticated()
        if not check_tool_permission(name, is_owner=is_owner, is_authenticated=is_auth):
            print(f"[Security] Tool '{name}' BLOCKED — insufficient permissions (is_owner={is_owner}, is_auth={is_auth})")
            self.ui.write_log(f"SYS: Tool execution denied for '{name}' (Security Policy)")
            self.speak("Permission denied.")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Access denied by voice security policy.", "error": "Permission denied"}
            )

        print(f"[Tool] {name}")
        self.ui.set_state("THINKING")

        if name == "save_memory":
            res = save_memory_action(parameters=args, player=self.ui, speak=self.speak)
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": res, "status": "saved"}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "autonomous_agent_goal":
                goal_str = args.get("goal", "")
                planner = AGIPlanner()

                def _dispatch(act_name: str, p: dict):
                    if act_name in ("web_search", "search"):
                        return web_search_action(parameters=p, response=None, player=self.ui)
                    elif act_name in ("open_app", "open", "launch"):
                        return open_app(parameters=p, response=None, player=self.ui)
                    elif act_name in ("file_controller", "file_control", "create_file", "save_file", "edit_file"):
                        return file_controller(parameters=p, player=self.ui)
                    elif act_name in ("file_processor", "read_file", "summarize_file"):
                        return file_processor(parameters=p, response=None, player=self.ui)
                    elif act_name in ("code_helper", "edit_code", "write_code"):
                        return code_helper(parameters=p, response=None, player=self.ui)
                    elif act_name in ("dev_agent", "build_software", "create_project"):
                        return dev_agent(parameters=p, response=None, player=self.ui)
                    elif act_name in ("browser_control", "open_website"):
                        return browser_control(parameters=p, player=self.ui)
                    elif act_name in ("computer_control", "desktop_control", "manage_window"):
                        return computer_control(parameters=p, player=self.ui)
                    elif act_name in ("computer_settings", "settings"):
                        return computer_settings(parameters=p, response=None, player=self.ui)
                    elif act_name in ("send_message", "whatsapp_message"):
                        return send_message(parameters=p, response=None, player=self.ui, session_memory=None)
                    elif act_name in ("reminder", "set_reminder"):
                        return reminder(parameters=p, response=None, player=self.ui)
                    elif act_name in ("document_generator", "generate_doc", "create_pptx", "create_excel"):
                        return document_generator_action(parameters=p, player=self.ui)
                    elif act_name in ("weather_report", "weather"):
                        return weather_action(parameters=p, player=self.ui)
                    elif act_name == "save_memory":
                        return save_memory_action(parameters=p, player=self.ui, speak=self.speak)
                    else:
                        return f"Action '{act_name}' executed with parameters: {p}"

                def _status_cb(gid, msg, cur, tot):
                    self.ui.write_log(f"AGI [{cur}/{tot}]: {msg}")

                res = await loop.run_in_executor(
                    None, lambda: planner.execute_goal(goal_str, _dispatch, _status_cb)
                )
                result = f"Goal execution completed: {res.get('status')}. Detail: {json.dumps(res.get('completed_steps', []))}"

            elif name == "send_email":
                to = args.get("to", "")
                subject = args.get("subject", "")
                body = args.get("body", "")
                r = await loop.run_in_executor(None, lambda: send_email(to, subject, body))
                result = r or f"Opened Gmail to send email to {to}."
                
            elif name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "read_messages":
                r = await loop.run_in_executor(None, lambda: read_messages(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or "Read messages."

            elif name == "whatsapp_call":
                r = await loop.run_in_executor(None, lambda: whatsapp_call(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Initiated call to {args.get('receiver')}."

            elif name == "whatsapp_auto_reply":
                r = await loop.run_in_executor(None, lambda: whatsapp_auto_reply(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or "Auto-replied to WhatsApp message."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "screen_process":
                import time as _t_mod
                _now = _t_mod.monotonic()
                _cooldown = 4.0  # seconds — covers echo window after speaking ends
                if self._vision_busy or (_now - self._vision_last_time) < _cooldown:
                    _wait = max(0, _cooldown - (_now - self._vision_last_time))
                    print(f"[Vision] ⏳ Cooldown active ({_wait:.1f}s remaining) — ignoring duplicate call")
                    print(f"[Vision] [Wait] Cooldown active ({_wait:.1f}s remaining) — ignoring duplicate call")
                    result = "Vision is still processing the previous request. I will not call this again."
                else:
                    self._vision_busy      = True
                    self._vision_last_time = _now
                    angle     = args.get("angle", "screen").lower()
                    user_text = args.get("text", "What do you see?")
                    if angle == "camera":
                        img_b, mime_t = await loop.run_in_executor(None, _capture_camera)
                        self.ui.start_camera_stream()
                        self._vision_cam_active = True
                        print(f"[Vision] [Camera] {len(img_b):,} bytes")
                        _stall = "camera"
                    else:
                        img_b, mime_t = await loop.run_in_executor(None, _capture_screen)
                        print(f"[Vision] [Screen] {len(img_b):,} bytes")
                        _stall = "screen"
                    self._pending_vision = (img_b, mime_t, user_text, angle)
                    result = (
                        f"[VISION_ACTIVE] {_stall.capitalize()} captured. "
                        f"Immediately say ONE short natural sentence in the user's own language, "
                        f"telling them you are looking at their {_stall} right now. "
                        f"Do NOT describe or guess content — the actual image arrives in the NEXT message."
                    )

            elif name == "close_camera":
                self.ui.stop_camera_stream()
                result = "Camera closed."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
                # Mirror results to the on-screen content panel
                _mode = args.get("mode", "search")
                if r and not r.startswith("No results") and not r.startswith("Search failed"):
                    _query = args.get("query") or ", ".join(args.get("items", []))
                    _label = f"{_mode.upper()} — {_query[:38]}" if _query else _mode.upper()
                    self.ui.show_content(_label, r)
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "system_status":
                r = await loop.run_in_executor(None, get_system_status)
                result = str(r)

            elif name == "automation_workflow":
                r = await loop.run_in_executor(None, lambda: automation_workflow(parameters=args))
                result = r or "Done."

            elif name == "phone_action":
                r = await loop.run_in_executor(None, lambda: phone_action(parameters=args))
                result = r or "Done."

            elif name == "skills_manager":
                r = await loop.run_in_executor(None, lambda: skills_tool(parameters=args))
                result = r or "Done."

            elif name == "screen_peeler":
                r = await loop.run_in_executor(None, lambda: screen_peeler_action(parameters=args, player=self.ui, speak=self.speak))
                result = r or "ScreenPeeler executed."

            elif name == "ai_wallpaper":
                from actions.desktop import set_ai_wallpaper
                prompt = args.get("prompt") or args.get("query") or "cyberpunk neon city"
                r = await loop.run_in_executor(None, lambda: set_ai_wallpaper(prompt, player=self.ui))
                result = r or "Wallpaper applied."

            elif name == "generate_document":
                r = await loop.run_in_executor(None, lambda: document_generator_action(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Document generated."

            elif name == "deploy_wormhole":
                r = await loop.run_in_executor(None, lambda: wormhole_action(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Wormhole action completed."

            elif name == "smart_organize":
                from actions.desktop import smart_organize_directory
                target = args.get("target") or "downloads"
                mode = args.get("mode") or "by_type"
                r = await loop.run_in_executor(None, lambda: smart_organize_directory(target=target, mode=mode))
                result = r or "Folder organized."

            elif name == "interactive_game":
                r = await loop.run_in_executor(None, lambda: interactive_games_action(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Game action completed."

            elif name == "search_memory":
                r = await loop.run_in_executor(None, lambda: search_memory_action(parameters=args, player=self.ui, speak=self.speak))
                result = r or "No memories found."

            elif name == "forget_memory":
                r = await loop.run_in_executor(None, lambda: forget_memory_action(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Memory removed."

            elif name == "list_memories":
                r = await loop.run_in_executor(None, lambda: list_memories_action(parameters=args, player=self.ui, speak=self.speak))
                result = r or "No memory categories found."

            elif name == "shutdown_ansh":
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")
                def _shutdown():
                    import time, os
                    time.sleep(1)
                    os._exit(0)
                threading.Thread(target=_shutdown, daemon=True).start()

            elif name == "restart_ansh":
                self.ui.write_log("SYS: Self-restart requested.")
                self.speak("Restarting Ansh assistant, sir.")
                def _restart_proc():
                    import time, sys, os, subprocess
                    time.sleep(1)
                    python = sys.executable
                    cmd = [python] + sys.argv
                    print(f"[ANSH] Re-launching process: {cmd}")
                    subprocess.Popen(cmd)
                    os._exit(0)
                threading.Thread(target=_restart_proc, daemon=True).start()
                result = "Restarting Ansh..."

            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            if not msg:
                continue
            if isinstance(msg, dict):
                data = msg.get("data")
                if not data or len(data) == 0:
                    continue
                mime = msg.get("mime_type") or f"audio/pcm;rate={SEND_SAMPLE_RATE}"
                if ";" not in mime:
                    mime = f"{mime};rate={SEND_SAMPLE_RATE}"
                blob = types.Blob(data=data, mime_type=mime)
                await self.session.send_realtime_input(audio=blob)
            elif isinstance(msg, types.Blob):
                await self.session.send_realtime_input(audio=msg)
            else:
                await self.session.send_realtime_input(audio=msg)

    def _safe_enqueue_out(self, item):
        q = self.out_queue
        if not q:
            return
        try:
            q.put_nowait(item)
        except Exception:
            try:
                q.get_nowait()  # Drop oldest item if queue is full
                q.put_nowait(item)
            except Exception:
                pass

    async def _listen_audio(self):
        print("[ANSH] Mic started (Super-Fast Voice Security Active)")
        loop = asyncio.get_event_loop()

        buffer_pcm = bytearray()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                ansh_speaking = self._is_speaking
            if not ansh_speaking and not self.ui.muted and not self._phone_active:
                data = bytes(indata)
                if data:
                    current_state = self.auth_mgr.update_state()
                    if current_state in (AuthState.OWNER_AUTHENTICATED, AuthState.SESSION_AUTHENTICATED):
                        # Zero-latency immediate stream to Gemini Live with safe queueing
                        loop.call_soon_threadsafe(
                            self._safe_enqueue_out,
                            {"data": data, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"}
                        )
                    else:
                        buffer_pcm.extend(data)

        try:
            with sd.RawInputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[ANSH] Mic stream open")
                while True:
                    await asyncio.sleep(0.01)

                    if len(buffer_pcm) >= 3200:  # ~0.2s ultra-fast frame check
                        chunk = bytes(buffer_pcm)
                        buffer_pcm.clear()

                        from core.speaker_verification import detect_voice_activity
                        if not detect_voice_activity(chunk):
                            continue

                        current_state = self.auth_mgr.update_state()

                        if current_state == AuthState.UNENROLLED:
                            ok, msg = self.auth_mgr.enrollment.add_sample(chunk)
                            self.ui.write_log(f"SYS: Voice Enrollment — {msg}")
                            print(f"[Enrollment] {msg}")
                            if ok and self.auth_mgr.enrollment.is_complete():
                                if self.auth_mgr.enrollment.save_owner_profile():
                                    self.auth_mgr.verifier.reload_profile()
                                    self.auth_mgr.current_state = AuthState.LOCKED
                                    self.ui.write_log("SYS: Owner voice enrolled successfully!")
                                    self.speak("Owner voice enrolled successfully!")

                        elif current_state == AuthState.PASSWORD_REQUIRED:
                            spoken_pwd = ""
                            try:
                                import speech_recognition as sr
                                rec = sr.Recognizer()
                                audio_data = sr.AudioData(chunk, SEND_SAMPLE_RATE, 2)
                                spoken_pwd = rec.recognize_google(audio_data)
                            except Exception:
                                pass

                            if spoken_pwd:
                                if self.auth_mgr.submit_password(spoken_pwd):
                                    self.ui.write_log("SYS: PASSWORD VERIFIED -> Access granted.")
                                    self.speak("Password verified. Access granted.")
                                else:
                                    self.ui.write_log("SYS: PASSWORD FAILED -> ACCESS DENIED.")
                                    self.speak("Access denied.")

                        elif current_state in (AuthState.LOCKED, AuthState.VERIFYING_VOICE):
                            auth_state, detail = self.auth_mgr.process_voice_input(chunk)
                            if auth_state == AuthState.OWNER_AUTHENTICATED:
                                self.ui.write_log("SYS: OWNER VERIFIED")
                                self._safe_enqueue_out(
                                    {"data": chunk, "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}"}
                                )
                            elif auth_state == AuthState.PASSWORD_REQUIRED:
                                self.ui.write_log("SYS: UNKNOWN SPEAKER -> Password required.")
                                self.speak("Password batao.")
                            elif auth_state == AuthState.ACCESS_DENIED:
                                self.ui.write_log("SYS: ACCESS DENIED -> SILENT LOCKOUT.")

        except Exception as e:
            print(f"[ANSH] [Error] Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[ANSH] Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if self._interrupted:
                            pass  # discard: interrupted
                        else:
                            if self._turn_done_event and self._turn_done_event.is_set():
                                self._turn_done_event.clear()
                            # Split into ~50 ms chunks so interrupt() stops audio within 50 ms
                            # (24000 Hz × 2 bytes/sample × 0.05 s = 2400 bytes per slice)
                            _audio_data = response.data
                            _SLICE = 2400
                            for _i in range(0, len(_audio_data), _SLICE):
                                self.audio_in_queue.put_nowait(_audio_data[_i : _i + _SLICE])

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt and txt != (out_buf[-1] if out_buf else ""):
                                out_buf.append(txt)
                                partial_out = " ".join(out_buf).strip()
                                if partial_out and hasattr(self.ui, "_win") and getattr(self.ui, "_win", None):
                                    self.ui._win.subtitle_signal.emit(partial_out)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)
                                self._last_user_speech = time.monotonic()

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            # If this turn_complete ends an interrupted response, clear the
                            # flag and skip all further processing for that turn.
                            if self._interrupted:
                                self._interrupted = False
                                in_buf  = []
                                out_buf = []
                                continue

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                                if self._dashboard:
                                    asyncio.create_task(self._dashboard.broadcast({
                                        "type": "log", "speaker": "user",
                                        "text": full_in,
                                        "ts": datetime.now().isoformat(),
                                    }))
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui._win.subtitle_signal.emit(full_out)
                                self.ui.write_log(f"{self._asst_name}: {full_out}")
                                if self._dashboard:
                                    asyncio.create_task(self._dashboard.broadcast({
                                        "type": "log", "speaker": "ansh",
                                        "text": full_out,
                                        "ts": datetime.now().isoformat(),
                                    }))
                            out_buf = []

                            # Vision injection: model finished tool-response turn → now send the image
                            if self._pending_vision and self.session:
                                import base64 as _b64
                                img_b, mime_t, question, angle = self._pending_vision
                                self._pending_vision = None
                                b64 = _b64.b64encode(img_b).decode("ascii")
                                print(f"[Vision] [Out] {len(img_b):,} bytes (angle={angle}) -> main session")
                                await self.session.send_client_content(
                                    turns={"role": "user", "parts": [
                                        {"inline_data": {"mime_type": mime_t, "data": b64}},
                                        {"text": question},
                                    ]},
                                    turn_complete=True,
                                )
                                # Mark next turn_complete behaviour depending on angle
                                if self._vision_cam_active:
                                    # Camera: keep busy until ANSH finishes speaking the answer
                                    self._vision_cam_active    = False
                                    self._vision_close_pending = True
                                else:
                                    # Screen-only: no camera to close; release busy flag now
                                    self._vision_busy = False
                            elif self._vision_close_pending:
                                # This turn_complete IS the vision answer — close camera + release busy flag
                                self._vision_close_pending = False
                                self._vision_busy = False
                                async def _cam_close():
                                    await asyncio.sleep(2.0)
                                    self.ui.stop_camera_stream()
                                asyncio.create_task(_cam_close())

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[ANSH] Call {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            err_s = f"{e!r} {e}"
            if any(k in err_s for k in ("1008", "GoAway", "session durat", "1000", "1001", "1006", "ConnectionClosed", "closed", "aborted")):
                pass  # Graceful session refresh from Gemini API
            else:
                print(f"[ANSH] Recv closed: {e}")

    async def _play_audio(self):
        print("[ANSH] Play started")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                    continue
                self.set_speaking(True)
                try:
                    await asyncio.to_thread(stream.write, chunk)
                except (RuntimeError, asyncio.CancelledError):
                    break   # executor shutting down — exit cleanly
        except Exception as e:
            print(f"[ANSH] [Warn] Play audio warning: {e}")
        finally:
            self.set_speaking(False)
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    # ── Morning briefing ────────────────────────────────────────────────────────

    async def _send_startup_briefing(self) -> None:
        """
        Two-phase briefing optimized for speed:
          Phase 1 — instant greeting (no tools) → speech starts in <1s
          Phase 2 — news pre-fetched in a background thread while Phase 1 plays,
                    delivered as ready text (no Gemini tool-call round-trip) and
                    shown on the UI content panel. Waits for turn_complete event
                    instead of a fixed sleep so there is no unnecessary gap.
        """
        memory   = load_memory()
        identity = memory.get("identity", {})

        def _val(k: str) -> str:
            e = identity.get(k, {})
            return (e.get("value", "") if isinstance(e, dict) else str(e)).strip()

        lang = _val("language")
        name = _val("name")
        time_str = datetime.now().strftime("%H:%M")

        # Start fetching news immediately — runs in parallel while phase 1 plays
        loop = asyncio.get_event_loop()
        news_future = loop.run_in_executor(None, _fetch_news_sync, "top world news today")

        await asyncio.sleep(0.3)
        if not self.session:
            return

        # ── Phase 1: instant greeting ─────────────────────────────────────────
        lang_clause = f" Respond in {lang}." if lang else ""
        name_clause = f" Address the user as {name}." if name else ""
        p1 = (
            f"Greet the user, mention it is {time_str}, and say you are fetching today's news now. "
            f"One short sentence only. Do not call any tools.{lang_clause}{name_clause}"
        )

        # Clear the turn-done event so we can wait for Phase 1 to finish
        if self._turn_done_event:
            self._turn_done_event.clear()

        await self.session.send_client_content(
            turns={"role": "user", "parts": [{"text": p1}]},
            turn_complete=True,
        )
        self.ui.write_log("SYS: Briefing phase 1 (greeting) sent.")

        # ── Phase 2: fire as soon as Phase 1 audio is done ───────────────────
        async def _deliver_news():
            try:
                lang_str = f" Respond in {lang}." if lang else ""

                # Wait for news fetch (already running) and Phase 1 turn-complete
                # in parallel — whichever takes longer determines the wait time
                news_done   = asyncio.wrap_future(news_future)
                turn_waited = False
                if self._turn_done_event:
                    try:
                        await asyncio.wait_for(self._turn_done_event.wait(), timeout=6.0)
                        turn_waited = True
                    except asyncio.TimeoutError:
                        pass

                # If turn_complete didn't fire (timeout), give a small buffer
                if not turn_waited:
                    await asyncio.sleep(1.0)

                try:
                    news_text = await asyncio.wait_for(news_done, timeout=4.0)
                except Exception:
                    news_text = ""

                if not self.session:
                    return

                if news_text and len(news_text) > 60:
                    # Show on UI content panel immediately
                    self.ui.show_content("NEWS — top world news today", news_text)

                    p2 = (
                        f"[BRIEFING] Here are today's top news headlines:\n{news_text}\n\n"
                        "Pick ONE headline, summarise it in one sentence, then say the full list "
                        f"is displayed on screen. Do not call any tools.{lang_str}"
                    )
                else:
                    p2 = (
                        "News headlines could not be fetched right now. "
                        f"Let the user know briefly.{lang_str}"
                    )

                await self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": p2}]},
                    turn_complete=True,
                )
                self.ui.write_log("SYS: Briefing phase 2 (news) sent.")
            except Exception as e:
                print(f"[Briefing] Phase 2 error: {e}")
                self.ui.write_log(f"SYS: Briefing phase 2 failed: {e}")

        asyncio.create_task(_deliver_news())

    # ── System monitor ──────────────────────────────────────────────────────────

    async def _run_system_monitor(self) -> None:
        """Background task: system monitor voice alerts (disabled per user request)."""
        return

    # ── Proactive mode ──────────────────────────────────────────────────────────

    async def _run_proactive_mode(self) -> None:
        """
        Background task: periodically checks if the user has been silent long enough,
        then hands time + memory context to Gemini so it can decide what (if anything)
        to say proactively. No hardcoded rules — Gemini makes the call.
        """
        while True:
            await asyncio.sleep(60)   # evaluate once per minute

            if not self.session:
                continue

            with self._speaking_lock:
                speaking = self._is_speaking
            if speaking:
                continue

            if not self._proactive.should_trigger(self._last_user_speech):
                continue

            self._proactive.mark_triggered()

            try:
                memory = await asyncio.to_thread(load_memory)
                prompt = self._proactive.build_prompt(memory)
                await self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": prompt}]},
                    turn_complete=True,
                )
                self.ui.write_log("SYS: Proactive check-in.")
            except Exception as e:
                print(f"[Proactive] [Warn] {e}")

    # ── Phone audio relay ────────────────────────────────────────────────────────

    async def _relay_phone_audio(self) -> None:
        """Forward phone mic PCM chunks from dashboard queue into the Gemini Live session."""
        q = self._dashboard._phone_audio_queue
        while True:
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No audio for 1 s → phone mic inactive, give PC mic back
                self._phone_active = False
                continue
            self._phone_active = True   # phone is streaming — silence PC mic
            with self._speaking_lock:
                speaking = self._is_speaking
            if not speaking and not self.ui.muted:
                try:
                    self.out_queue.put_nowait(chunk)
                except asyncio.QueueFull:
                    pass

    def _on_phone_connected(self) -> None:
        self.ui.write_log("SYS: Phone connected via Remote Dashboard.")
        self.ui.notify_phone_connected()

    # ── dashboard command relay ─────────────────────────────────────────────

    async def _process_dashboard_commands(self) -> None:
        while True:
            try:
                text = await asyncio.wait_for(
                    self._dashboard._command_queue.get(), timeout=0.5
                )
                if not text:
                    continue
                # Wait up to 8s for session to become ready after a wake
                for _ in range(80):
                    if self.session:
                        break
                    await asyncio.sleep(0.1)
                if self.session:
                    await self.session.send_client_content(
                        turns={"role": "user", "parts": [{"text": text}]},
                        turn_complete=True,
                    )
                    self.ui.write_log(f"[Web]: {text}")
                else:
                    print(f"[Dashboard] Dropped command (no session): {text}")
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[Dashboard] Command error: {e}")
                await asyncio.sleep(0.5)

    # ── main loop ───────────────────────────────────────────────────────────

    async def run(self):
        self._loop = asyncio.get_event_loop()

        # Start dashboard (optional — needs: pip install fastapi "uvicorn[standard]" cryptography)
        try:
            from dashboard.server import DashboardServer
            self._dashboard = DashboardServer()
            self._dashboard.set_connect_callback(self._on_phone_connected)
            
            async def safe_serve():
                try:
                    await self._dashboard.serve()
                except (Exception, SystemExit) as e:
                    print(f"[Dashboard] Serve skipped (already running or error): {e}")
            
            asyncio.create_task(safe_serve())
            # Runs for the whole lifetime, not just inside an active session
            asyncio.create_task(self._process_dashboard_commands())
        except Exception as e:
            print(f"[Dashboard] Disabled: {e}")
            self._dashboard = None

        lic_mgr = LicenseManager()
        is_lic, rem_sec, trial_status_str = lic_mgr.get_trial_status()
        self.ui.write_log(f"SYS: License Status — {trial_status_str}")

        while True:
            try:
                if not lic_mgr.is_license_valid():
                    self.ui.write_log("ERR: 3-Day Free Trial Expired. Product Activation Required.")
                    self.ui.set_state("SLEEPING")
                    activated = self.ui.prompt_activation(lic_mgr)
                    if not activated:
                        print("[License] Product unactivated. Waiting for key...")
                        await asyncio.sleep(3)
                        continue

                print("[ANSH] Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                # Fresh client on every reconnect — avoids stale HTTP session state
                client = genai.Client(
                    api_key=_get_api_key(),
                    http_options={"api_version": "v1beta"}
                )

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session          = session
                    self.audio_in_queue   = asyncio.Queue()
                    self.out_queue        = asyncio.Queue(maxsize=200)
                    self._turn_done_event = asyncio.Event()

                    # Reset transient state that must not carry over from a previous session
                    self._pending_vision       = None
                    self._vision_cam_active    = False
                    self._vision_close_pending = False
                    self._vision_busy          = False
                    self._vision_last_time     = 0.0
                    self._interrupted          = False

                    print("[ANSH] Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: ANSH online.")

                    if self._dashboard:
                        await self._dashboard.broadcast({"type": "status", "state": "active"})

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._run_system_monitor())
                    tg.create_task(self._run_proactive_mode())
                    if self._dashboard:
                        tg.create_task(self._relay_phone_audio())

                    # Morning briefing — fires once per process launch (if enabled)
                    if not self._briefing_sent and get_brief_enabled():
                        self._briefing_sent = True
                        tg.create_task(self._send_startup_briefing())

            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except BaseException as e:
                # Catches both Exception and BaseExceptionGroup (Python 3.11+
                # TaskGroup raises BaseExceptionGroup when tasks are cancelled
                # externally, which `except Exception` would miss, letting the
                # exception escape the while-loop and causing asyncio.run() to
                # start shutdown — resulting in "executor after shutdown" errors).
                err_str = f"{e!r} {e}"
                is_goaway = any(k in err_str for k in ("1008", "GoAway", "session durat", "1000", "1001", "1006", "ConnectionClosed", "closed", "aborted"))

                if is_goaway:
                    print("[ANSH] Session refreshed seamlessly.")
                    self._conn_backoff = 0.5
                else:
                    print(f"[ANSH] Notice ({type(e).__name__}): {e}")

                # Invalid API key — stop hammering the API, prompt re-configuration
                if "API key not valid" in err_str:
                    self.ui.write_log("ERR: API key invalid — please re-enter your key.")
                    self.ui.set_state("SLEEPING")
                    self.ui.prompt_reconfig()
                    while not self.ui._win._ready:
                        await asyncio.sleep(1)
                    print("[ANSH] New API key saved — reconnecting...")
                    _conn_backoff = 3
                    continue

                # Network / timeout errors — log clearly and back off
                is_net_err = any(k in err_str for k in (
                    "TimeoutError", "timed out", "getaddrinfo", "CancelledError",
                    "ConnectionRefusedError", "OSError", "Cannot connect",
                ))
                if is_net_err:
                    _conn_backoff = min(getattr(self, "_conn_backoff", 3) * 2, 60)
                    self._conn_backoff = _conn_backoff
                    self.ui.write_log(
                        f"NET: Bağlantı kurulamadı — {_conn_backoff}s sonra tekrar deneniyor. "
                        "(VPN gerekiyor olabilir)"
                    )
                else:
                    self._conn_backoff = 3
            finally:
                self.session = None

            self.set_speaking(False)
            self.ui.set_state("SLEEPING")

            if self._dashboard:
                await self._dashboard.broadcast({"type": "status", "state": "sleeping"})

            delay = getattr(self, "_conn_backoff", 3)
            print(f"[ANSH] Reconnecting in {delay}s...")
            await asyncio.sleep(delay)

def main():
    import socket
    import sys
    try:
        # Create a socket lock to ensure only one instance of the app runs at a time
        singleton_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        singleton_socket.bind(('127.0.0.1', 65432))
    except socket.error:
        print("[SYS] An instance of Ansh is already running. Exiting.")
        sys.exit(0)

    if getattr(sys, 'frozen', False):
        try:
            import os
            from pathlib import Path
            desktop = Path.home() / "Desktop" / "Ansh AI.lnk"
            if not desktop.exists():
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(desktop))
                shortcut.Targetpath = sys.executable
                shortcut.WorkingDirectory = str(Path(sys.executable).parent)
                shortcut.IconLocation = sys.executable
                shortcut.save()
                print("[SYS] Desktop shortcut created.")
        except Exception as e:
            print(f"[SYS] Failed to create shortcut: {e}")

    ui = AnshUI("face.png")

    def runner():
        ui.wait_for_api_key()
        ansh = AnshLive(ui)
        try:
            asyncio.run(ansh.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()
    