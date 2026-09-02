from __future__ import annotations

import ast
import base64
import re
import zlib
from pathlib import Path

impl = Path(__file__).with_name("apply_feature_update_impl.py")
text = impl.read_text(encoding="utf-8")
match = re.search(r"^_PAYLOAD\s*=\s*(.+)$", text, re.MULTILINE)
if not match:
    raise SystemExit("Could not locate staged feature payload")
payload = ast.literal_eval(match.group(1))
source = zlib.decompress(base64.b64decode(payload)).decode("utf-8")
lines = []
for line in source.splitlines():
    if "Content-Disposition: form-data; name=" in line and "safe_name" in line:
        line = "            f'--{boundary}\\r\\nContent-Disposition: form-data; name=\"file\"; filename=\"{safe_name}\"\\r\\nContent-Type: application/x-bittorrent\\r\\n\\r\\n'.encode(),"
    elif "--{boundary}--" in line and ".encode()," in line:
        line = "            f'\\r\\n--{boundary}--\\r\\n'.encode(),"
    lines.append(line)
source = "\n".join(lines) + "\n"
exec(compile(source, str(impl), "exec"), globals(), globals())
impl.unlink(missing_ok=True)
