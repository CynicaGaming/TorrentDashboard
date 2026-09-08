from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "static" / "index.html"
APP_JS = ROOT / "static" / "app.js"

OLD_STYLE = '''<style>
.login-card{
  border-color:color-mix(in srgb,var(--accent) 34%,var(--border));
  animation:login-accent-glow 5.5s ease-in-out infinite;
}
@keyframes login-accent-glow{
  0%,100%{box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 14%,transparent),0 0 20px color-mix(in srgb,var(--accent) 12%,transparent)}
  50%{box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 34%,transparent),0 0 36px color-mix(in srgb,var(--accent) 24%,transparent)}
}
@media (prefers-reduced-motion:reduce){
  .login-card{animation:none;box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 20%,transparent),0 0 24px color-mix(in srgb,var(--accent) 16%,transparent)}
}
</style>'''

NEW_STYLE = '''<style>
.login-card{
  position:relative;
  isolation:isolate;
  border-color:color-mix(in srgb,var(--accent) 24%,var(--border));
  box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 8%,transparent);
}
.login-card::before{
  content:"";
  position:absolute;
  inset:-18px;
  z-index:-1;
  border-radius:30px;
  background:radial-gradient(ellipse at center,color-mix(in srgb,var(--accent) 28%,transparent) 0%,color-mix(in srgb,var(--accent) 13%,transparent) 44%,transparent 74%);
  filter:blur(17px);
  opacity:.46;
  transform:scale(.985);
  pointer-events:none;
  animation:login-radiant-glow 7s ease-in-out infinite;
}
@keyframes login-radiant-glow{
  0%,100%{opacity:.38;transform:scale(.985)}
  50%{opacity:.68;transform:scale(1.015)}
}
@media (prefers-reduced-motion:reduce){
  .login-card::before{animation:none;opacity:.52;transform:none}
}
</style>'''


def update_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    if NEW_STYLE not in text:
        if OLD_STYLE not in text:
            raise SystemExit("Expected existing login glow style was not found")
        text = text.replace(OLD_STYLE, NEW_STYLE, 1)

    # The Console remains available in the primary navigation, but should not be
    # duplicated in the profile-picture account menu.
    text = re.sub(
        r'<button\b[^>]*\bid="accountConsoleBtn"[^>]*>.*?</button>',
        '',
        text,
        count=1,
        flags=re.S,
    )
    INDEX.write_text(text, encoding="utf-8")


def update_app_js() -> None:
    text = APP_JS.read_text(encoding="utf-8")
    legacy = ";$('#accountConsoleBtn')?.addEventListener('click',()=>{hideAccountMenu();setView('console')})"
    text = text.replace(legacy, "")
    APP_JS.write_text(text, encoding="utf-8")


def validate_result() -> None:
    html = INDEX.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")
    required = (
        'animation:login-radiant-glow 7s ease-in-out infinite',
        '.login-card::before{',
        '@keyframes login-radiant-glow{',
    )
    missing = [marker for marker in required if marker not in html]
    if missing:
        raise SystemExit("Login radiant-glow contract is incomplete: " + ", ".join(missing))
    if 'accountConsoleBtn' in html or 'accountConsoleBtn' in app_js:
        raise SystemExit("Profile menu still contains the Console shortcut contract")


def main() -> None:
    update_index()
    update_app_js()
    validate_result()


if __name__ == "__main__":
    main()
