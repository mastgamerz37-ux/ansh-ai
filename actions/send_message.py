"""
actions/send_message.py — Smart Persistent Messaging & Message Reading for ANSH

Optimized for instant consecutive messaging without repeatedly re-opening apps.
Supports reading incoming messages from active chat threads.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.06
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

# Global state tracking for smart window reuse
_STATE = {
    "app": None,
    "receiver": None,
    "last_time": 0.0
}


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_os() -> str:
    try:
        cfg = json.loads(
            (_base_dir() / "config" / "api_keys.json").read_text(encoding="utf-8")
        )
        return cfg.get("os_system", "windows").lower()
    except Exception:
        return "windows"


def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")


def _focus_app_window(app_name: str) -> bool:
    """Brings an already-open app window (e.g. WhatsApp) to foreground without re-launching."""
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(app_name)
        if not windows:
            all_w = gw.getAllWindows()
            windows = [w for w in all_w if app_name.lower() in w.title.lower() and w.title.strip()]
        if windows:
            w = windows[0]
            if w.isMinimized:
                w.restore()
            w.activate()
            time.sleep(0.3)
            return True
    except Exception as e:
        print(f"[SendMessage] Focus window error for {app_name}: {e}")
    return False


def _paste_text(text: str) -> None:
    _require_pyautogui()
    os_name = _get_os()
    paste_hotkey = ("command", "v") if os_name == "mac" else ("ctrl", "v")

    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.15)
        pyautogui.hotkey(*paste_hotkey)
        time.sleep(0.1)
    else:
        pyautogui.write(text, interval=0.03)


def _clear_and_paste(text: str) -> None:
    _require_pyautogui()
    os_name = _get_os()
    select_all = ("command", "a") if os_name == "mac" else ("ctrl", "a")
    pyautogui.hotkey(*select_all)
    time.sleep(0.1)
    pyautogui.press("delete")
    time.sleep(0.1)
    _paste_text(text)


def _open_app(app_name: str) -> bool:
    _require_pyautogui()
    os_name = _get_os()

    try:
        if os_name == "windows":
            pyautogui.press("win")
            time.sleep(0.5)
            _paste_text(app_name)
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(2.0)
            return True
        elif os_name == "mac":
            subprocess.run(["open", "-a", app_name], capture_output=True, text=True, timeout=10)
            time.sleep(2.0)
            return True
        else:
            subprocess.Popen([app_name.lower()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2.0)
            return True
    except Exception as e:
        print(f"[SendMessage] ⚠️ Could not open {app_name}: {e}")
        return False


def _search_in_app(query: str) -> None:
    _require_pyautogui()
    os_name = _get_os()
    search_hotkey = ("command", "f") if os_name == "mac" else ("ctrl", "f")

    pyautogui.hotkey(*search_hotkey)
    time.sleep(0.4)
    _clear_and_paste(query)
    time.sleep(0.8)


def _desktop_send(app_name: str, receiver: str, message: str) -> str:
    _require_pyautogui()
def _get_str_param(params: dict, key: str, default: str = "") -> str:
    if not params or not isinstance(params, dict):
        return default
    val = params.get(key)
    if val is None:
        return default
    return str(val).strip()


def _desktop_send(app_name: str, receiver: str, message: str) -> str:
    _require_pyautogui()
    now = time.time()
    receiver_clean = (receiver or "").strip()
    message_clean  = (message or "").strip()

    if not message_clean:
        return "Please specify the message content."

    # Active chat fallback: if no receiver specified, send to active chat window
    if not receiver_clean:
        if _focus_app_window(app_name):
            print(f"[SendMessage] ⚡ Active chat mode: Pasting message directly into open {app_name} chat.")
            _paste_text(message_clean)
            time.sleep(0.15)
            pyautogui.press("enter")
            _STATE["app"] = app_name.lower()
            _STATE["last_time"] = now
            return f"Message sent via {app_name}."
        return f"Please open {app_name} or specify a contact name."

    same_app = (_STATE["app"] == app_name.lower())
    same_receiver = (_STATE["receiver"] == receiver_clean.lower())
    recent = (now - _STATE["last_time"] < 300)

    # 1. Fast-path: App & Receiver already open -> Paste directly without searching or reopening!
    if same_app and same_receiver and recent:
        print(f"[SendMessage] ⚡ Fast-path: {app_name} active chat with '{receiver_clean}'. Pasting message directly.")
        _focus_app_window(app_name)
        _paste_text(message_clean)
        time.sleep(0.15)
        pyautogui.press("enter")
        _STATE["last_time"] = now
        return f"Message sent to {receiver_clean} via {app_name}."

    # 2. Fast-path: App is already open, but switching to a different contact
    if same_app and recent and _focus_app_window(app_name):
        print(f"[SendMessage] ⚡ Fast-path: Switching contact in open {app_name} to '{receiver_clean}'.")
        _search_in_app(receiver_clean)
        pyautogui.press("enter")
        time.sleep(0.5)
        _paste_text(message_clean)
        time.sleep(0.15)
        pyautogui.press("enter")
        _STATE["receiver"] = receiver_clean.lower()
        _STATE["last_time"] = now
        return f"Message sent to {receiver_clean} via {app_name}."

    # 3. Full open: App not open yet or inactive
    if not _focus_app_window(app_name):
        if not _open_app(app_name):
            return f"Could not open {app_name}."
        time.sleep(1.0)

    _search_in_app(receiver_clean)
    pyautogui.press("enter")
    time.sleep(0.8)

    _paste_text(message_clean)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.3)

    _STATE["app"] = app_name.lower()
    _STATE["receiver"] = receiver_clean.lower()
    _STATE["last_time"] = now
    return f"Message sent to {receiver_clean} via {app_name}."


def _send_whatsapp(receiver: str, message: str) -> str:
    return _desktop_send("WhatsApp", receiver, message)


def _send_telegram(receiver: str, message: str) -> str:
    return _desktop_send("Telegram", receiver, message)


def _send_signal(receiver: str, message: str) -> str:
    return _desktop_send("Signal", receiver, message)


def _send_discord(receiver: str, message: str) -> str:
    return _desktop_send("Discord", receiver, message)


def _send_instagram(receiver: str, message: str) -> str:
    _require_pyautogui()
    return _desktop_send("Instagram", receiver, message)


def _send_messenger(receiver: str, message: str) -> str:
    _require_pyautogui()
    return _desktop_send("Messenger", receiver, message)


_PLATFORM_MAP = [
    ({"whatsapp", "wp", "wapp"},              _send_whatsapp),
    ({"telegram", "tg"},                      _send_telegram),
    ({"instagram", "ig", "insta"},            _send_instagram),
    ({"signal"},                               _send_signal),
    ({"discord"},                              _send_discord),
    ({"messenger", "facebook", "fb"},         _send_messenger),
]


def _resolve_platform(platform_str: str):
    key = (platform_str or "").lower().strip()
    for keywords, handler in _PLATFORM_MAP:
        if any(k in key for k in keywords):
            return handler
    return lambda r, m: _desktop_send((platform_str or "WhatsApp").strip().title(), r, m)


def send_message(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params       = parameters or {}
    receiver     = _get_str_param(params, "receiver")
    message_text = _get_str_param(params, "message_text")
    platform     = _get_str_param(params, "platform", "whatsapp")

    if not message_text:
        return "Please specify the message content."
    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed — cannot control the desktop."

    preview = message_text[:50] + ("…" if len(message_text) > 50 else "")
    print(f"[SendMessage] 📨 {platform} → {receiver or 'active chat'}: {preview}")
    if player:
        player.write_log(f"[msg] {platform} → {receiver or 'active chat'}")

    try:
        handler = _resolve_platform(platform)
        result  = handler(receiver, message_text)
    except Exception as e:
        result = f"Could not send message: {e}"

    print(f"[SendMessage] {'✅' if 'sent' in result.lower() else '❌'} {result}")
    if player:
        player.write_log(f"[msg] {result}")

    return result


def read_messages(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Reads recent messages from open WhatsApp/messaging window to understand incoming replies.
    """
    params = parameters or {}
    platform = _get_str_param(params, "platform", "whatsapp").title()
    receiver = _get_str_param(params, "receiver")

    _require_pyautogui()

    if not _focus_app_window(platform):
        _open_app(platform)
        time.sleep(1.0)

    if receiver and _STATE["receiver"] != receiver.lower():
        _search_in_app(receiver)
        pyautogui.press("enter")
        time.sleep(0.5)
        _STATE["receiver"] = receiver.lower()
        _STATE["app"] = platform.lower()
        _STATE["last_time"] = time.time()

    time.sleep(0.3)

    # Attempt to copy chat text via keyboard selection
    if _PYPERCLIP:
        pyperclip.copy("")

    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.2)

    chat_text = pyperclip.paste() if _PYPERCLIP else ""

    if not chat_text or len(chat_text.strip()) == 0:
        return f"Opened {platform} chat with {receiver or 'active contact'}. Chat window is open on screen."

    lines = [line.strip() for line in chat_text.splitlines() if line.strip()]
    recent = lines[-12:] if len(lines) > 12 else lines
    result_text = "\n".join(recent)

    print(f"[ReadMessages] 📖 Read {len(lines)} lines from {platform} chat.")
    if player:
        player.write_log(f"[ReadMessages] Read chat from {platform}")

    return f"Recent messages in {platform} chat thread:\n{result_text}"


