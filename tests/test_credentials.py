import os
import pytest
from unittest.mock import patch
from harness.security.credentials import CredentialStore


@pytest.fixture
def env_store(tmp_path):
    env_file = tmp_path / ".env"
    return CredentialStore(service_name="test-harness", env_file=env_file)


class TestCredentialStore:
    def test_store_and_load_from_env(self, env_store):
        with patch("harness.security.credentials.keyring", None):
            env_store.store("TEST_KEY", "test_value")
            val = env_store.load("TEST_KEY")
            assert val == "test_value"

    def test_load_missing_returns_none(self, env_store):
        val = env_store.load("NONEXISTENT_KEY")
        assert val is None

    def test_delete_from_env(self, env_store):
        with patch("harness.security.credentials.keyring", None):
            env_store.store("DEL_KEY", "value")
            env_store.delete("DEL_KEY")
            assert env_store.load("DEL_KEY") is None

    def test_status_stored(self, env_store):
        with patch("harness.security.credentials.keyring", None):
            env_store.store("STATUS_KEY", "value")
            assert env_store.status("STATUS_KEY") == "stored"

    def test_status_not_set(self, env_store):
        assert env_store.status("MISSING") == "not_set"

    def test_env_file_permissions(self, env_store, tmp_path):
        import stat
        with patch("harness.security.credentials.keyring", None):
            env_store.store("KEY", "value")
        mode = os.stat(env_store.env_file).st_mode
        assert not (mode & stat.S_IROTH)