"""
core/voice_enrollment.py — Owner Voice Enrollment Engine for ANSH

Collects multiple valid voice samples from the owner, validates audio quality,
and computes a normalized average speaker profile stored in data/secure/owner_voice_profile.npz.
"""
from __future__ import annotations

import os
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple

from core.speaker_verification import extract_speaker_embedding, detect_voice_activity
from config.security_config import OWNER_PROFILE_PATH, TARGET_ENROLLMENT_SAMPLES


class VoiceEnrollmentEngine:
    """
    Manages owner voice enrollment workflow.
    """

    def __init__(self, target_samples: int = TARGET_ENROLLMENT_SAMPLES, profile_path: Optional[Path] = None):
        self.target_samples = target_samples
        self.profile_path = profile_path or OWNER_PROFILE_PATH
        self.collected_embeddings: List[np.ndarray] = []

    def reset(self):
        """Resets currently collected samples."""
        self.collected_embeddings.clear()

    def add_sample(self, audio_pcm: bytes, sample_rate: int = 16000) -> Tuple[bool, str]:
        """
        Validates and registers one speech sample.
        Returns: (success: bool, status_message: str)
        """
        if not audio_pcm or len(audio_pcm) < 6400:  # < 0.4s @ 16kHz 16-bit
            return False, "Sample rejected: Audio sample too short. Please speak clearly for at least 1-2 seconds."

        if not detect_voice_activity(audio_pcm):
            return False, "Sample rejected: Silence, background fan, or ambient noise detected."

        emb = extract_speaker_embedding(audio_pcm, sample_rate=sample_rate)
        if emb is None:
            return False, "Sample rejected: Could not extract clear acoustic voice features."

        # If we already have samples, verify consistency with previous samples
        if self.collected_embeddings:
            prev_avg = np.mean(self.collected_embeddings, axis=0)
            prev_avg /= np.linalg.norm(prev_avg)
            sim = float(np.dot(prev_avg, emb))
            if sim < 0.70:
                return False, "Sample rejected: Voice sample inconsistent with previous samples. Speak naturally."

        self.collected_embeddings.append(emb)
        count = len(self.collected_embeddings)
        return True, f"Sample {count}/{self.target_samples} accepted successfully!"

    def is_complete(self) -> bool:
        """Returns True if target sample count is reached."""
        return len(self.collected_embeddings) >= self.target_samples

    def save_owner_profile(self) -> bool:
        """
        Averages collected sample embeddings, normalizes, and saves binary NPZ profile.
        """
        if not self.is_complete():
            print("[Enrollment] Cannot save: Enrollment incomplete.")
            return False

        try:
            self.profile_path.parent.mkdir(parents=True, exist_ok=True)
            avg_embedding = np.mean(self.collected_embeddings, axis=0)
            norm = np.linalg.norm(avg_embedding)
            if norm > 0:
                avg_embedding = avg_embedding / norm

            np.savez_compressed(str(self.profile_path), embedding=avg_embedding)
            print(f"[Enrollment] Owner voice profile saved successfully to: {self.profile_path}")
            return True
        except Exception as e:
            print(f"[Enrollment] Failed to save voice profile: {e}")
            return False

    def delete_profile(self) -> bool:
        """
        Deletes the stored owner voice profile and resets internal state.
        """
        self.reset()
        try:
            if self.profile_path.exists():
                self.profile_path.unlink()
                print(f"[Enrollment] Owner voice profile deleted: {self.profile_path}")
                return True
        except Exception as e:
            print(f"[Enrollment] Failed to delete voice profile: {e}")
        return False
