# ANSH — Complete User, Operational & Troubleshooting Guide
### Your Step-by-Step Manual for Everyday Voice Interaction, Desktop Automation & System Mastery
**Product:** ANSH — Your Own AI Friend  
**Developer:** **Anshu Dubey**  
**Official Activation & Key Portal:** [https://getyoursoft.page.gd](https://getyoursoft.page.gd)  
**Source Repository:** [https://github.com/mastgamerz37-ux/ansh-ai](https://github.com/mastgamerz37-ux/ansh-ai)  

---

## 📑 Guide Contents

1. [Quick Start: Zero to Running in 5 Minutes](#1-quick-start-zero-to-running-in-5-minutes)
2. [First-Time Voice Enrollment & Security Setup](#2-first-time-voice-enrollment--security-setup)
3. [Voice Interaction & Everyday Spoken Commands](#3-voice-interaction--everyday-spoken-commands)
4. [Autonomous Desktop Control & File Management](#4-autonomous-desktop-control--file-management)
5. [Developer & Coding Agent Workflow](#5-developer--coding-agent-workflow)
6. [Safety, Shadow Backups & Undo Rollback](#6-safety-shadow-backups--undo-rollback)
7. [Smart Island Overlay & Futuristic HUD Interface](#7-smart-island-overlay--futuristic-hud-interface)
8. [Teaching ANSH: Memory, Knowledge Graph & Workflows](#8-teaching-ansh-memory-knowledge-graph--workflows)
9. [Study Intelligence, Notes & Quiz Engine](#9-study-intelligence-notes--quiz-engine)
10. [Commercial License & 3-Day Trial Activation Guide](#10-commercial-license--3-day-trial-activation-guide)
11. [Troubleshooting & Frequently Asked Questions (FAQ)](#11-troubleshooting--frequently-asked-questions-faq)

---

## 1. Quick Start: Zero to Running in 5 Minutes

### Step 1: Check Minimum System Prerequisites
- **OS:** Windows 10 or Windows 11 (64-bit).
- **Python:** Python 3.10 to 3.13 installed with PATH enabled.
- **Hardware:** Microphone and Speakers or Headset. Webcam is optional.

### Step 2: Obtain Free API Credentials
ANSH uses a Bring-Your-Own-Key (BYOK) architecture for cloud foundation models:
1. **Google Gemini API Key:** Visit [Google AI Studio](https://aistudio.google.com/app/apikey), sign in with any Google account, and click **"Create API Key"** (100% Free).
2. **Groq Cloud API Key:** Visit [Groq Console](https://console.groq.com/keys), sign up, and create a free API key (provides ultra-fast LLaMA-3.3-70B reasoning).

### Step 3: Configure Credentials
In `d:\ansh\core\.env` or `d:\ansh\config\api_keys.json`, insert your keys:
```json
{
  "gemini_api_key": "AIzaSyYourKeyHere...",
  "groq_api_key": "gsk_YourGroqKeyHere..."
}
```

### Step 4: Launch ANSH
Open PowerShell in the project directory:
```powershell
cd D:\ansh
python main.py
```
Upon startup, the **PyQt6 Cyberpunk HUD** and top **Smart Island** will appear, and ANSH will greet you through your speakers!

---

## 2. First-Time Voice Enrollment & Security Setup

ANSH features an advanced biometric voice security engine (`core/speaker_verification.py`). On the first launch, ANSH is in the `UNENROLLED` state.

```
       [Launch ANSH]
             │
             ▼
    [Enrollment Prompt]
             │
             ▼
   Speak Sample 1 ──► Speak Sample 2 ──► Speak Sample 3 ──► Speak Sample 4 ──► Speak Sample 5
             │
             ▼
[Vectorized 26-D Embedding Computed via Pure NumPy STFT & Mel Filterbanks]
             │
             ▼
   [Profile Saved to data/secure/owner_voice_profile.npz]
             │
             ▼
    [Set Emergency Password: Salted PBKDF2/SHA-256]
             │
             ▼
   [OWNER VERIFIED & READY]
```

### Tips for Perfect Enrollment
- **Quiet Environment:** Minimize background TV, fan noise, or music during enrollment.
- **Consistent Distance:** Speak naturally 15–30 cm (6–12 inches) away from your microphone.
- **Clear Speech:** Say a natural sentence for at least 1.5 to 2 seconds (e.g. *"Hey ANSH, I am Anshu and I am the owner of this system"*).
- **Emergency Password:** Choose a memorable passphrase (e.g. `anshu123`). If you ever have a cold or your microphone acts up, you can simply type or speak your password to unlock the system.

---

## 3. Voice Interaction & Everyday Spoken Commands

ANSH does not require robotic syntax. Speak naturally in English, Hindi, or Hinglish:

### 💬 General Conversation & Assistance
| What You Say | What ANSH Does |
| :--- | :--- |
| *"Hey ANSH, good morning! What's my schedule today?"* | Greets you, checks local notes and calendar context. |
| *"Can you explain how quantum computing works in simple terms?"* | Provides a clear, conversational breakdown. |
| *"What is the weather in Delhi right now?"* | Performs live web scraping and summarizes conditions. |
| *"Search the web for the latest artificial intelligence news."* | Runs live DuckDuckGo search and reads the top headlines. |

### 🎭 Personality Mode Switching
You can instantly alter ANSH's conversational style on the fly:
- **Developer Mode:** *"Switch to developer mode"* ➔ ANSH becomes terse, outputs code snippets, references line numbers, and skips pleasantries.
- **Casual / Bro Mode:** *"Bro mode on"* / *"Casual baat karo"* ➔ ANSH speaks warm, friendly Hinglish with colloquial expressions.
- **JARVIS Mode:** *"Be like JARVIS"* ➔ ANSH addresses you as *"Boss"* or *"Sir"*, responding with formal British military efficiency.
- **Mentor Mode:** *"Teach me mode"* ➔ ANSH breaks concepts down step-by-step with pedagogical patience.

---

## 4. Autonomous Desktop Control & File Management

ANSH can operate your Windows desktop using native OS APIs and automated action dispatchers:

### 🖥️ Application & Window Control
- *"Open VS Code and Chrome"* ➔ Launches both applications simultaneously.
- *"Close Notepad"* / *"Minimize this window"* ➔ Performs window management commands.
- *"Mute my computer"* / *"Set volume to 50%"* ➔ Adjusts Windows master volume.
- *"Check my system performance"* ➔ Reads real-time CPU, RAM, battery, and GPU metrics.

### 📁 File Controller (`actions/file_controller.py`)
- *"Create a file named todo.txt on my Desktop with 5 coding tasks."*
- *"List all files inside D:\ansh\actions."*
- *"Read the first 20 lines of main.py."*
- *"Rename test.txt to completed.txt."*

### 👁️ Screen Peeler Visual Intelligence (`actions/screen_peeler.py`)
- *"Look at my screen and tell me why this code isn't compiling."*
  - ANSH captures the active monitor viewport, detects the terminal error via OCR/Vision, and explains the fix.
- *"Summarize the article currently open on my screen."*
- *"Where is the Submit button on this page?"*

---

## 5. Developer & Coding Agent Workflow

ANSH acts as an autonomous pair-programmer:

### 💻 Live Code Debugging & Editing
- **Referential Pronoun Resolution:** You can say *"Run this"* or *"Is file me line 40 ka error fix karo"*. ANSH automatically inspects the active IDE file and resolves the pronoun to the current target file!
- **Autonomous Error Repair:** When you execute a script that fails:
  1. ANSH reads the Python exception traceback.
  2. The System 2 AGI Planner analyzes the failing module.
  3. Automatically patches the file using `replace_file_content` or `file_controller`.
  4. Runs unit tests to verify that the patch resolved the issue.

---

## 6. Safety, Shadow Backups & Undo Rollback

Because ANSH can modify local files, it provides enterprise-grade safety:

```
[Tool Modifies or Deletes File]
              │
              ▼
[Automatic Pre-Execution Shadow Snapshot in data/shadow_backups/]
              │
              ▼
[Execute Requested Change]
              │
    ┌─────────┴─────────┐
    ▼                   ▼
User Satisfied     Error / Regret
                   User Says: "Undo that!" / "Rollback!"
                        │
                        ▼
             [Instant One-Click Restoration]
```

### Safety Commands
- *"Undo that"* / *"Rollback last action"* ➔ Restores the previous file state instantly.
- *"Emergency Stop"* / *"ANSH Freeze"* ➔ Immediately kills running sub-agents and freezes automated keystrokes.
- **Audit Log Review:** Open `data/secure/audit_log.jsonl` to see every tool execution, timestamp, and safety rating.

---

## 7. Smart Island Overlay & Futuristic HUD Interface

ANSH features two synchronized visual presentation layers:

### 7.1 The Desktop Smart Island (`smart_island.py`)
- **Floating Pill:** Positioned at the top-center of your primary display.
- **Always on Top:** Never steals keyboard focus from your active game or code editor.
- **Dynamic States:**
  - 🟢 **Pulse (Green):** Listening to your voice.
  - 🔵 **Orbit (Cyan):** Processing / Thinking (System 2 Planner active).
  - 🟣 **Waveform (Magenta):** ANSH is speaking.
  - 🟡 **Warning (Amber):** High CPU / Temperature threshold alert.
  - 🔴 **Lock (Red):** Voice unauthorized / Password required.

### 7.2 The PyQt6 Cyberpunk HUD (`ui.py`)
- **Real-Time Audio Visualizer:** High-FPS audio waveform analyzer.
- **Terminal Event Feed:** Live stream of sub-agent actions, tool parameters, and execution timings.
- **Camera Feed:** Real-time webcam thumbnail for visual confirmation.
- **Activation Modal:** Displays remaining trial hours with single-click key activation.

---

## 8. Teaching ANSH: Memory, Knowledge Graph & Workflows

ANSH learns and personalizes over time:

### 🧠 Semantic Memory (`memory/storage/`)
- Simply state personal preferences:
  - *"Remember that my favorite programming language is Python and I prefer dark mode."*
  - *"Note down that Anshu is working on the v2.5 release of ANSH AI."*
- ANSH automatically extracts facts and saves them to human-readable Markdown files in `memory/storage/`.

### 🕸️ Knowledge Graph (`data/memory/knowledge_graph.json`)
- Stores associative knowledge triples: `(Subject, Predicate, Object)`.
- Enables multi-hop reasoning (e.g. asking *"Who is the developer of the project I was working on yesterday?"* resolves through `(Anshu) -> [develops] -> (ANSH AI)`).

### 🎬 "Teach ANSH" Workflow Recording (`data/workflows/custom_workflows.json`)
You can teach ANSH repeated complex desktop routines:
1. Say: *"ANSH, start recording workflow 'Morning Setup'"*.
2. Perform or describe the steps: *"Open VS Code, open Chrome to GitHub, and launch Spotify"*.
3. Say: *"Save workflow"*.
4. From then on, simply say *"Run Morning Setup"*, and ANSH executes the entire sequence autonomously!

---

## 9. Study Intelligence, Notes & Quiz Engine

Located in `data/study/`, ANSH includes built-in learning assistance:

- **Doubt Solver:** *"I have a doubt in machine learning gradient descent. Explain with a real-life analogy."*
- **Auto Notes Compiler:** *"Compile a comprehensive revision sheet on Operating System deadlocks."* ➔ Saves a structured Markdown report in `data/study/`.
- **Interactive Quiz Generator:** *"Quiz me on Python decorators. Ask 3 questions one by one and grade my answers."* ➔ ANSH asks questions, listens to your spoken answers, scores your performance, and updates `study_progress.json`.

---

## 10. Commercial License & Subscription Activation Guide

```
[First Launch] ──► 72-Hour Unrestricted Free Evaluation Trial
                         │
                         ▼
             [72-Hour Free Trial Expires]
                         │
                         ▼
        [Product Activation Dialog Appears]
                         │
                         ▼
[Click "Get Product Key" ──► https://getyoursoft.page.gd]
       │                                     │
       ▼                                     ▼
 [Monthly Plan: ₹199/mo]          [Lifetime Pro: ₹999/once]
(Key: ANSH-M-XXXX-XXXX-XXXX)     (Key: ANSH-L-XXXX-XXXX-XXXX)
       │                                     │
       └──────────────────┬──────────────────┘
                          ▼
            ["Activate" ──► Instant Access]
```

### Where to Obtain a Product Key
1. Visit the official commercial licensing portal:  
   👉 **[https://getyoursoft.page.gd](https://getyoursoft.page.gd)**
2. Select your preferred tier:
   - **Monthly Subscription (₹199 / 30-Day Pass):** Keys start with `ANSH-M-XXXX-XXXX-XXXX`.
   - **Lifetime Perpetual (₹999 / One-Time):** Keys start with `ANSH-L-XXXX-XXXX-XXXX`.
3. Paste the key into the ANSH Activation Dialog or terminal and click **"Activate"**.
4. The software will instantly unlock all capabilities!

### Auto-Start on Windows Startup
- ANSH automatically registers in Windows startup on launch (`core/autostart.py`).
- When your computer boots, ANSH starts in the background using `pythonw.exe`.
- You can toggle this on or off anytime using the **AUTO-START** button in the HUD settings menu.

### Dedicated Desktop Window Mode for Dashboard
- Opening the dashboard from the HUD or Smart Island will launch a dedicated, standalone application window (`core/app_window.py`) instead of opening a browser tab.
- This gives you a clutter-free, native desktop experience without browser URL bars or tabs.

---

## 11. Troubleshooting & Frequently Asked Questions (FAQ)

### Q1: "ImportError: DLL load failed while importing _minpack: An Application Control policy has blocked this file"
- **Cause:** Windows 11 Smart App Control (SAC) or Defender Application Control blocked `scipy`'s C-extension DLLs.
- **Solution:** This has been **100% resolved in v2.5.0!** ANSH now utilizes our custom zero-dependency **Pure NumPy Audio Engine** (`_stft_numpy`). Ensure your repository is up to date (`git pull`).

### Q2: Voice Verification fails with "UNKNOWN SPEAKER"
- **Cause:** Background television noise, speaking too quietly, or microphone gain set too low.
- **Solution:**
  1. Speak your emergency fallback password (e.g. *"Password anshu123"*) to authenticate for the current session.
  2. To re-enroll with a cleaner voice profile, delete `data/secure/owner_voice_profile.npz` and restart ANSH to trigger fresh 5-sample enrollment.

### Q3: "API Key Missing or Invalid" Error
- **Cause:** `core/.env` or `config/api_keys.json` is missing your keys or has a typo.
- **Solution:** Open `config/api_keys.json` and ensure your keys start with `AIzaSy...` (Gemini) and `gsk_...` (Groq). Both keys are free to acquire.

### Q4: Smart Island is not appearing on screen
- **Cause:** PyQt6 window manager initialization delayed or overlay hidden off-screen.
- **Solution:** Run `python smart_island.py` directly in a terminal to verify standalone rendering, or check screen resolution settings in multi-monitor setups.

### Q5: How do I completely wipe all memory and start fresh?
- **Solution:** Simply delete the `data/` and `memory/storage/` folders. ANSH will recreate clean, factory-default directories upon next launch.

---

## 12. Support & Contact

- **Lead Architect & Developer:** **Anshu Dubey**
- **Commercial Licensing & Activation Portal:** [https://getyoursoft.page.gd](https://getyoursoft.page.gd)
- **GitHub Repository:** [https://github.com/mastgamerz37-ux/ansh-ai](https://github.com/mastgamerz37-ux/ansh-ai)
