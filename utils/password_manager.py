# file: utils/password_manager.py
import os
import json
import hashlib
import secrets
from typing import Optional
from config import APP_DATA_DIR

PASSWORD_FILE = os.path.join(APP_DATA_DIR, "password.json")


def _load() -> dict:
    if not os.path.exists(PASSWORD_FILE):
        return {"enabled": False}
    try:
        with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"enabled": False}


def _save(data: dict):
    os.makedirs(os.path.dirname(PASSWORD_FILE), exist_ok=True)
    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def is_enabled() -> bool:
    cfg = _load()
    return bool(cfg.get("enabled", False))


def _hash_password(password: str, salt: str) -> str:
    h = hashlib.sha256()
    h.update((salt + password).encode("utf-8"))
    return h.hexdigest()


def verify_password(password: str) -> bool:
    cfg = _load()
    if not cfg.get("enabled"):
        return True
    salt = cfg.get("salt")
    stored = cfg.get("hash")
    if not salt or not stored:
        return False
    return _hash_password(password, salt) == stored


def set_password(new_password: str):
    salt = secrets.token_hex(16)
    h = _hash_password(new_password, salt)
    cfg = {"enabled": True, "salt": salt, "hash": h}
    _save(cfg)


def clear_password():
    cfg = {"enabled": False}
    _save(cfg)


def enable_password():
    cfg = _load()
    cfg["enabled"] = True
    _save(cfg)


def disable_password():
    cfg = _load()
    cfg["enabled"] = False
    _save(cfg)


def get_info() -> dict:
    """Return a non-sensitive summary of password state."""
    cfg = _load()
    return {"enabled": bool(cfg.get("enabled", False))}
