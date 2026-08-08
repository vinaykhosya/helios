"""
automation/sessions/manager.py

Helios Portal Session Manager.
- Manages Playwright `storageState` authentication cookies & local storage in data/sessions/<portal>.json.
- Maintains structured metadata in data/sessions/metadata.json (created_at, last_validated_at, auth_state, expires_at).
- Validates active sessions before application flows, falling back to OS Vault auto-login when expired.
"""
import os
import json
import time
from typing import Optional, Dict, Any

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "sessions")
METADATA_FILE = os.path.join(SESSIONS_DIR, "metadata.json")


class PortalSessionManager:
    def __init__(self, sessions_dir: str = SESSIONS_DIR):
        self.sessions_dir = sessions_dir
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.metadata_file = os.path.join(self.sessions_dir, "metadata.json")

    def _read_metadata(self) -> dict:
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _write_metadata(self, data: dict):
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_state_file_path(self, portal: str) -> str:
        portal_key = portal.lower().strip()
        return os.path.join(self.sessions_dir, f"{portal_key}.json")

    async def save_session(self, context, portal: str, auth_state: str = "authenticated") -> str:
        """Saves Playwright storageState context cookies and updates metadata."""
        portal_key = portal.lower().strip()
        state_file = self.get_state_file_path(portal_key)

        # Save Playwright storageState
        await context.storage_state(path=state_file)

        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        meta = self._read_metadata()
        meta[portal_key] = {
            "portal": portal_key,
            "created_at": meta.get(portal_key, {}).get("created_at", now_str),
            "last_validated_at": now_str,
            "last_used_at": now_str,
            "auth_state": auth_state,
            "state_file": state_file
        }
        self._write_metadata(meta)
        return state_file

    def get_session_metadata(self, portal: str) -> Optional[Dict[str, Any]]:
        portal_key = portal.lower().strip()
        meta = self._read_metadata()
        return meta.get(portal_key)

    def get_storage_state_path_if_valid(self, portal: str) -> Optional[str]:
        """Returns storageState path if file exists and metadata is marked authenticated."""
        portal_key = portal.lower().strip()
        state_file = self.get_state_file_path(portal_key)
        
        if not os.path.exists(state_file):
            return None

        meta = self.get_session_metadata(portal_key)
        if meta and meta.get("auth_state") == "authenticated":
            return state_file
        
        return None

    def invalidate_session(self, portal: str):
        """Marks portal session as EXPIRED."""
        portal_key = portal.lower().strip()
        meta = self._read_metadata()
        if portal_key in meta:
            meta[portal_key]["auth_state"] = "expired"
            meta[portal_key]["last_validated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            self._write_metadata(meta)

    def list_all_sessions(self) -> dict:
        return self._read_metadata()
