# Changelog — ANSH: Your Own AI Friend

All notable changes to the **ANSH** personal AI system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.5.0] - 2026-09-11 (Master Upgrade & Zero-Dependency Native Audio Engine)

### 🚀 Highlights
- **Zero-Dependency Native Voice Engine**: Completely removed `scipy` dependency, eliminating Windows 11 Smart App Control / Defender Application Control DLL blocking errors (`_minpack.pyd` / `_lsap.pyd`).
- **Dynamic Desktop Smart Island**: Modern floating pill overlay providing real-time visual status, waveform animations, and proactive notifications.
- **Multi-Agent Hub & Autonomous Sub-Agents**: Specialized roles for coding, web browsing, system control, phone gateway, and screen remoting.
- **Affective Emotional Intelligence**: Real-time user sentiment tracking, personality modes (Developer, Casual, JARVIS, Mentor), and referential pronoun resolution.
- **Enterprise Safety & Shadow Rollback Engine**: Pre-execution risk assessment, automated file snapshots in `data/shadow_backups/`, and one-click undo rollback.

### 🌟 Added
- **Pure NumPy Vectorized STFT (`core/speaker_verification.py`)**:
  - Implemented high-performance Short-Time Fourier Transform (`_stft_numpy`) utilizing `np.fft.rfft` and periodic Hamming windowing.
  - Exactly matched scipy's spectral normalization scaling (`1 / win.sum()`), ensuring speaker identification verification accuracy across acoustic environments.
- **Desktop Smart Island (`smart_island.py`, `dashboard/static/smart_island.html`)**:
  - Compact, non-intrusive floating overlay for active task status, voice waveform states, and system notifications.
- **Multi-Agent Hub (`core/multi_agent_hub.py`)**:
  - Dynamic agent routing: Coding Agent, Browser Agent, Telemetry Agent, System Controller, Phone Gateway, and Remote Screen Controller.
- **Affective Engine (`core/affective_engine.py`)**:
  - Real-time sentiment classification (`FRUSTRATED_STRESSED`, `JOYFUL_CASUAL`, `FOCUSED_NEUTRAL`).
  - Personality switcher: Developer mode, Casual Bro mode, JARVIS/Iron Man mode, Mentor mode.
  - Referential pronoun resolver (e.g., resolving *"isko chalao"* or *"run this"* to the active IDE window or file).
- **Security & Safety Engine (`core/security_engine.py`)**:
  - Risk categorization: Low, Medium, High, Critical.
  - Automatic shadow backup snapshots prior to any destructive file modification (`data/shadow_backups/`).
  - `undo_rollback` capability allowing instant restoration of previous file versions.
  - Emergency killswitch functionality.
- **Teach ANSH Workflow Engine (`data/workflows/custom_workflows.json`)**:
  - Interactive demonstration recording mode to capture repeated user tasks and replay them on demand.
- **Study & Learning Engine (`data/study/study_progress.json`)**:
  - Automated study note compilation, doubt resolution, customized quiz generation, and learning progress metrics.
- **Knowledge Graph & World State (`memory/knowledge_graph.py`, `data/memory/knowledge_graph.json`, `data/memory/world_state.json`)**:
  - Multi-hop entity relationship storage and querying.
- **Multimodal Store & Context Continuation (`memory/multimodal_store.py`)**:
  - Cross-session checkpoints, visual index caching, and conversation continuation across restarts.
- **Local Offline SLM Reliability Layer**:
  - Automatic connectivity detection and graceful degradation to local offline task handling when internet access is unavailable.
- **Pub-Sub Event Bus (`data/logs/events.jsonl`)**:
  - Structured event dispatching and telemetry history logging.
- **Complete Legal & User Documentation Suite (`docs/`)**:
  - Added comprehensive `DOCUMENTATION.md`, `PRIVACY_POLICY.md`, `TERMS_AND_CONDITIONS.md`, `REFUND_POLICY.md`, and `CHANGELOG.md`.

### 🔧 Changed & Improved
- Vectorized Mel Filterbank (`_FBANK`) and DCT-II matrix (`_DCT_MAT`) execution in `core/speaker_verification.py` now runs in sub-millisecond execution time.
- Updated `release_app/` distribution files to match the pure NumPy audio engine.
- Enhanced `tests/test_voice_auth.py` and `tests/test_master_upgrade.py` with 100% test passing verification.

---

## [2.0.0] - 2026-08-20 (System 2 AGI Planner & Multimodal Overhaul)

### 🌟 Added
- **Autonomous System 2 AGI Planner (`core/agi_planner.py`)**:
  - Goal decomposition engine that breaks complex natural language requests into sequential action steps.
  - Self-reflection feedback loop: automatically catches tool failure tracebacks and formulates alternative action plans.
- **Dual-Model Routing Engine (`core/task_llm.py`)**:
  - High-speed Groq API integration (`llama-3.3-70b-versatile` / `deepseek-r1-distill-llama-70b`) for instantaneous planning and reasoning.
  - Gemini 3.1 Flash Live preview integration for real-time conversational voice streaming.
- **Proactive Intelligence 2.0 (`core/agi_proactive.py`)**:
  - Contextual monitoring of screen content, clipboard changes, and hardware spikes.
  - Proactive assistance prompts triggered during coding errors or user hesitation.
- **Screen Peeler Vision Action (`actions/screen_peeler.py`)**:
  - High-speed screenshot capture and visual element OCR analysis.
- **Phone Hub & Wormhole (`actions/phone_hub.py`, `actions/wormhole.py`)**:
  - Cross-device notification sync, remote phone actions, and cloud file transfer.
- **Interactive Games Action (`actions/interactive_games.py`)**:
  - Trivia, word games, and interactive voice entertainment modes.

---

## [1.5.0] - 2026-07-15 (Voice Biometrics & Commercial Licensing)

### 🌟 Added
- **Biometric Speaker Verification (`core/speaker_verification.py`, `core/voice_enrollment.py`)**:
  - 5-sample owner voice enrollment procedure.
  - 26-dimensional MFCC feature embedding vector extraction with cosine similarity matching.
  - Lightning-fast Voice Activity Detection (VAD).
- **Commercial Licensing & Trial System (`core/license_manager.py`)**:
  - 3-day (72-hour) free unrestricted evaluation trial.
  - Commercial product key validation modal (`ANSH-XXXX-XXXX-XXXX`).
  - Hardware binding and trial timer persistence.
- **Password Fallback Layer (`core/password_manager.py`)**:
  - PBKDF2/SHA-256 salted password hashing and spoken password normalization (e.g., converting *"One Two Three"* to *"123"*).
- **Futuristic PyQt6 HUD Interface (`ui.py`)**:
  - Animated audio waveform bars.
  - Real-time terminal log viewer.
  - Live webcam preview thumbnail.
  - Activation dialog with direct web links to [https://getyoursoft.page.gd](https://getyoursoft.page.gd).
- **Executable Builder (`build_exe.py`) & Inno Setup (`installer/setup.iss`)**:
  - One-click build script to package ANSH into a standalone Windows installer.

---

## [1.0.0] - 2026-06-01 (Initial Genesis Release)

### 🌟 Added
- Initial public release of **ANSH — Your Own AI Friend**.
- Real-time bi-directional audio streaming via Google Gemini Live WebSockets.
- Core action tools: file creation, editing, application launching, web searches, and system telemetry monitoring.
- Authoritative local Markdown memory store (`memory/`).
- Basic prompt engineering for Tony Stark / JARVIS inspired assistant persona.
