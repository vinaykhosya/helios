"""
tests/test_credentials.py

Unit tests for Helios Encrypted Credential Vault.
"""
import os
import tempfile
import pytest
from cryptography.fernet import Fernet, InvalidToken
from automation.sessions.credentials import EncryptedCredentialVault


def test_credential_vault_encrypt_decrypt():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_file = os.path.join(tmpdir, "vault.json")
        key = Fernet.generate_key()
        vault = EncryptedCredentialVault(vault_file=vault_file, master_key=key)

        # Store credentials for Siemens portal
        vault.set_credential("siemens", "candidate@nsut.ac.in", "SecretPass123!")

        # Retrieve credentials
        creds = vault.get_credential("siemens")
        assert creds is not None
        assert creds["username"] == "candidate@nsut.ac.in"
        assert creds["password"] == "SecretPass123!"


def test_credential_vault_metadata_redaction():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_file = os.path.join(tmpdir, "vault.json")
        key = Fernet.generate_key()
        vault = EncryptedCredentialVault(vault_file=vault_file, master_key=key)

        vault.set_credential("bosch", "vinay.khosya@nsut.ac.in", "MyPassword456!")

        metadata = vault.list_credentials_metadata()
        assert len(metadata) == 1
        assert metadata[0]["portal"] == "bosch"
        assert metadata[0]["username_redacted"] == "vi***@nsut.ac.in"
        # Ensure password is NEVER in metadata
        assert "password" not in metadata[0]
        assert "MyPassword456!" not in str(metadata)


def test_credential_vault_invalid_key():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_file = os.path.join(tmpdir, "vault.json")
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        vault1 = EncryptedCredentialVault(vault_file=vault_file, master_key=key1)
        vault1.set_credential("ey", "vinay@nsut.ac.in", "EYSecret789!")

        # Attempt to decrypt using key2
        vault2 = EncryptedCredentialVault(vault_file=vault_file, master_key=key2)
        creds = vault2.get_credential("ey")
        assert creds is None  # Decryption failure gracefully returns None
