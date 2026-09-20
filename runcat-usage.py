#!/usr/bin/env python3
"""RunCat Neo custom metric — Claude Code usage per account."""
import json, os, re, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))

def default_out():
    name = CONFIG_DIR.name.lstrip(".")           # .claude -> claude, .claude-personal -> claude-personal
    slug = "code" if name == "claude" else re.sub(r"^claude-?", "", name) or "alt"
    return Path.home() / "RunCatMetrics" / f"claude-{slug}.json"

OUT = Path(os.environ["RUNCAT_OUT_FILE"]) if os.environ.get("RUNCAT_OUT_FILE") else default_out()

def account_info():
    for path in (CONFIG_DIR / ".claude.json", Path(str(CONFIG_DIR) + ".json"),
                 Path.home() / ".claude.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        acct = data.get("oauthAccount") or {}
        if acct.get("emailAddress") or acct.get("organizationName"):
            return acct.get("emailAddress"), acct.get("organizationName")
    return os.environ.get("CLAUDE_ACCOUNT_EMAIL"), None

def used_row(title, used):
    if used is None:
        return None
    u = max(0.0, float(used))
    return {"title": title, "formattedValue": f"{u:.0f}% 사용",
            "normalizedValue": round(min(u, 100.0) / 100, 4)}

def symbol_for(email):
    """메뉴바 아이콘(SF Symbol): 이메일 도메인 첫 글자. hanyang.ac.kr -> H, gmail.com -> G"""
    override = os.environ.get("RUNCAT_SYMBOL")
    if override:
        return override
    dom = (email or "").split("@")[-1].lower()
    ch = dom[:1] if dom[:1].isalpha() else (email or "")[:1].lower()
    return f"{ch}.circle.fill" if ch.isalpha() else "bolt.horizontal.circle"

try:
    p = json.load(sys.stdin)
    if not isinstance(p, dict):
        p = {}
except Exception:
    p = {}

model      = (p.get("model") or {}).get("display_name") or "Claude"
ctx        = (p.get("context_window") or {}).get("used_percentage")
rl         = p.get("rate_limits") or {}
five       = (rl.get("five_hour") or {}).get("used_percentage")
five_reset = (rl.get("five_hour") or {}).get("resets_at")
seven      = (rl.get("seven_day") or {}).get("used_percentage")
email, org = account_info()

rows = []
if email:
    rows.append({"title": "계정", "formattedValue": email})
if org:
    rows.append({"title": "조직", "formattedValue": org})
rows.append({"title": "모델", "formattedValue": model})
for t, v in (("5시간 한도", five), ("주간 한도", seven)):
    r = used_row(t, v)
    if r:
        rows.append(r)
if five_reset:
    try:
        rows.append({"title": "5시간 리셋",
                     "formattedValue": datetime.fromtimestamp(int(five_reset)).strftime("%H:%M")})
    except Exception:
        pass
if ctx is not None:
    rows.append({"title": "컨텍스트 사용", "formattedValue": f"{ctx:g}%",
                 "normalizedValue": round(ctx / 100, 4)})

snap = {
    "title": f"Claude · {email}" if email else "Claude 사용량",
    "symbol": symbol_for(email),
    "metrics": rows,
    "lastUpdatedDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
if five is not None:
    snap["metricsBarValue"] = f"{five:.0f}%"
elif ctx is not None:
    snap["metricsBarValue"] = f"ctx {ctx:g}%"

OUT.parent.mkdir(parents=True, exist_ok=True)
fd, tmp = tempfile.mkstemp(prefix=".runcat-", dir=str(OUT.parent))
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False)
os.replace(tmp, OUT)

print(f"{(email or model)} · 5h {(five or 0):.0f}% used")
