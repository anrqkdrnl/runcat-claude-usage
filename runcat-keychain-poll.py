#!/usr/bin/env python3
"""RunCat Neo custom metric — Claude Code usage via direct Keychain + API polling.

Unlike runcat-usage.py (which only updates when Claude Code's statusLine hook
fires, i.e. while you're actively using that terminal session), this script
reads the profile's own OAuth session credential straight from the macOS
Keychain and calls Anthropic's usage endpoint directly. Meant to run on a
schedule (e.g. every 5 minutes) via a launchd LaunchAgent, independent of
whether Claude Code is running. See README.md for full setup steps.

Required environment variable:
  RUNCAT_KEYCHAIN_SERVICE  Keychain service name for this profile's
                            "Claude Code-credentials" item. For a second (or
                            later) profile this often has a random suffix,
                            e.g. "Claude Code-credentials-xxxxxxxx" — see
                            README.md for how to find it in Keychain Access.

Optional:
  CLAUDE_CONFIG_DIR   Config dir this credential belongs to, used only to
                      look up the account email/org for display
                      (default: ~/.claude)
  RUNCAT_OUT_FILE     Output JSON path (default: derived from the service
                      name under ~/RunCatMetrics/)
  RUNCAT_SYMBOL       Force a specific SF Symbol icon instead of the
                      auto-picked one (email domain's first letter)
"""
import json, os, re, subprocess, sys, tempfile, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

KEYCHAIN_SERVICE = os.environ.get("RUNCAT_KEYCHAIN_SERVICE")
if not KEYCHAIN_SERVICE:
    sys.exit("RUNCAT_KEYCHAIN_SERVICE is required — see README.md")

CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))


def default_out():
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", KEYCHAIN_SERVICE).strip("-").lower()
    return Path.home() / "RunCatMetrics" / f"{slug}.json"


OUT = Path(os.environ.get("RUNCAT_OUT_FILE") or default_out())


def account_info():
    for path in (CONFIG_DIR / ".claude.json", Path.home() / ".claude.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        acct = data.get("oauthAccount") or {}
        if acct.get("emailAddress") or acct.get("organizationName"):
            return acct.get("emailAddress"), acct.get("organizationName")
    return None, None


def symbol_for(email):
    override = os.environ.get("RUNCAT_SYMBOL")
    if override:
        return override
    dom = (email or "").split("@")[-1].lower()
    ch = dom[:1] if dom[:1].isalpha() else (email or "")[:1].lower()
    return f"{ch}.circle.fill" if ch.isalpha() else "bolt.horizontal.circle"


def load_token():
    raw = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    data = json.loads(raw)
    oauth = data.get("claudeAiOauth") or data
    token = oauth.get("accessToken") or oauth.get("access_token")
    if not token:
        raise ValueError("no accessToken found in keychain credential")
    return token


def fetch_usage(token):
    req = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
            "User-Agent": "claude-code",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


def used_row(title, used):
    if used is None:
        return None
    u = max(0.0, float(used))
    return {"title": title, "formattedValue": f"{u:.0f}% 사용",
            "normalizedValue": round(min(u, 100.0) / 100, 4)}


def write_snapshot(title, symbol, rows, bar_value):
    snap = {
        "title": title,
        "symbol": symbol,
        "metrics": rows,
        "lastUpdatedDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if bar_value is not None:
        snap["metricsBarValue"] = bar_value
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".runcat-", dir=str(OUT.parent))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)
    os.replace(tmp, OUT)


def main():
    email, org = account_info()
    symbol = symbol_for(email)
    title = f"Claude · {email}" if email else "Claude"

    try:
        token = load_token()
        payload = fetch_usage(token)
    except Exception as exc:
        write_snapshot(title, symbol, [{"title": "상태", "formattedValue": f"오류: {exc.__class__.__name__}"}], None)
        print(f"error: {exc}", file=sys.stderr)
        return 1

    five = (payload.get("five_hour") or {}).get("utilization")
    seven = (payload.get("seven_day") or {}).get("utilization")

    rows = []
    if email:
        rows.append({"title": "계정", "formattedValue": email})
    if org:
        rows.append({"title": "조직", "formattedValue": org})
    for t, v in (("5시간 한도", five), ("주간 한도", seven)):
        r = used_row(t, v)
        if r:
            rows.append(r)

    bar_value = f"{five:.0f}%" if five is not None else None
    write_snapshot(title, symbol, rows, bar_value)
    print(f"{email or 'claude'} · 5h {(five or 0):.0f}% used")
    return 0


if __name__ == "__main__":
    sys.exit(main())
