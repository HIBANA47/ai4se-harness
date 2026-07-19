from __future__ import annotations
import getpass
from harness.security.credentials import CredentialStore

def first_run_setup(store: CredentialStore):
    if store.load("LLM_API_KEY"):
        return
    print("LLM_API_KEY not found. Running first-time setup.")
    key = getpass.getpass("Enter LLM API Key: ")
    if key:
        store.store("LLM_API_KEY", key)
        print("Key stored securely.")
    else:
        print("No key provided. Agent will not be able to call LLM.")