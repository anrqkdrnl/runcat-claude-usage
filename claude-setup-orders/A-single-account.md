# 작업 지시: RunCat Neo에 Claude Code 사용량 표시 — 방법 A / 계정 1개

Claude Code에게 이 파일을 주고 그대로 수행하게 하면 된다.
실행 환경: macOS, `python3` 설치됨, [RunCat Neo](https://github.com/runcat-dev/RunCatNeo) 설치됨.

## 목표

RunCat Neo 메뉴바에 이 컴퓨터의 Claude Code 계정 사용량(5시간/주간 한도, 계정, 모델)을
statusLine 훅으로 표시한다. **Claude Code가 실행 중일 때만 값이 갱신되는 가장 간단한 방식**이다
(상시 자동 갱신이 필요하면 이 폴더의 `B-single-account.md`를 대신 사용할 것).

## 절대 하지 말 것

- 스크립트에 실제 이메일 주소를 하드코딩하지 말 것 — 스크립트는 계정 정보를 자동으로 읽어온다.
- `~/.claude/settings.json`에 이미 있는 다른 설정(hooks 등)을 지우지 말고 `statusLine` 키만 병합할 것.

## 순서

1. `mkdir -p ~/.claude ~/RunCatMetrics`
2. 아래 "파일 내용"의 `runcat-usage.py`를 `~/.claude/runcat-usage.py`로 저장하고 `chmod +x`.
3. `~/.claude/settings.json`을 읽는다. 없으면 새로 만들고, 있으면 기존 키를 보존한 채
   `statusLine` 키만 아래 값으로 병합한다:
   ```json
   { "statusLine": { "type": "command", "command": "python3 $HOME/.claude/runcat-usage.py" } }
   ```
4. 검증 (반드시 임시 경로로 — `~/RunCatMetrics/`의 실제 값을 덮어쓰지 않도록):
   ```sh
   echo '{"model":{"display_name":"Opus 5"},"rate_limits":{"five_hour":{"used_percentage":18},"seven_day":{"used_percentage":64}}}' \
     | RUNCAT_OUT_FILE=/tmp/runcat-test.json python3 ~/.claude/runcat-usage.py
   cat /tmp/runcat-test.json
   ```
   `... · 5h 18% used`가 출력되고 JSON의 `symbol`이 `x.circle.fill` 형태(x는 이메일 도메인 첫 글자)면 정상.
5. 사용자에게 다음을 안내하고 마무리:
   - 아무 프롬프트로 `claude`를 한 번 실행해 응답을 받으면 `~/RunCatMetrics/claude-code.json`이 실제로 생성됨
   - RunCat Neo → 설정 → 메트릭 → Custom Metrics → `+ 사용자 설정 메트릭 소스 추가` → `Cmd+Shift+G` → 그 경로 입력
6. 완료 후 `cat ~/.claude/settings.json` 결과를 출력해서 최종 상태를 보고할 것.

## 예상되는 막힘과 대응

이 방법은 자격증명을 다루지 않으므로 자동 모드 보안 정책에 막힐 일이 거의 없다. 혹시 `settings.json` 수정이
차단되면, 현재 내용을 사용자에게 보여주고 `statusLine` 키를 직접 추가해달라고 요청할 것.

## 파일 내용

### `runcat-usage.py`

```python
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
    """메뉴바 아이콘(SF Symbol): 이메일 도메인 첫 글자."""
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
```
