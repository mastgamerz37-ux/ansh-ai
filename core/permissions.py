"""
core/permissions.py — Permission Control Layer for ANSH

Enforces granular permission levels (PUBLIC, AUTHENTICATED, OWNER_ONLY)
for tool execution and sensitive system operations.
"""
from __future__ import annotations

from enum import Enum, auto
from typing import Dict


class PermissionLevel(Enum):
    PUBLIC        = auto()
    AUTHENTICATED = auto()
    OWNER_ONLY    = auto()


# Mapping tool declarations to required permission levels
TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
    # Public (Anyone can ask general queries if system is unmuted)
    "weather":           PermissionLevel.PUBLIC,
    "web_search":        PermissionLevel.PUBLIC,
    "interactive_game":  PermissionLevel.PUBLIC,
    "list_memories":     PermissionLevel.PUBLIC,

    # Authenticated (Requires active session or Owner verification)
    "open_app":          PermissionLevel.AUTHENTICATED,
    "youtube_video":     PermissionLevel.AUTHENTICATED,
    "reminder":          PermissionLevel.AUTHENTICATED,
    "send_email":        PermissionLevel.AUTHENTICATED,
    "send_message":      PermissionLevel.AUTHENTICATED,
    "read_messages":      PermissionLevel.AUTHENTICATED,
    "whatsapp_call":     PermissionLevel.AUTHENTICATED,
    "whatsapp_auto_reply": PermissionLevel.AUTHENTICATED,
    "flight_finder":     PermissionLevel.AUTHENTICATED,
    "generate_document": PermissionLevel.AUTHENTICATED,
    "browser_control":   PermissionLevel.AUTHENTICATED,
    "ai_wallpaper":      PermissionLevel.AUTHENTICATED,
    "save_memory":       PermissionLevel.AUTHENTICATED,
    "search_memory":     PermissionLevel.AUTHENTICATED,
    "forget_memory":     PermissionLevel.AUTHENTICATED,

    # Owner-Only (Strictly requires fresh Owner Voice Verification)
    "file_controller":   PermissionLevel.OWNER_ONLY,
    "computer_settings": PermissionLevel.OWNER_ONLY,
    "computer_control":  PermissionLevel.OWNER_ONLY,
    "desktop":           PermissionLevel.OWNER_ONLY,
    "dev_agent":         PermissionLevel.OWNER_ONLY,
    "code_helper":       PermissionLevel.OWNER_ONLY,
    "deploy_wormhole":   PermissionLevel.OWNER_ONLY,
    "shutdown_ansh":     PermissionLevel.OWNER_ONLY,
    "restart_ansh":      PermissionLevel.OWNER_ONLY,
    "re_enroll_voice":   PermissionLevel.OWNER_ONLY,
    "delete_voice_profile": PermissionLevel.OWNER_ONLY,
    "change_password":   PermissionLevel.OWNER_ONLY,
}


def check_tool_permission(tool_name: str, is_owner: bool, is_authenticated: bool) -> bool:
    """
    Evaluates whether the current caller identity is permitted to execute tool_name.
    """
    required = TOOL_PERMISSIONS.get(tool_name, PermissionLevel.AUTHENTICATED)

    if required == PermissionLevel.PUBLIC:
        return True
    if required == PermissionLevel.AUTHENTICATED:
        return is_authenticated or is_owner
    if required == PermissionLevel.OWNER_ONLY:
        return is_owner

    return False


def get_tool_permission(tool_name: str) -> PermissionLevel:
    """Returns required PermissionLevel for a tool."""
    return TOOL_PERMISSIONS.get(tool_name, PermissionLevel.AUTHENTICATED)
