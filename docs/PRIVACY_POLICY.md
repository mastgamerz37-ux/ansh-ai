# Privacy Policy for ANSH — Your Own AI Friend

**Last Updated:** September 11, 2026  
**Product:** ANSH — Your Own AI Friend  
**Developer & Copyright Holder:** Anshu Dubey  
**Official Website:** [https://getyoursoft.page.gd](https://getyoursoft.page.gd)  

---

## 1. Introduction

Welcome to **ANSH — Your Own AI Friend** ("ANSH", "the Software", "we", "our", or "us"). We are committed to protecting your personal privacy, data sovereignty, and security. ANSH has been architected from the ground up on a **"Local-First, Privacy-by-Design"** philosophy: your sensitive biometric data, passwords, personal memories, and activity logs remain stored locally on your own machine.

This Privacy Policy explains what information ANSH processes, how that data is stored and utilized, what is transmitted to external AI cloud providers (such as the Google Gemini Live API and Groq Cloud), and your rights regarding data control, modification, and deletion.

---

## 2. Information Processed by ANSH

### 2.1 Audio & Voice Biometric Data
- **Voice Enrollment & Speaker Profile:** During voice enrollment, ANSH captures 16-bit 16 kHz PCM audio frames to compute a normalized 26-dimensional mathematical speaker embedding vector.
- **Local Storage of Biometrics:** Your voice embedding vector is stored strictly on your local machine in `data/secure/owner_voice_profile.npz`. Raw audio recordings used during enrollment are **not** uploaded to any external server or sold to third parties.
- **Voice Activity Detection (VAD):** An on-device VAD analyzes root-mean-square (RMS) volume and zero-crossing rates locally in real-time to detect speech vs. background noise.
- **Live Voice Interaction:** When voice interaction is active, incoming microphone audio frames are streamed over an encrypted WebSocket connection directly to the **Google Gemini Live API** to produce conversational responses.

### 2.2 Visual & Screen Data
- **Screen Perception ("Screen Peeler"):** If you request screen assistance or have proactive monitoring enabled, ANSH captures local screen frames using high-speed native capture libraries. Screen frames are analyzed strictly for your active goal and are not retained permanently.
- **Webcam Feed:** If you enable camera input, webcam frames are rendered in your local HUD and can be sent to the Gemini Vision API for multimodal visual question answering. No persistent video archive is created without your explicit direction.

### 2.3 System Telemetry & Clipboard
- **Hardware Monitoring:** ANSH reads local hardware metrics (CPU load, RAM usage, battery levels, network ping, GPU stats) via the local system monitor module (`actions/system_monitor.py`). This data is displayed on your HUD and used to prevent system overheating or degradation.
- **Clipboard Content:** When the Proactive Intelligence Engine or universal clipboard skill is active, ANSH inspects clipboard text to provide contextual suggestions (e.g., summarizing copied links or debugging copied error stack traces).

### 2.4 Semantic Memory & Knowledge Graph
- **Personal Knowledge Store:** Facts, preferences, procedures, and conversation notes you share are saved in human-readable Markdown format within `memory/storage/` and in the local Knowledge Graph (`data/memory/knowledge_graph.json`).
- **Full User Sovereignty:** All memory files are 100% locally editable, viewable, and deletable by you at any time.

### 2.5 Security, Passwords & Audit Logs
- **Password Manager:** Security passwords created to bypass or supplement voice authentication are hashed and salted with PBKDF2/SHA-256 before local persistence in `data/secure/security_config.json`. Plaintext passwords are never stored.
- **Audit Logging:** Tool executions, permission escalations, and security events are recorded in local JSONL files (`data/secure/audit_log.jsonl` and `data/logs/events.jsonl`) for transparency and forensics.

---

## 3. How Data is Transmitted to Third-Party AI Services

To deliver real-time multimodal reasoning and conversational responses, ANSH connects to external AI APIs using industry-standard TLS/SSL encrypted channels:

1. **Google Gemini Live API (`gemini-3.1-flash-live-preview` / `gemini-2.5-flash`):**
   - Transmits real-time audio PCM streams, visual frames (when requested), and text prompts.
   - Operates in accordance with Google's API Terms of Service and Cloud Data Protection guidelines. Google Enterprise API tier does not use customer API data to train foundational models.
2. **Groq Cloud API (`llama-3.3-70b-versatile` / `deepseek-r1-distill-llama-70b`):**
   - Transmits high-level task descriptions for System 2 multi-step reasoning, coding tasks, and autonomous decomposition.
   - Operates over HTTPS; data is ephemeral and discarded following completion of the inference request.
3. **Telegram Bot API (Optional):**
   - If you configure the optional Telegram remote gateway, text messages and authorized commands travel through Telegram's encrypted bot infrastructure to and from your personal account.

---

## 4. Biometric Data Protection & Security Controls

- **No Remote Biometric Database:** We do not operate a central cloud database of user voices or facial profiles. Your voice profile exists exclusively on your device.
- **Pure Native Vectorization:** Audio analysis uses pre-computed mathematical matrices and pure native NumPy transforms. There are no opaque third-party closed-source binaries handling your audio biometrics.
- **Shadow Backups & Undo Rollback:** When automated actions modify files on your computer, the Safety Engine (`core/security_engine.py`) automatically creates temporary shadow snapshots in `data/shadow_backups/` so you can instantly restore previous file versions.

---

## 5. User Rights, Data Control & Deletion

You retain absolute ownership and control over your data:

- **View All Stored Information:** Open your local `d:\ansh\data\` and `d:\ansh\memory\` directories in File Explorer or any text editor to inspect every note, memory triple, profile, and audit log.
- **Delete Specific Memories:** Ask ANSH directly (*"forget my preference for X"*) or manually edit/delete the corresponding `.md` file in `memory/storage/`.
- **Reset Voice Profile:** Delete `data/secure/owner_voice_profile.npz`. ANSH will immediately return to the unenrolled state and prompt for a fresh enrollment.
- **Purge All History:** Delete the `data/` and `memory/storage/` directories to perform a total factory reset of all application state.

---

## 6. Children's Privacy

ANSH is designed for general desktop productivity and educational purposes. We do not knowingly collect or solicit personal information from children under the age of 13 without parental consent.

---

## 7. Changes to This Privacy Policy

We may update this Privacy Policy from time to time to reflect software updates, new capabilities, or regulatory changes. The latest version will always be published in the `docs/` folder of the official repository and on our product website.

---

## 8. Contact & Developer Inquiries

If you have any questions, privacy concerns, or data requests regarding ANSH, please contact:

- **Developer:** Anshu Dubey
- **Product & Activation Website:** [https://getyoursoft.page.gd](https://getyoursoft.page.gd)
- **Repository:** [https://github.com/mastgamerz37-ux/ansh-ai](https://github.com/mastgamerz37-ux/ansh-ai)
