from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

try:
    import keyring
except ImportError:
    keyring = None

from dotenv import dotenv_values, set_key as dotenv_set_key, unset_key as dotenv_unset_key


class CredentialStore:
    def __init__(self, service_name: str = "harness-agent", env_file: Optional[Path] = None):
        self.service = service_name
        self.env_file = env_file or Path.cwd() / ".env"

    def store(self, key: str, value: str):
        if keyring:
            try:
                keyring.set_password(self.service, key, value)
                return
            except Exception:
                pass
        self.env_file.parent.mkdir(parents=True, exist_ok=True)
        self.env_file.touch(mode=0o600)
        os.chmod(self.env_file, 0o600)
        dotenv_set_key(str(self.env_file), key, value)

    def load(self, key: str) -> Optional[str]:
        if keyring:
            try:
                val = keyring.get_password(self.service, key)
                if val is not None:
                    return val
            except Exception:
                pass
        if self.env_file.exists():
            values = dotenv_values(str(self.env_file))
            return values.get(key)
        return os.getenv(key)

    def delete(self, key: str):
        if keyring:
            try:
                keyring.delete_password(self.service, key)
                return
            except Exception:
                pass
        if self.env_file.exists():
            dotenv_unset_key(str(self.env_file), key)

    def status(self, key: str) -> str:
        val = self.load(key)
        return "stored" if val is not None else "not_set"