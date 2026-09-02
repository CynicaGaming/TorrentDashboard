#!/usr/bin/env python3
from pathlib import Path

HERE = Path(__file__).resolve().parent
impl = HERE / "apply_feature_update_impl.py"
source = impl.read_text(encoding="utf-8")
old = "join('\\n')"
new = "join('\\\\n')"
if source.count(old) != 1:
    raise RuntimeError(f"expected one trusted-IP newline escape, found {source.count(old)}")
source = source.replace(old, new, 1)
namespace = {"__file__": str(impl), "__name__": "__main__"}
try:
    exec(compile(source, str(impl), "exec"), namespace)
finally:
    impl.unlink(missing_ok=True)
