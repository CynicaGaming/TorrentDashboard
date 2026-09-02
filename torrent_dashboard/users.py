"""User, account, password, and profile domain operations."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
AVATAR_DIR = APP_DIR / "data" / "avatars"
MAX_AVATAR_BYTES = 4 * 1024 * 1024
PROFILE_AVATAR_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

USER_GROUPS = {
    "administrator": "Administrator",
    "standard": "Standard User",
}


def hash_password(password: str, iterations: int = 260_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        pad = lambda s: s + "=" * (-len(s) % 4)
        salt = base64.urlsafe_b64decode(pad(salt_b64))
        expected = base64.urlsafe_b64decode(pad(digest_b64))
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(expected, got)
    except Exception:
        return False


def user_display_name(user):
    full = " ".join(
        x
        for x in (
            str(user.get("first_name") or "").strip(),
            str(user.get("last_name") or "").strip(),
        )
        if x
    ).strip()
    return full or str(user.get("username") or "User")


def normalize_user(data, existing=None, require_password=False):
    existing = existing or {}
    uid = str(data.get("id") or existing.get("id") or uuid.uuid4().hex[:12])[:64]
    username = str(
        data.get("username")
        if data.get("username") is not None
        else existing.get("username") or ""
    ).strip()[:128]
    if not username:
        raise RuntimeError("Username is required")
    if not re.fullmatch(r"[A-Za-z0-9_.@-]+", username):
        raise RuntimeError(
            "Username may contain letters, numbers, dots, underscores, hyphens, and @"
        )
    group_raw = (
        str(data.get("group") or existing.get("group") or "standard")
        .strip()
        .lower()
        .replace(" ", "_")
    )
    if group_raw in ("admin", "administrator"):
        group = "administrator"
    elif group_raw in ("standard", "standard_user", "user"):
        group = "standard"
    else:
        raise RuntimeError("User group must be Administrator or Standard User")
    email = str(
        data.get("email")
        if data.get("email") is not None
        else existing.get("email") or ""
    ).strip()[:254]
    if email and ("@" not in email or email.startswith("@") or email.endswith("@")):
        raise RuntimeError("Enter a valid email address or leave it blank")
    password_hash = str(data.get("password_hash") or existing.get("password_hash") or "")
    password = str(data.get("password") or "")
    if password:
        password_hash = hash_password(password)
    if require_password and not password_hash:
        raise RuntimeError("Password is required for a new user")
    return {
        "id": uid,
        "username": username,
        "password_hash": password_hash,
        "first_name": str(
            data.get("first_name")
            if data.get("first_name") is not None
            else existing.get("first_name") or ""
        ).strip()[:128],
        "last_name": str(
            data.get("last_name")
            if data.get("last_name") is not None
            else existing.get("last_name") or ""
        ).strip()[:128],
        "email": email,
        "avatar_file": Path(
            str(
                data.get("avatar_file")
                if data.get("avatar_file") is not None
                else existing.get("avatar_file") or ""
            )
        ).name[:255],
        "avatar_version": str(
            data.get("avatar_version")
            if data.get("avatar_version") is not None
            else existing.get("avatar_version") or ""
        )[:64],
        "group": group,
    }


def public_user(user):
    avatar_path, _ = configured_user_avatar(user)
    return {
        "id": str(user.get("id") or ""),
        "username": str(user.get("username") or ""),
        "first_name": str(user.get("first_name") or ""),
        "last_name": str(user.get("last_name") or ""),
        "email": str(user.get("email") or ""),
        "group": "administrator" if user.get("group") == "administrator" else "standard",
        "group_label": USER_GROUPS.get(user.get("group"), "Standard User"),
        "display_name": user_display_name(user),
        "avatar_configured": bool(avatar_path),
        "avatar_version": str(user.get("avatar_version") or ""),
        "password_configured": bool(user.get("password_hash")),
    }


def _profile_avatar_stem(user_id):
    return "profile-" + hashlib.sha256(str(user_id or "").encode("utf-8")).hexdigest()[:24]


def configured_user_avatar(user):
    user_id = str((user or {}).get("id") or "")
    filename = Path(str((user or {}).get("avatar_file") or "")).name
    if not user_id or not filename:
        return None, None
    ext = Path(filename).suffix.lower()
    mime = PROFILE_AVATAR_TYPES.get(ext)
    if not mime or filename != _profile_avatar_stem(user_id) + ext:
        return None, None
    path = AVATAR_DIR / filename
    if not path.exists() or not path.is_file():
        return None, None
    return path, mime


def _validate_profile_avatar(filename, content):
    filename = Path(str(filename or "profile")).name
    ext = Path(filename).suffix.lower()
    mime = PROFILE_AVATAR_TYPES.get(ext)
    if not mime:
        raise RuntimeError("Profile picture must be a PNG, JPG, or WebP image")
    if not content or len(content) > MAX_AVATAR_BYTES:
        raise RuntimeError("Profile picture must be between 1 byte and 4 MB")
    if ext == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("The selected PNG file is not valid")
    if ext in (".jpg", ".jpeg") and not content.startswith(b"\xff\xd8\xff"):
        raise RuntimeError("The selected JPG file is not valid")
    if ext == ".webp" and not (
        len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    ):
        raise RuntimeError("The selected WebP file is not valid")
    return ext, mime


def delete_user_avatar_files(user_id):
    if not user_id:
        return
    stem = _profile_avatar_stem(user_id)
    for ext in PROFILE_AVATAR_TYPES:
        try:
            (AVATAR_DIR / f"{stem}{ext}").unlink(missing_ok=True)
        except Exception:
            pass


def store_user_avatar(cfg, user_id, filename, content):
    out = json.loads(json.dumps(cfg))
    user = user_by_id(out, user_id)
    if not user:
        raise RuntimeError("This session is not linked to a user account")
    ext, _ = _validate_profile_avatar(filename, content)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    delete_user_avatar_files(user_id)
    dest = AVATAR_DIR / f"{_profile_avatar_stem(user_id)}{ext}"
    dest.write_bytes(content)
    user["avatar_file"] = dest.name
    user["avatar_version"] = secrets.token_hex(8)
    sync_legacy_auth(out)
    return out, user


def remove_user_avatar(cfg, user_id):
    out = json.loads(json.dumps(cfg))
    user = user_by_id(out, user_id)
    if not user:
        raise RuntimeError("This session is not linked to a user account")
    delete_user_avatar_files(user_id)
    user["avatar_file"] = ""
    user["avatar_version"] = secrets.token_hex(8)
    sync_legacy_auth(out)
    return out, user


def save_current_user_profile(cfg, user_id, data):
    out = json.loads(json.dumps(cfg))
    users = out.setdefault("users", [])
    existing = user_by_id(out, user_id)
    if not existing:
        raise RuntimeError("This session is not linked to a user account")
    requested_username = str(
        data.get("username")
        if data.get("username") is not None
        else existing.get("username") or ""
    ).strip()
    requested_email = str(
        data.get("email")
        if data.get("email") is not None
        else existing.get("email") or ""
    ).strip()
    secure_change = (
        requested_username != str(existing.get("username") or "")
        or requested_email != str(existing.get("email") or "")
    )
    encoded = str(existing.get("password_hash") or "")
    if secure_change and encoded and not verify_password(
        str(data.get("current_password") or ""), encoded
    ):
        raise RuntimeError("Current password is required to change your username or email")
    item = normalize_user(
        {
            "id": existing.get("id"),
            "username": requested_username,
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": requested_email,
            "group": existing.get("group"),
        },
        existing,
    )
    duplicate = next(
        (
            u
            for u in users
            if str(u.get("id") or "") != item["id"]
            and str(u.get("username") or "").casefold() == item["username"].casefold()
        ),
        None,
    )
    if duplicate:
        raise RuntimeError("That username is already in use")
    users[users.index(existing)] = item
    sync_legacy_auth(out)
    return out, item


def change_current_user_password(cfg, user_id, current_password, new_password):
    out = json.loads(json.dumps(cfg))
    user = user_by_id(out, user_id)
    if not user:
        raise RuntimeError("This session is not linked to a user account")
    encoded = str(user.get("password_hash") or "")
    if encoded and not verify_password(str(current_password or ""), encoded):
        raise RuntimeError("Current password is incorrect")
    new_password = str(new_password or "")
    if len(new_password) < 8:
        raise RuntimeError("New password must be at least 8 characters")
    user["password_hash"] = hash_password(new_password)
    sync_legacy_auth(out)
    return out, user


def user_by_username(cfg, username):
    wanted = str(username or "").casefold()
    return next(
        (
            u
            for u in cfg.get("users", [])
            if str(u.get("username") or "").casefold() == wanted
        ),
        None,
    )


def user_by_id(cfg, user_id):
    wanted = str(user_id or "")
    return next(
        (u for u in cfg.get("users", []) if str(u.get("id") or "") == wanted),
        None,
    )


def session_is_admin(sess):
    return bool(sess and sess.get("group") == "administrator")


def sync_legacy_auth(cfg):
    auth = cfg.setdefault("auth", {})
    admins = [u for u in cfg.get("users", []) if u.get("group") == "administrator"]
    chosen = admins[0] if admins else (cfg.get("users") or [None])[0]
    if chosen:
        auth["username"] = chosen.get("username", "admin")
        auth["password_hash"] = chosen.get("password_hash", "")
    else:
        auth["username"] = "admin"
        auth["password_hash"] = ""
    return cfg


def save_user(cfg, data):
    out = json.loads(json.dumps(cfg))
    users = out.setdefault("users", [])
    user_id = str(data.get("id") or "")
    existing = (
        next((u for u in users if str(u.get("id") or "") == user_id), None)
        if user_id
        else None
    )
    item = normalize_user(data, existing, require_password=existing is None)
    duplicate = next(
        (
            u
            for u in users
            if str(u.get("id") or "") != item["id"]
            and str(u.get("username") or "").casefold() == item["username"].casefold()
        ),
        None,
    )
    if duplicate:
        raise RuntimeError("That username is already in use")
    if existing:
        users[users.index(existing)] = item
    else:
        users.append(item)
    if not any(u.get("group") == "administrator" for u in users):
        raise RuntimeError("At least one Administrator account is required")
    sync_legacy_auth(out)
    return out, item


def delete_user(cfg, user_id, current_user_id=""):
    user_id = str(user_id or "")
    if not user_id:
        raise RuntimeError("User ID is required")
    if current_user_id and user_id == str(current_user_id):
        raise RuntimeError("You cannot delete the account you are currently using")
    out = json.loads(json.dumps(cfg))
    before = len(out.get("users", []))
    out["users"] = [
        u for u in out.get("users", []) if str(u.get("id") or "") != user_id
    ]
    if len(out["users"]) == before:
        raise RuntimeError("User was not found")
    if not any(u.get("group") == "administrator" for u in out["users"]):
        raise RuntimeError("At least one Administrator account is required")
    sync_legacy_auth(out)
    return out


__all__ = [
    "AVATAR_DIR",
    "MAX_AVATAR_BYTES",
    "PROFILE_AVATAR_TYPES",
    "USER_GROUPS",
    "change_current_user_password",
    "configured_user_avatar",
    "delete_user",
    "delete_user_avatar_files",
    "hash_password",
    "normalize_user",
    "public_user",
    "remove_user_avatar",
    "save_current_user_profile",
    "save_user",
    "session_is_admin",
    "store_user_avatar",
    "sync_legacy_auth",
    "user_by_id",
    "user_by_username",
    "user_display_name",
    "verify_password",
]
