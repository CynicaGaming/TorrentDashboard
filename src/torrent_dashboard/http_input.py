"""Bounded HTTP request parsing for JSON objects and multipart uploads."""

import json
import re
from email import policy
from email.parser import BytesParser
from email.message import Message


def read_body(handler, max_bytes):
    """Reject ambiguous framing and short bodies before passing bytes to parsers."""
    if handler.headers.get("Transfer-Encoding") is not None:
        raise RuntimeError("Transfer-Encoding is not supported")
    headers = handler.headers
    lengths = headers.get_all("Content-Length", []) if hasattr(headers, "get_all") else [headers.get("Content-Length", "0")]
    if len(lengths) > 1:
        raise RuntimeError("Multiple Content-Length headers are not supported")
    value = str(lengths[0] if lengths else "0").strip()
    if not re.fullmatch(r"[0-9]+", value):
        raise RuntimeError("Invalid Content-Length")
    length = int(value)
    if length > max_bytes:
        raise RuntimeError("Request too large")
    raw = handler.rfile.read(length) if length else b""
    if len(raw) != length:
        raise RuntimeError("Incomplete request body")
    return raw


def parse_json_body(handler, max_bytes=1_000_000):
    raw = read_body(handler, max_bytes)
    try:
        value = json.loads(raw.decode("utf-8") or "{}")
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Expected a valid JSON object") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Expected a JSON object")
    return value


def parse_multipart(handler, max_bytes=50_000_000):
    content_type = handler.headers.get("Content-Type", "")
    if "\r" in content_type or "\n" in content_type:
        raise RuntimeError("Invalid upload Content-Type")
    header = Message()
    header["Content-Type"] = content_type
    boundary = header.get_boundary()
    if header.get_content_type() != "multipart/form-data" or not boundary:
        raise RuntimeError("Expected multipart/form-data")
    if not re.fullmatch(r"[\x20-\x7e]{1,70}", boundary) or boundary.endswith(" "):
        raise RuntimeError("Invalid multipart boundary")
    body = read_body(handler, max_bytes)
    try:
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("ascii") + body
        )
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError("Invalid multipart upload") from exc
    if not message.is_multipart() or message.defects:
        raise RuntimeError("Incomplete or invalid multipart upload")
    fields, files = {}, []
    for index, part in enumerate(message.iter_parts()):
        if index >= 1000:
            raise RuntimeError("Upload contains too many parts")
        if part.is_multipart() or part.defects or part.get("Content-Transfer-Encoding"):
            raise RuntimeError("Unsupported multipart part")
        if part.get_content_disposition() != "form-data":
            raise RuntimeError("Expected form-data upload parts")
        name = part.get_param("name", header="content-disposition")
        if not isinstance(name, str) or not name:
            raise RuntimeError("Upload part is missing its field name")
        data = part.get_payload(decode=True)
        filename = part.get_filename()
        if filename is not None:
            files.append((name, filename, data))
        else:
            fields[name] = data.decode("utf-8", errors="replace")
    return fields, files


__all__ = ["parse_json_body", "parse_multipart"]
