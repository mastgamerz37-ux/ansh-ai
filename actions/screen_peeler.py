"""
actions/screen_peeler.py — ScreenPeeler (Multimodal AI OCR & Region Extractor) for ANSH

Allows rectangular region selection or full screen snip, performs OCR / multimodal vision,
and copies extracted code/text to system clipboard with notification.
"""
from __future__ import annotations

import io
import os
import sys
import time
import json
import base64
from pathlib import Path
from typing import Optional, Tuple

import mss
from PIL import Image
import pyperclip

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_gemini_api_key() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def capture_region(bbox: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
    """
    Capture bounding box (left, top, right, bottom) or primary monitor if bbox is None.
    """
    with mss.mss() as sct:
        if bbox:
            left, top, right, bottom = bbox
            width = max(1, right - left)
            height = max(1, bottom - top)
            monitor = {"left": left, "top": top, "width": width, "height": height}
        else:
            monitor = sct.monitors[1]  # primary screen

        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return img


def ocr_extract_text(img: Image.Image, prompt: str = "Extract all text and code from this image exactly as shown.") -> str:
    """
    Perform multimodal OCR extraction on the image using Google Gemini API.
    """
    try:
        from google import genai
        from google.genai import types

        api_key = _get_gemini_api_key()
        client = genai.Client(api_key=api_key)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        img_bytes = buf.getvalue()

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                prompt + "\nOutput only the extracted text/code. Do not wrap in conversational fluff.",
            ]
        )
        return (response.text or "").strip()
    except Exception as e:
        print(f"[ScreenPeeler] OCR error: {e}")
        return f"OCR Extraction Error: {e}"


def screen_peeler_action(
    parameters: dict = None,
    player=None,
    speak=None,
) -> str:
    """
    parameters:
        action : 'snip' | 'extract_active_window' | 'extract_full' | 'ocr_clipboard'
        bbox   : [left, top, right, bottom] (optional)
        prompt : optional instruction
    """
    params = parameters or {}
    action = params.get("action", "snip").lower().strip()
    user_prompt = params.get("prompt", "Extract all code and text from this image precisely.")
    bbox = params.get("bbox")

    if player:
        player.write_log(f"[ScreenPeeler] Action: {action}")

    try:
        img = None
        if action == "extract_full" or action == "full":
            img = capture_region(None)
        elif action == "extract_active_window" or action == "window":
            try:
                import pygetwindow as gw
                win = gw.getActiveWindow()
                if win:
                    img = capture_region((win.left, win.top, win.right, win.bottom))
                else:
                    img = capture_region(None)
            except Exception:
                img = capture_region(None)
        else:
            # Default / Snip mode
            if bbox and len(bbox) == 4:
                img = capture_region(tuple(bbox))
            else:
                img = capture_region(None)

        if not img:
            return "Screen capture failed."

        extracted_text = ocr_extract_text(img, prompt=user_prompt)

        if extracted_text and not extracted_text.startswith("OCR Extraction Error"):
            pyperclip.copy(extracted_text)
            if player:
                player.write_log(f"[ScreenPeeler] ✅ {len(extracted_text)} chars copied to clipboard.")
            return f"Successfully extracted {len(extracted_text)} characters and copied to your clipboard.\n\nExtracted content:\n{extracted_text[:300]}..."
        else:
            return f"Extraction result: {extracted_text}"

    except Exception as e:
        print(f"[ScreenPeeler] Failed: {e}")
        return f"ScreenPeeler error: {e}"
