"""
tests/test_voice_auth.py — Comprehensive Unit Tests for Voice Security & Authentication System
"""
import unittest
import numpy as np
from pathlib import Path
import time

from core.speaker_verification import detect_voice_activity, extract_speaker_embedding, SpeakerVerifier
from core.voice_enrollment import VoiceEnrollmentEngine
from core.password_manager import PasswordManager, normalize_password_input
from core.authentication import AuthenticationManager, AuthState
from core.permissions import check_tool_permission, PermissionLevel


class TestVoiceAuthentication(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = Path("scratch/test_secure_dir")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_profile = self.tmp_dir / "owner_voice_profile.npz"
        self.tmp_config = self.tmp_dir / "security_config.json"

        # Cleanup existing test artifacts
        if self.tmp_profile.exists():
            self.tmp_profile.unlink()
        if self.tmp_config.exists():
            self.tmp_config.unlink()

    def tearDown(self):
        if self.tmp_profile.exists():
            self.tmp_profile.unlink()
        if self.tmp_config.exists():
            self.tmp_config.unlink()

    def _generate_pcm(self, voice_type: str = "owner", duration: float = 1.0, sample_rate: int = 16000) -> bytes:
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        if voice_type == "owner":
            # Fundamental 140Hz + formants at 500, 1500 Hz
            signal_arr = (
                0.5 * np.sin(2 * np.pi * 140 * t) +
                0.3 * np.sin(2 * np.pi * 500 * t) +
                0.2 * np.sin(2 * np.pi * 1500 * t)
            )
        else:
            # Different voice profile (320Hz + formants 900, 2800 Hz)
            signal_arr = (
                0.5 * np.sin(2 * np.pi * 320 * t) +
                0.3 * np.sin(2 * np.pi * 900 * t) +
                0.2 * np.sin(2 * np.pi * 2800 * t)
            )
        signal_int16 = (signal_arr / np.max(np.abs(signal_arr)) * 16000).astype(np.int16)
        return signal_int16.tobytes()

    def test_password_manager(self):
        pm = PasswordManager(config_path=self.tmp_config)
        self.assertFalse(pm.is_password_set())

        # Set password
        self.assertTrue(pm.set_password("anshu123"))
        self.assertTrue(pm.is_password_set())

        # Spoken & normalized password checks
        self.assertTrue(pm.verify_password("anshu123"))
        self.assertTrue(pm.verify_password(" ANSHU123 "))

        # Verify wrong password
        self.assertFalse(pm.verify_password("wrongpass"))

    def test_password_input_normalization(self):
        self.assertEqual(normalize_password_input("One Two Three 4"), "1234")
        self.assertEqual(normalize_password_input("ANSHU 123! "), "anshu123")

    def test_speaker_verification_and_vad(self):
        voice_pcm = self._generate_pcm(voice_type="owner", duration=1.0)
        silence_pcm = np.zeros(16000, dtype=np.int16).tobytes()

        # Test VAD
        self.assertTrue(detect_voice_activity(voice_pcm))
        self.assertFalse(detect_voice_activity(silence_pcm))

        # Test feature extraction
        emb_voice = extract_speaker_embedding(voice_pcm)
        self.assertIsNotNone(emb_voice)
        self.assertEqual(len(emb_voice), 26)

    def test_enrollment_workflow(self):
        enrollment = VoiceEnrollmentEngine(target_samples=5, profile_path=self.tmp_profile)
        self.assertFalse(enrollment.is_complete())

        # Add samples
        sample_voice = self._generate_pcm(voice_type="owner", duration=1.0)
        for i in range(5):
            ok, msg = enrollment.add_sample(sample_voice)
            self.assertTrue(ok)

        self.assertTrue(enrollment.is_complete())
        self.assertTrue(enrollment.save_owner_profile())
        self.assertTrue(self.tmp_profile.exists())

        # Verify verifier loads profile
        verifier = SpeakerVerifier(owner_profile_path=self.tmp_profile)
        self.assertIsNotNone(verifier.owner_embedding)

        # Test verification of owner sample
        status, score = verifier.verify_speaker(sample_voice)
        self.assertEqual(status, "OWNER")
        self.assertGreaterEqual(score, verifier.threshold)

        # Test unknown speaker (different harmonic profile)
        other_voice = self._generate_pcm(voice_type="unknown", duration=1.0)
        status_other, score_other = verifier.verify_speaker(other_voice)
        self.assertEqual(status_other, "UNKNOWN")

    def test_auth_manager_state_machine(self):
        auth_mgr = AuthenticationManager(
            profile_path=self.tmp_profile,
            config_path=self.tmp_config,
            session_timeout=1.0  # short timeout for test
        )

        # Initially UNENROLLED because profile does not exist
        self.assertEqual(auth_mgr.current_state, AuthState.UNENROLLED)

        # Enroll owner voice
        sample_voice = self._generate_pcm(voice_type="owner", duration=1.0)
        for _ in range(5):
            state, msg = auth_mgr.process_voice_input(sample_voice)

        # Should transition to LOCKED after enrollment completes
        self.assertEqual(auth_mgr.current_state, AuthState.LOCKED)

        # Process owner voice -> OWNER_AUTHENTICATED
        state, msg = auth_mgr.process_voice_input(sample_voice)
        self.assertEqual(state, AuthState.OWNER_AUTHENTICATED)
        self.assertTrue(auth_mgr.is_owner())
        self.assertTrue(auth_mgr.is_authenticated())

        # Process unknown voice -> PASSWORD_REQUIRED
        other_voice = self._generate_pcm(voice_type="unknown", duration=1.0)
        auth_mgr.authenticated_until = 0.0
        auth_mgr.current_state = AuthState.LOCKED
        state, msg = auth_mgr.process_voice_input(other_voice)
        self.assertEqual(state, AuthState.PASSWORD_REQUIRED)

        # Submit wrong password -> ACCESS_DENIED -> LOCKED
        res = auth_mgr.submit_password("wrong_password")
        self.assertFalse(res)
        self.assertFalse(auth_mgr.is_authenticated())

        # Re-trigger password mode and submit correct password
        auth_mgr.current_state = AuthState.PASSWORD_REQUIRED
        res_ok = auth_mgr.submit_password("anshu123")
        self.assertTrue(res_ok)
        self.assertEqual(auth_mgr.current_state, AuthState.SESSION_AUTHENTICATED)
        self.assertTrue(auth_mgr.is_authenticated())

        # Test session timeout
        time.sleep(1.1)
        self.assertEqual(auth_mgr.update_state(), AuthState.LOCKED)
        self.assertFalse(auth_mgr.is_authenticated())

    def test_permission_layer(self):
        # Public tool
        self.assertTrue(check_tool_permission("web_search", is_owner=False, is_authenticated=False))

        # Authenticated tool
        self.assertFalse(check_tool_permission("open_app", is_owner=False, is_authenticated=False))
        self.assertTrue(check_tool_permission("open_app", is_owner=False, is_authenticated=True))
        self.assertTrue(check_tool_permission("open_app", is_owner=True, is_authenticated=False))

        # Owner-only tool
        self.assertFalse(check_tool_permission("file_controller", is_owner=False, is_authenticated=True))
        self.assertTrue(check_tool_permission("file_controller", is_owner=True, is_authenticated=False))


if __name__ == "__main__":
    unittest.main()
