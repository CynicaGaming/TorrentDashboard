"""Password-based authenticated encryption for portable Torrent Dashboard backups.

The format is intentionally independent of ZIP encryption so backup validation remains
under application control. It uses PBKDF2-HMAC-SHA256 to derive independent stream and
MAC keys, an HMAC-SHA256 PRF stream, and encrypt-then-MAC authentication.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import struct

MAGIC = b"TDBACKUP-ENC\x01"
SALT_BYTES = 16
NONCE_BYTES = 16
TAG_BYTES = 32
DEFAULT_ITERATIONS = 310_000
_HEADER_STRUCT = struct.Struct(">I16s16s")


def _password_bytes(password: str) -> bytes:
    value = str(password or "")
    if len(value) < 12:
        raise RuntimeError("Backup encryption password must contain at least 12 characters")
    encoded = value.encode("utf-8")
    if len(encoded) > 4096:
        raise RuntimeError("Backup encryption password is too long")
    return encoded


def _derive_keys(password: str, salt: bytes, iterations: int):
    if iterations < 100_000 or iterations > 2_000_000:
        raise RuntimeError("Backup encryption parameters are invalid")
    material = hashlib.pbkdf2_hmac("sha256", _password_bytes(password), salt, iterations, dklen=64)
    return material[:32], material[32:]


def _keystream_block(key: bytes, nonce: bytes, counter: int) -> bytes:
    return hmac.new(
        key,
        b"torrent-dashboard-backup-stream-v1\x00" + nonce + counter.to_bytes(8, "big"),
        hashlib.sha256,
    ).digest()


def _xor_stream(data: bytes, key: bytes, nonce: bytes, counter: int, offset: int):
    out = bytearray(len(data))
    pos = 0
    while pos < len(data):
        block = _keystream_block(key, nonce, counter)
        available = len(block) - offset
        take = min(available, len(data) - pos)
        for index in range(take):
            out[pos + index] = data[pos + index] ^ block[offset + index]
        pos += take
        offset += take
        if offset == len(block):
            counter += 1
            offset = 0
    return bytes(out), counter, offset


def is_encrypted_backup(path: Path | str) -> bool:
    try:
        with Path(path).open("rb") as handle:
            return handle.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def encrypt_file(source: Path | str, destination: Path | str, password: str, *, iterations: int = DEFAULT_ITERATIONS):
    """Encrypt one file to the versioned authenticated backup envelope."""
    source = Path(source)
    destination = Path(destination)
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    encryption_key, mac_key = _derive_keys(password, salt, int(iterations))
    params = _HEADER_STRUCT.pack(int(iterations), salt, nonce)
    header = MAGIC + params
    digest = hmac.new(mac_key, header, hashlib.sha256)
    counter = 0
    offset = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, destination.open("wb") as dst:
        dst.write(header)
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            encrypted, counter, offset = _xor_stream(chunk, encryption_key, nonce, counter, offset)
            dst.write(encrypted)
            digest.update(encrypted)
        dst.write(digest.digest())
    return destination


def decrypt_file(source: Path | str, destination: Path | str, password: str):
    """Authenticate and decrypt one backup envelope.

    Plaintext is written only to the caller-provided temporary destination. If
    authentication fails the temporary plaintext is removed before returning.
    """
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
        encryption_key, mac_key = _derive_keys(password, salt, int(iterations))
        header = MAGIC + raw_params
        ciphertext_size = total - len(header) - TAG_BYTES
        digest = hmac.new(mac_key, header, hashlib.sha256)
        counter = 0
        offset = 0
        remaining = ciphertext_size
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("wb") as dst:
                while remaining:
                    chunk = src.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError("Encrypted backup is truncated")
                    remaining -= len(chunk)
                    digest.update(chunk)
                    plain, counter, offset = _xor_stream(chunk, encryption_key, nonce, counter, offset)
                    dst.write(plain)
            tag = src.read(TAG_BYTES)
            if len(tag) != TAG_BYTES or not hmac.compare_digest(tag, digest.digest()):
                raise RuntimeError("Backup password is incorrect or the encrypted backup was modified")
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
