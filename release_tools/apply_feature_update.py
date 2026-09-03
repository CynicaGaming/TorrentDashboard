from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, value: str) -> None:
    (ROOT / path).write_text(value, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing transform anchor: {label}")
    return text.replace(old, new, 1)


app_js = read("static/app.js")
app_js = replace_once(
    app_js,
    "window.addEventListener('resize',()=>requestAnimationFrame(()=>{syncTorrentWorkspaceLayout();applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}));",
    "window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}));",
    "global resize synchronization",
)
app_js = replace_once(
    app_js,
    "  if(state.me?.can_manage)TDSettings.bind();\n  window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}));\n  window.addEventListener('keydown',e=>",
    "  if(state.me?.can_manage)TDSettings.bind();\n  window.addEventListener('keydown',e=>",
    "duplicate bindUI resize listener",
)
write("static/app.js", app_js)

validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    "    assert \"window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}))\" in app_js\n",
    "    assert app_js.count(\"window.addEventListener('resize',()=>requestAnimationFrame(()=>{applyFixedTorrentColumnLayout();syncDesktopDetailPaneHeight();syncMobileBulkbarOffset()}))\") == 1\n",
    "single resize listener audit",
)
write("release_tools/validate_ui_strings.py", validator)
print("Cleaned v0.5.112 viewport resize synchronization")
