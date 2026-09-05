"""
core/authentication.py — Security State Machine & Authentication Manager for ANSH

Coordinates speaker verification, password authentication, enrollment, session timeouts,
and authentication state transitions.
"""
from __future__ import annotations

import time
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Tuple

from core.speaker_verification import SpeakerVerifier
from core.voice_enrollment import VoiceEnrollmentEngine
from core.password_manager import PasswordManager
from config.security_config import (
    AUTH_SESSION_TIMEOUT,
    VOICE_VERIFICATION_THRESHOLD,
    OWNER_PROFILE_PATH,
    SECURITY_CONFIG_PATH,
)


class AuthState(Enum):
    UNENROLLED            = auto()
    LOCKED                = auto()
    LISTENING             = auto()
    VERIFYING_VOICE       = auto()
    OWNER_AUTHENTICATED   = auto()
    PASSWORD_REQUIRED     = auto()
    VERIFYING_PASSWORD    = auto()
    SESSION_AUTHENTICATED = auto()
    ACCESS_DENIED         = auto()


class AuthenticationManager:
    """
    Core Security & Speaker Authentication Manager.
    """

    def __init__(
        self,
        profile_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        session_timeout: float = AUTH_SESSION_TIMEOUT,
        verification_threshold: float = VOICE_VERIFICATION_THRESHOLD,
    ):
        p_path = profile_path or OWNER_PROFILE_PATH
        c_path = config_path or SECURITY_CONFIG_PATH

        self.verifier = SpeakerVerifier(owner_profile_path=p_path, threshold=verification_threshold)
        self.enrollment = VoiceEnrollmentEngine(profile_path=p_path)
        self.password_mgr = PasswordManager(config_path=c_path)

        self.session_timeout = session_timeout
        self.authenticated_until: float = 0.0
        self.current_state: AuthState = AuthState.LOCKED

        # Set default password if none is set
        if not self.password_mgr.is_password_set():
            self.password_mgr.set_password("anshu123")

        self.update_state()

    def update_state(self) -> AuthState:
        """
        Refreshes security state and handles session expirations.
        """
        # If no owner voice profile exists -> UNENROLLED
        if self.verifier.owner_embedding is None:
            self.current_state = AuthState.UNENROLLED
            return self.current_state

        # Check if an authenticated session is active
        now = time.monotonic()
        if now < self.authenticated_until:
            if self.current_state != AuthState.OWNER_AUTHENTICATED:
                self.current_state = AuthState.SESSION_AUTHENTICATED
            return self.current_state

        # If session expired or locked
        if self.current_state not in (AuthState.PASSWORD_REQUIRED, AuthState.VERIFYING_PASSWORD, AuthState.ACCESS_DENIED):
            self.current_state = AuthState.LOCKED

        return self.current_state

    def process_voice_input(self, audio_pcm: bytes, sample_rate: int = 16000) -> Tuple[AuthState, str]:
        """
        Processes audio frame through Speaker Verification pipeline.
        Returns: (state: AuthState, detail_message: str)
        """
        self.update_state()

        if self.current_state == AuthState.UNENROLLED:
            ok, msg = self.enrollment.add_sample(audio_pcm, sample_rate=sample_rate)
            if ok and self.enrollment.is_complete():
                if self.enrollment.save_owner_profile():
                    self.verifier.reload_profile()
                    self.current_state = AuthState.LOCKED
                    return AuthState.LOCKED, "Owner voice enrolled successfully!"
            return AuthState.UNENROLLED, msg

        if self.current_state in (AuthState.SESSION_AUTHENTICATED, AuthState.OWNER_AUTHENTICATED):
            return self.current_state, "Session Active"

        self.current_state = AuthState.VERIFYING_VOICE
        identity, similarity = self.verifier.verify_speaker(audio_pcm, sample_rate=sample_rate)

        if identity == "OWNER":
            self.authenticated_until = time.monotonic() + self.session_timeout
            self.current_state = AuthState.OWNER_AUTHENTICATED
            print(f"[Security] OWNER VERIFIED (similarity: {similarity:.2f})")
            return AuthState.OWNER_AUTHENTICATED, "Owner verified"

        elif identity == "UNKNOWN":
            self.current_state = AuthState.PASSWORD_REQUIRED
            print(f"[Security] UNKNOWN SPEAKER DETECTED (similarity: {similarity:.2f}) -> PASSWORD_REQUIRED")
            return AuthState.PASSWORD_REQUIRED, "Password batao."

        else:
            # NO_SPEECH or silence
            self.current_state = AuthState.LOCKED
            return AuthState.LOCKED, "No speech"

    def submit_password(self, spoken_or_entered_text: str) -> bool:
        """
        Verifies spoken/entered password.
        If correct -> SESSION_AUTHENTICATED.
        If wrong -> ACCESS_DENIED & LOCKED (SILENT).
        """
        if self.current_state != AuthState.PASSWORD_REQUIRED:
            return False

        self.current_state = AuthState.VERIFYING_PASSWORD
        verified = self.password_mgr.verify_password(spoken_or_entered_text)

        if verified:
            self.authenticated_until = time.monotonic() + self.session_timeout
            self.current_state = AuthState.SESSION_AUTHENTICATED
            print("[Security] PASSWORD VERIFIED -> SESSION_AUTHENTICATED")
            return True
        else:
            self.authenticated_until = 0.0
            self.current_state = AuthState.ACCESS_DENIED
            print("[Security] WRONG PASSWORD -> ACCESS_DENIED (SILENT LOCKOUT)")
            # Transition to LOCKED for silent monitoring
            self.current_state = AuthState.LOCKED
            return False

    def is_authenticated(self) -> bool:
        """
        Returns True if current speaker is verified Owner or Active Session.
        """
        state = self.update_state()
        return state in (AuthState.OWNER_AUTHENTICATED, AuthState.SESSION_AUTHENTICATED)

    def is_owner(self) -> bool:
        """
        Returns True if current state is explicitly OWNER_AUTHENTICATED.
        """
        return self.current_state == AuthState.OWNER_AUTHENTICATED

    def re_enroll_owner_voice(self) -> bool:
        """
        Deletes stored profile and transitions to UNENROLLED.
        """
        self.enrollment.delete_profile()
        self.verifier.owner_embedding = None
        self.authenticated_until = 0.0
        self.current_state = AuthState.UNENROLLED
        print("[Security] Owner voice profile reset. Re-enrollment required.")
        return True

    def delete_owner_profile(self) -> bool:
        """
        Deletes stored voice profile.
        """
        return self.re_enroll_owner_voice()

    def change_password(self, new_password: str) -> bool:
        """
        Updates the stored security password hash.
        """
        return self.password_mgr.set_password(new_password)
