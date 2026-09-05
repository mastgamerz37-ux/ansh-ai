"""
core/airtouch.py — ANSH AirTouch Camera Vision Engine
Optimized for zero-lag performance, one-shot face snapshot recognition, and long-term memory.
"""
from __future__ import annotations

import os
import json
import time
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any

import cv2
import numpy as np

from memory.memory_service import MemoryService

_SECURE_DIR = Path(__file__).resolve().parent.parent / "data" / "secure"
_FACES_DIR = _SECURE_DIR / "faces"
_KNOWN_FACES_FILE = _SECURE_DIR / "known_faces.json"


def _extract_face_feature(crop_bgr: np.ndarray) -> List[float]:
    """Computes a robust 128-dim normalized spatial-color feature vector for fast face matching."""
    resized = cv2.resize(crop_bgr, (32, 32))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)

    gray_norm = (gray.flatten().astype(np.float32) - 128.0) / 128.0
    hue_norm = (hsv[:, :, 0].flatten().astype(np.float32) - 90.0) / 90.0

    feature = np.concatenate([gray_norm[:64], hue_norm[:64]])
    norm = np.linalg.norm(feature)
    if norm > 0:
        feature = feature / norm
    return feature.tolist()


def _compare_features(feat1: List[float], feat2: List[float]) -> float:
    """Computes similarity between two face feature vectors."""
    if not feat1 or not feat2 or len(feat1) != len(feat2):
        return 0.0
    v1 = np.array(feat1, dtype=np.float32)
    v2 = np.array(feat2, dtype=np.float32)
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))


class AirTouchEngine:
    """
    AirTouch Background Camera Vision Engine.
    Continuous webcam monitoring, one-shot face recognition, and auto-registration to memory.
    """

    _instance: Optional[AirTouchEngine] = None

    @classmethod
    def get_instance(cls) -> AirTouchEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.running = False
        self._thread: Optional[threading.Thread] = None

        self.on_unknown_face: Optional[Callable[[dict], None]] = None
        self.on_known_face: Optional[Callable[[str], None]] = None

        self._lock = threading.Lock()
        self.known_faces: Dict[str, dict] = {}
        self.last_unknown_crop: Optional[np.ndarray] = None
        self.last_unknown_feature: Optional[List[float]] = None
        self.last_unknown_time: float = 0.0
        self.last_recognized_name: Optional[str] = None
        self.last_recognized_time: float = 0.0
        self.cooldown_seconds: float = 25.0

        self._load_known_faces()

    def _load_known_faces(self):
        with self._lock:
            _FACES_DIR.mkdir(parents=True, exist_ok=True)
            if _KNOWN_FACES_FILE.exists():
                try:
                    data = json.loads(_KNOWN_FACES_FILE.read_text(encoding="utf-8"))
                    self.known_faces = data.get("faces", {})
                except Exception as e:
                    print(f"[AirTouch] Load error: {e}")
                    self.known_faces = {}
            else:
                self.known_faces = {}

    def _save_known_faces(self):
        with self._lock:
            try:
                _SECURE_DIR.mkdir(parents=True, exist_ok=True)
                payload = {"faces": self.known_faces}
                _KNOWN_FACES_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[AirTouch] Save error: {e}")

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        print("[AirTouch] Continuous camera vision engine started.")

    def stop(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        print("[AirTouch] Camera vision engine stopped.")

    def _detect_faces_simple(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Fast non-blocking face detector using HSV skin color mask & bounding contours."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 25, 60], dtype=np.uint8)
        upper_skin = np.array([25, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        faces = []
        h_frame, w_frame = frame.shape[:2]

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > (h_frame * w_frame * 0.03):
                x, y, w, h = cv2.boundingRect(cnt)
                aspect = float(w) / float(h)
                if 0.6 <= aspect <= 1.4:
                    faces.append((x, y, w, h))
        return faces

    def _worker_loop(self):
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)
        except Exception:
            cap = None

        if not cap or not cap.isOpened():
            print("[AirTouch] Camera 0 unavailable or in use.")
            self.running = False
            return

        frame_count = 0
        while self.running:
            try:
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.5)
                    continue

                frame_count += 1
                if frame_count % 10 != 0:
                    time.sleep(0.05)
                    continue

                faces = self._detect_faces_simple(frame)
                if not faces:
                    time.sleep(0.15)
                    continue

                now = time.time()
                for (x, y, w, h) in faces:
                    crop = frame[y:y+h, x:x+w]
                    if crop.shape[0] < 35 or crop.shape[1] < 35:
                        continue

                    feat = _extract_face_feature(crop)
                    matched_name = None
                    best_sim = 0.0

                    with self._lock:
                        for name, meta in self.known_faces.items():
                            known_feat = meta.get("features")
                            if known_feat:
                                sim = _compare_features(feat, known_feat)
                                if sim >= 0.65 and sim > best_sim:
                                    best_sim = sim
                                    matched_name = name

                    if matched_name:
                        if now - self.last_recognized_time > 15.0 or self.last_recognized_name != matched_name:
                            self.last_recognized_name = matched_name
                            self.last_recognized_time = now
                            print(f"[AirTouch] Recognized user: {matched_name} (similarity: {best_sim:.2f})")
                            if self.on_known_face:
                                try:
                                    self.on_known_face(matched_name)
                                except Exception:
                                    pass
                    else:
                        if now - self.last_unknown_time > self.cooldown_seconds:
                            self.last_unknown_time = now
                            self.last_unknown_crop = crop
                            self.last_unknown_feature = feat
                            if self.on_unknown_face:
                                try:
                                    self.on_unknown_face({
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                                        "feature": feat,
                                    })
                                except Exception:
                                    pass
                            break
            except Exception as loop_err:
                pass

            time.sleep(0.15)

        if cap:
            try:
                cap.release()
            except Exception:
                pass


    def register_identity(self, person_name: str, relation_or_notes: str = "") -> str:
        """
        One-shot face photo registration:
        Saves face features + snapshot image and stores identity in Long-Term Memory.
        Once registered, this person is recognized instantly without asking again!
        """
        person_name = person_name.strip().title()
        if not person_name:
            return "Please provide a valid person name."

        with self._lock:
            feat = self.last_unknown_feature or []

            # Save snapshot PNG if crop is available
            img_filename = ""
            if self.last_unknown_crop is not None:
                try:
                    _FACES_DIR.mkdir(parents=True, exist_ok=True)
                    safe_name = "".join(c for c in person_name if c.isalnum() or c in (" ", "_")).strip()
                    img_path = _FACES_DIR / f"{safe_name}.png"
                    cv2.imwrite(str(img_path), self.last_unknown_crop)
                    img_filename = img_path.name
                except Exception as e:
                    print(f"[AirTouch] Snapshot save note: {e}")

            self.known_faces[person_name] = {
                "name": person_name,
                "registered": time.strftime("%Y-%m-%d %H:%M"),
                "notes": relation_or_notes or "Recognized person",
                "features": feat,
                "photo": img_filename
            }
            self._save_known_faces()

            # Set as current recognized user so unknown alert resets immediately
            self.last_recognized_name = person_name
            self.last_recognized_time = time.time()

        # Save to Long-Term Memory
        mem_svc = MemoryService.get_instance()
        mem_svc.remember(
            topic=f"Person: {person_name}",
            content=f"{person_name} — {relation_or_notes or 'Registered person recognized by AirTouch camera'}",
            category="relationships",
            importance="High",
            confidence="High"
        )
        return f"Successfully registered face profile and memory for {person_name}!"