def whatsapp_call(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Initiates a WhatsApp voice or video call to a specified contact.
    """
    params    = parameters or {}
    receiver  = _get_str_param(params, "receiver")
    call_type = _get_str_param(params, "call_type", "voice").lower()

    if not _PYAUTOGUI:
        return "PyAutoGUI is not installed — cannot control the desktop."

    app_name = "WhatsApp"
    now = time.time()

    same_app = (_STATE["app"] == app_name.lower())
    same_receiver = (_STATE["receiver"] == receiver.lower()) if receiver else True
    recent = (now - _STATE["last_time"] < 300)

    print(f"[WhatsAppCall] 📞 Initiating {call_type} call to '{receiver or 'active chat'}' on WhatsApp...")
    if player:
        player.write_log(f"[call] WhatsApp {call_type} → {receiver or 'active chat'}")

    # 1. Focus or launch WhatsApp
    if not _focus_app_window(app_name):
        if not _open_app(app_name):
            return f"Could not open {app_name} for calling."
        time.sleep(1.2)

    # 2. Select receiver chat if specified and not active
    if receiver and not (same_app and same_receiver and recent):
        _search_in_app(receiver)
        pyautogui.press("enter")
        time.sleep(0.8)
        _STATE["app"] = app_name.lower()
        _STATE["receiver"] = receiver.lower()
        _STATE["last_time"] = now

    time.sleep(0.4)

    # 3. Trigger Call via Hotkeys
    if call_type == "video":
        pyautogui.hotkey("ctrl", "shift", "v")
        time.sleep(0.3)
        return f"Initiated WhatsApp video call to {receiver or 'active contact'}."
    else:
        pyautogui.hotkey("ctrl", "shift", "c")
        time.sleep(0.3)
        return f"Initiated WhatsApp voice call to {receiver or 'active contact'}."


def whatsapp_auto_reply(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Reads incoming messages from a WhatsApp chat, uses AI to formulate an intelligent response
    (answering questions or replying conversationally), and automatically sends the reply back.
    """
    params      = parameters or {}
    receiver    = _get_str_param(params, "receiver")
    custom_inst = _get_str_param(params, "instruction")
    platform    = _get_str_param(params, "platform", "whatsapp").title()

    _require_pyautogui()

    # 1. Read recent chat messages from WhatsApp
    read_params = {"platform": platform, "receiver": receiver}
    chat_history = read_messages(read_params, response=response, player=player, session_memory=session_memory)

    if not chat_history or "No messages" in chat_history:
        return f"Could not read messages from {platform} to auto-reply."

    # 2. Formulate AI response using TaskLLM
    try:
        from core.task_llm import call_task_llm

        user_name = "Anshu"
        system_prompt = (
            f"You are ANSH, an intelligent personal AI assistant representing your owner '{user_name}'.\n"
            f"Analyze the received WhatsApp message(s) carefully before replying:\n"
            f"1. MESSAGE ANALYSIS:\n"
            f"   - Is it a QUESTION? (e.g. asking for time, status, info, location, math, facts, or help) -> Answer it directly, accurately, and concisely.\n"
            f"   - Is it a STATEMENT or CASUAL TALK? (e.g. greeting, sharing news, casual discussion) -> Respond conversationally in a warm, friendly tone.\n"
            f"   - Is it a REQUEST or INSTRUCTION? -> Acknowledge politely and respond appropriately.\n"
            f"2. TONE & LANGUAGE:\n"
            f"   - Match the exact language/style of the incoming message (Hinglish, Hindi, or English).\n"
            f"   - Keep the reply natural, brief, and human-like.\n"
            f"3. OUTPUT FORMAT:\n"
            f"   - Output ONLY the final message text to be sent — no analysis labels, quotes, or meta commentary."
        )

        user_prompt = (
            f"Recent Chat Thread with {receiver or 'Contact'}:\n"
            f"----------------------------------------\n"
            f"{chat_history}\n"
            f"----------------------------------------\n"
        )
        if custom_inst:
            user_prompt += f"User's Specific Instruction: {custom_inst}\n"

        ai_reply = call_task_llm(prompt=user_prompt, system=system_prompt).strip()

        # Clean quotes if model wrapped output in quotes
        if ai_reply.startswith('"') and ai_reply.endswith('"'):
            ai_reply = ai_reply[1:-1].strip()

        if not ai_reply:
            return "Could not generate reply for the message."

        print(f"[AutoReply] 🤖 Generated Reply for '{receiver or 'active chat'}': {ai_reply}")

        # 3. Send generated response back via WhatsApp
        target_receiver = receiver or _STATE.get("receiver", "")
        send_params = {
            "receiver": target_receiver,
            "message_text": ai_reply,
            "platform": platform
        }
        send_result = send_message(send_params, response=response, player=player, session_memory=session_memory)

        return f"Read WhatsApp message from '{target_receiver or 'active chat'}' and auto-replied: \"{ai_reply}\""

    except Exception as e:
        print(f"[AutoReply] ❌ Error generating reply: {e}")
        return f"Failed to generate auto-reply: {e}"