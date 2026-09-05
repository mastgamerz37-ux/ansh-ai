"""
core/speaker_verification.py — Ultra-Fast Pure Python Speaker Verification & Audio Feature Extractor for ANSH

Uses pre-computed C-vectorized Mel Filterbank & DCT-II matrices for sub-millisecond feature extraction.
"""
from __future__ import annotations

import os
import math
import numpy as np
from scipy import signal
from pathlib import Path
from typing import Optional, Tuple

from config.security_config import (
    OWNER_PROFILE_PATH,
    VOICE_VERIFICATION_THRESHOLD,
    MIN_SPEECH_DURATION_SEC,
)

# ── Ultra-Fast Vectorized Pre-Computed Transform Matrices ────────────────────
def _init_transform_matrices(n_mels: int = 26, n_mfcc: int = 13, n_fft: int = 512, sample_rate: int = 16000):
    mel_low = 0.0
    mel_high = 2595.0 * np.log10(1.0 + (sample_rate / 2.0) / 700.0)
    mel_points = np.linspace(mel_low, mel_high, n_mels + 2)
    hz_points = 700.0 * (10.0 ** (mel_points / 2595.0) - 1.0)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)

    fbank = np.zeros((n_mels, int(n_fft // 2 + 1)), dtype=np.float32)
    for m in range(1, n_mels + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]

        for k in range(f_m_minus, f_m):
            fbank[m - 1, k] = (k - bin_points[m - 1]) / max(1, (bin_points[m] - bin_points[m - 1]))
        for k in range(f_m, f_m_plus):
            fbank[m - 1, k] = (bin_points[m + 1] - k) / max(1, (bin_points[m + 1] - bin_points[m]))

    # DCT-II matrix: shape (n_mfcc, n_mels)
    n = np.arange(n_mels)
    k = np.arange(n_mfcc)[:, None]
    dct_mat = np.cos(np.pi * k * (n + 0.5) / n_mels).astype(np.float32)

    return fbank, dct_mat

_FBANK, _DCT_MAT = _init_transform_matrices()
# ─────────────────────────────────────────────────────────────────────────────


def detect_voice_activity(audio_pcm: bytes, threshold_db: float = -38.0, min_bytes: int = 640) -> bool:
    """
    Lightning-fast Voice Activity Detector (VAD).
    Determines if PCM frame contains active human speech vs ambient noise/silence.
    """
    if not audio_pcm or len(audio_pcm) < min_bytes:
        return False

    try:
        audio = np.frombuffer(audio_pcm, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio ** 2))
        if rms <= 1.0:
            return False

        db = 20.0 * math.log10(rms / 32768.0)
        if db <= threshold_db:
            return False

        # Zero-crossing rate check to reject pure DC offset or static hum
        zero_crossings = np.nonzero(np.diff(audio >= 0))[0]
        zcr = len(zero_crossings) / float(len(audio))
        if zcr < 0.005 or zcr > 0.48:
            return False

        return True
    except Exception:
        return False


def _compute_mfcc(
    audio_pcm: bytes,
    sample_rate: int = 16000,
    n_mfcc: int = 13,
    n_fft: int = 512,
    hop_length: int = 256
) -> Optional[np.ndarray]:
    """
    Extract MFCC features from 16-bit PCM audio bytes (Sub-millisecond vectorized execution).
    """
    try:
        audio = np.frombuffer(audio_pcm, dtype=np.int16).astype(np.float32)
        if len(audio) < n_fft:
            return None

        # Peak normalization
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val

        # Pre-emphasis filter
        audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1])

        # Short-Time Fourier Transform (STFT)
        frequencies, times, Zxx = signal.stft(
            audio,
            fs=sample_rate,
            nperseg=n_fft,
            noverlap=n_fft - hop_length,
            window="hamming"
        )
        spectrogram = np.abs(Zxx) ** 2

        # Fast Vectorized Mel Filterbank calculation
        filter_banks = np.dot(_FBANK, spectrogram)
        filter_banks = np.maximum(filter_banks, 1e-4)
        filter_banks_db = 20.0 * np.log10(filter_banks)

        # Fast Vectorized Discrete Cosine Transform (DCT-II)
        mfcc = np.dot(_DCT_MAT, filter_banks_db)

        # Mean normalization across frames
        mfcc -= (np.mean(mfcc, axis=1, keepdims=True) + 1e-8)
        return mfcc
    except Exception:
        return None


def extract_speaker_embedding(audio_pcm: bytes, sample_rate: int = 16000) -> Optional[np.ndarray]:
    """
    Computes a fixed 26-dimensional speaker embedding vector
    combining mean & std MFCCs. Performs quality & variance checks.
    """
    try:
        mfcc = _compute_mfcc(audio_pcm, sample_rate=sample_rate)
        if mfcc is None or mfcc.shape[1] < 1:
            return None

        # Check frame variance — multi-speaker or burst noise often causes extreme variance
        frame_vars = np.var(mfcc, axis=0)
        if len(frame_vars) > 1 and np.mean(frame_vars) > 20000.0:
            return None

        mean_vector = np.mean(mfcc, axis=1)
        std_vector = np.std(mfcc, axis=1)

        embedding = np.concatenate([mean_vector, std_vector])
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding
    except Exception:
        return None


class SpeakerVerifier:
    """
    Speaker Verifier instance.
    Loads stored owner profile and verifies incoming audio frames.
    """

    def __init__(self, owner_profile_path: Optional[Path] = None, threshold: float = VOICE_VERIFICATION_THRESHOLD):
        self.threshold = threshold
        self.owner_profile_path = owner_profile_path or OWNER_PROFILE_PATH
        self.owner_embedding: Optional[np.ndarray] = None
        self.reload_profile()

    def reload_profile(self) -> bool:
        """
        Reloads owner voice embedding from disk.
        """
        if self.owner_profile_path and self.owner_profile_path.exists():
            try:
                data = np.load(str(self.owner_profile_path))
                self.owner_embedding = data["embedding"]
                return True
            except Exception as e:
                print(f"[SpeakerVerifier] Failed to load owner profile: {e}")
        self.owner_embedding = None
        return False

    def verify_speaker(self, audio_pcm: bytes, sample_rate: int = 16000) -> Tuple[str, float]:
        """
        Verifies audio against stored owner profile.
        Returns: ("OWNER" | "UNKNOWN" | "NO_SPEECH" | "UNENROLLED", similarity_score)
        """
        try:
            if not detect_voice_activity(audio_pcm):
                return "NO_SPEECH", 0.0

            if self.owner_embedding is None:
                if not self.reload_profile():
                    return "UNENROLLED", 0.0

            sample_embedding = extract_speaker_embedding(audio_pcm, sample_rate=sample_rate)
            if sample_embedding is None:
                return "NO_SPEECH", 0.0

            # Cosine similarity metric
            similarity = float(np.dot(self.owner_embedding, sample_embedding))
            if similarity >= self.threshold:
                return "OWNER", similarity
            return "UNKNOWN", similarity
        except Exception as e:
            print(f"[SpeakerVerifier] Verification error (failing safely): {e}")
            return "UNKNOWN", 0.0
