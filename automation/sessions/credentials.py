"""
automation/sessions/credentials.py

Helios Encrypted Credential Vault.
- Authenticated symmetric encryption using Fernet (AES-128-CBC + HMAC-SHA256).
- Vault Master Key stored via Windows Credential Manager using OS `keyring` (service name: "helios_vault").
- Development fallback via HELIOS_VAULT_KEY in .env.
- Persists ONLY encrypted payload blobs to data/credentials/vault.json.
- REST API / Log Safety: Exposes metadata ONLY (portal, username_redacted, authenticated status).
"""
import os
import json
import base64
from typing import Optional, Dict, List
from cryptography.fernet import Fernet
import keyring

SERVICE_NAME = "helios_vault"
KEY_NAME = "master_key"
VAULT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "credentials", "vault.json")


def _get_or_create_master_key() -> bytes:
    """Retrieves master Fernet key from OS keyring (or env fallback), generating one if missing."""
    key_str = keyring.get_password(SERVICE_NAME, KEY_NAME)
    
    if not key_str:
        key_str = os.getenv("HELIOS_VAULT_KEY")

    if not key_str:
        # Generate new Fernet key (32 URL-safe base64-encoded bytes)
        new_key = Fernet.generate_key()
        key_str = new_key.decode("utf-8")
        try:
            keyring.set_password(SERVICE_NAME, KEY_NAME, key_str)
        except Exception:
            pass

    return key_str.encode("utf-8")


class EncryptedCredentialVault:
    def __init__(self, vault_file: str = VAULT_FILE, master_key: Optional[bytes] = None):
        self.vault_file = vault_file
        os.makedirs(os.path.dirname(self.vault_file), exist_ok=True)
        
        self.master_key = master_key or _get_or_create_master_key()
        self.cipher = Fernet(self.master_key)

    def _read_vault(self) -> dict:
        if os.path.exists(self.vault_file):
            try:
                with open(self.vault_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _write_vault(self, data: dict):
        with open(self.vault_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def set_credential(self, portal: str, username: str, password: str) -> bool:
        """Encrypts and stores username and password for a company portal."""
        portal_key = portal.lower().strip()
        payload = json.dumps({"username": username, "password": password}).encode("utf-8")
        encrypted_bytes = self.cipher.encrypt(payload)
        
        vault = self._read_vault()
        vault[portal_key] = {
            "portal": portal_key,
            "username_redacted": username[:2] + "***" + username[username.find("@"):] if "@" in username else username[:2] + "***",
            "encrypted_payload": encrypted_bytes.decode("utf-8")
        }
        self._write_vault(vault)
        return True

    def get_credential(self, portal: str) -> Optional[Dict[str, str]]:
        """Decrypts and returns username and password for a company portal."""
        portal_key = portal.lower().strip()
        vault = self._read_vault()
        
        if portal_key not in vault:
            return None

        encrypted_str = vault[portal_key].get("encrypted_payload", "")
        if not encrypted_str:
            return None

        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_str.encode("utf-8"))
            return json.loads(decrypted_bytes.decode("utf-8"))
        except Exception:
            return None

    def delete_credential(self, portal: str) -> bool:
        portal_key = portal.lower().strip()
        vault = self._read_vault()
        if portal_key in vault:
            del vault[portal_key]
            self._write_vault(vault)
            return True
        return False

    def list_credentials_metadata(self) -> List[Dict[str, str]]:
        """Returns ONLY safe metadata for dashboard display (NO passwords)."""
        vault = self._read_vault()
        res = []
        for portal_key, meta in vault.items():
            res.append({
                "portal": portal_key,
                "username_redacted": meta.get("username_redacted", "***"),
                "has_credentials": True
            })
        return res
