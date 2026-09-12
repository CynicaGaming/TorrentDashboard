"""AES-256-GCM protection for portable Torrent Dashboard backups."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import struct

MAGIC = b"TDBACKUP-AESGCM\x01"
SALT_BYTES = 16
NONCE_BYTES = 12
TAG_BYTES = 16
DEFAULT_ITERATIONS = 600_000
_HEADER_STRUCT = struct.Struct(">I16s12s")


def _crypto_primitives():
    """Import cryptography lazily so source installs still boot before dependencies are refreshed."""
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except Exception as exc:
        raise RuntimeError(
            "Encrypted backups require cryptography 50.0.1. Install project dependencies and try again"
        ) from exc
    return InvalidTag, Cipher, algorithms, modes


def _password_bytes(password: str) -> bytes:
    value = str(password or "")
    if len(value) < 12:
        raise RuntimeError("Backup encryption password must contain at least 12 characters")
    encoded = value.encode("utf-8")
    if len(encoded) > 4096:
        raise RuntimeError("Backup encryption password is too long")
    return encoded


def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    if iterations < 100_000 or iterations > 2_000_000:
        raise RuntimeError("Backup encryption parameters are invalid")
    return hashlib.pbkdf2_hmac("sha256", _password_bytes(password), salt, iterations, dklen=32)


def is_encrypted_backup(path: Path | str) -> bool:
    try:
        with Path(path).open("rb") as handle:
            return handle.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def encrypt_file(source: Path | str, destination: Path | str, password: str, *, iterations: int = DEFAULT_ITERATIONS):
    """Encrypt one file with streaming AES-256-GCM and authenticated metadata."""
    _, Cipher, algorithms, modes = _crypto_primitives()
    source = Path(source)
    destination = Path(destination)
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    key = _derive_key(password, salt, int(iterations))
    header = MAGIC + _HEADER_STRUCT.pack(int(iterations), salt, nonce)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(header)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with source.open("rb") as src, destination.open("wb") as dst:
            dst.write(header)
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(encryptor.update(chunk))
            dst.write(encryptor.finalize())
            dst.write(encryptor.tag)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def decrypt_file(source: Path | str, destination: Path | str, password: str):
    """Authenticate and decrypt one backup envelope without exposing unauthenticated plaintext."""
    InvalidTag, Cipher, algorithms, modes = _crypto_primitives()
    source = Path(source)
    destination = Path(destination)
    total = source.stat().st_size
    minimum = len(MAGIC) + _HEADER_STRUCT.size + TAG_BYTES
    if total < minimum:
        raise RuntimeError("Encrypted backup is truncated")

    with source.open("rb") as src:
        if src.read(len(MAGIC)) != MAGIC:
            raise RuntimeError("Backup is not an encrypted Torrent Dashboard archive")
        raw_params = src.read(_HEADER_STRUCT.size)
        if len(raw_params) != _HEADER_STRUCT.size:
            raise RuntimeError("Encrypted backup header is truncated")
        iterations, salt, nonce = _HEADER_STRUCT.unpack(raw_params)
        key = _derive_key(password, salt, int(iterations))
        header = MAGIC + raw_params
        ciphertext_offset = len(header)
        ciphertext_size = total - ciphertext_offset - TAG_BYTES
        src.seek(ciphertext_offset + ciphertext_size)
        tag = src.read(TAG_BYTES)
        if len(tag) != TAG_BYTES:
            raise RuntimeError("Encrypted backup authentication tag is truncated")
        src.seek(ciphertext_offset)

        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag, min_tag_length=TAG_BYTES)).decryptor()
        decryptor.authenticate_additional_data(header)
        destination.parent.mkdir(parents=True, exist_ok=True)
        remaining = ciphertext_size
        try:
            with destination.open("wb") as dst:
                while remaining:
                    chunk = src.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError("Encrypted backup is truncated")
                    remaining -= len(chunk)
                    dst.write(decryptor.update(chunk))
                dst.write(decryptor.finalize())
        except InvalidTag as exc:
            destination.unlink(missing_ok=True)
            raise RuntimeError("Backup password is incorrect or the encrypted backup was modified") from exc
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return destination


__all__ = [
    "DEFAULT_ITERATIONS",
    "MAGIC",
    "decrypt_file",
    "encrypt_file",
    "is_encrypted_backup",
]
