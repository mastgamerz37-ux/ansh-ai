# ANSH — Your Own AI Friend: Complete Documentation
### Developer: Anshu Dubey | Product Website: https://getyoursoft.page.gd

---

## 📖 Introduction & System Overview

**ANSH** is a real-time, cross-platform personal AI partner engineered by **Anshu Dubey**. Built on top of the **Gemini Live API** for expressive audio streaming and **Groq** for System 2 multi-step autonomous goal planning, ANSH provides zero-latency voice interaction, visual screen intelligence, desktop automation, and long-term memory.

---

## 🔑 Commercial Licensing & 3-Day Free Trial

ANSH includes a built-in commercial licensing and trial management system ([`core/license_manager.py`](file:///d:/ansh/core/license_manager.py)):

### 1. 3-Day Free Trial
- Upon first launch, users receive **72 hours (3 days) of unrestricted free trial access**.
- Trial status and remaining time are continuously calculated and displayed in the application HUD log.

### 2. Product Key Activation
- Once the 3-day trial expires, ANSH locks full application access and opens the **Product Activation Dialog**.
- Users can click **"Get Product Key"** to visit [https://getyoursoft.page.gd](https://getyoursoft.page.gd) to purchase or request an activation key.
- Product keys follow the format: `ANSH-XXXX-XXXX-XXXX`.

---

## 🧠 System Architecture & Core Modules

```
ANSH/
├── main.py                  # Core loop — Gemini Live session, audio I/O, tool dispatch
├── ui.py                    # PyQt6 HUD — waveform, log panel, activation dialog, camera feed
├── smart_island.py          # Dynamic Desktop Smart Island overlay widget
├── build_exe.py             # PyInstaller executable builder
├── docs/
│   └── DOCUMENTATION.md     # Full comprehensive production documentation
├── core/
│   ├── agi_planner.py       # System 2 multi-step autonomous planner & reflection engine
│   ├── agi_memory.py        # Semantic memory & active goal tracking
│   ├── agi_proactive.py     # Proactive context monitoring engine
│   ├── license_manager.py   # 3-Day free trial & activation engine
│   ├── task_llm.py          # Dual AI dispatcher (Groq + Gemini)
│   └── prompt.txt           # Assistant personality and routing protocol
├── memory/                  # Authoritative Markdown knowledge store
└── config/
    └── api_keys.json        # Configuration template
```

---

## 🚀 Key Features

### 1. Autonomous System 2 Reasoning Engine ([`core/agi_planner.py`](file:///d:/ansh/core/agi_planner.py))
- Decomposes high-level goals into sequential action plans.
- Self-reflection & error recovery: automatically analyzes failure tracebacks and formulates alternative tool calls.

### 2. Long-Term Semantic Memory ([`core/agi_memory.py`](file:///d:/ansh/core/agi_memory.py))
- Automatically extracts user facts, preferences, and project context during conversation turns.
- Persists knowledge across application restarts in structured Markdown storage.

### 3. Proactive Intelligence 2.0 ([`core/agi_proactive.py`](file:///d:/ansh/core/agi_proactive.py))
- Monitors screen content, system hardware load, clipboard snippets, and time context.
- Initiates proactive check-ins when silence or relevant background events occur.

---

## 🛠️ Building Standalone Executables (.exe)

To package ANSH into a single standalone `.exe` installer:

```bash
python build_exe.py
```

Any code changes made in `main.py`, `core/`, `actions/`, `memory/`, or `ui.py` are automatically compiled into `dist/ansh.exe`.

---

## 👤 Developer & Support

- **Developer**: **Anshu Dubey**
- **Activation & Keys Website**: [https://getyoursoft.page.gd](https://getyoursoft.page.gd)
