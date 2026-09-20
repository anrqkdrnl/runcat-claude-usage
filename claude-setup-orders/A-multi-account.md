# 작업 지시: RunCat Neo에 Claude Code 사용량 표시 — 방법 A / 계정 2개 이상

Claude Code에게 이 파일을 주고 그대로 수행하게 하면 된다.
실행 환경: macOS, `python3` 설치됨, [RunCat Neo](https://github.com/runcat-dev/RunCatNeo) 설치됨.

## 목표

RunCat Neo 메뉴바에 **여러 개의 Claude Code 계정** 사용량을 계정별로 따로 카드에 표시한다.
각 계정은 `CLAUDE_CONFIG_DIR` 프로파일로 분리하고, statusLine 훅으로 갱신한다
(**해당 프로파일로 `claude`를 실행 중일 때만** 그 계정 카드가 갱신됨). 상시 자동 갱신이 필요하면
이 폴더의 `B-multi-account.md`를 대신 사용할 것.

## 절대 하지 말 것

- 스크립트에 실제 이메일 주소를 하드코딩하지 말 것.
- 기본 프로파일(`~/.claude/settings.json`)이나 다른 계정 프로파일의 설정을 지우지 말고 병합만 할 것.
- 서로 다른 계정의 자격증명 파일을 뒤섞거나 다른 프로파일 디렉터리로 복사하지 말 것.

## 순서

1. **몇 개의 계정을 등록할지, 각 프로파일 이름을 무엇으로 할지 사용자에게 먼저 확인한다**
   (예: 기본 계정 + `~/.claude-personal` + `~/.claude-work` 처럼). 계정 이름/용도로 유추 가능한
   디렉터리명을 제안하되, 최종 이름은 사용자 확인을 받을 것.
2. `mkdir -p ~/.claude ~/RunCatMetrics` (기본 프로파일용, 이미 있으면 생략)
3. 아래 "파일 내용"의 `runcat-usage.py`를 `~/.claude/runcat-usage.py`로 저장하고 `chmod +x`.
4. 기본 프로파일의 `~/.claude/settings.json`에 다음을 병합(기존 키 보존):
   ```json
   { "statusLine": { "type": "command", "command": "python3 $HOME/.claude/runcat-usage.py" } }
   ```
5. **추가 계정마다** 다음을 반복 (예: 두 번째 계정 디렉터리명이 `.claude-personal`이라면):
   ```sh
   mkdir -p ~/.claude-personal
   cp ~/.claude/settings.json ~/.claude-personal/settings.json   # statusLine 키가 포함돼 있어야 함
   ```
   그리고 사용자의 쉘 설정 파일(`~/.zshrc` 등)에 편의 alias를 추가할지 물어볼 것:
   ```sh
   alias claude2='CLAUDE_CONFIG_DIR=$HOME/.claude-personal claude'
   ```
   (세 번째 계정부터는 `claude3`, `.claude-work` 등으로 이름만 바꿔 반복)
6. 검증 (임시 경로 사용, 실제 값 덮어쓰지 않도록):
   ```sh
   echo '{"model":{"display_name":"Opus 5"},"rate_limits":{"five_hour":{"used_percentage":18},"seven_day":{"used_percentage":64}}}' \
     | CLAUDE_CONFIG_DIR="$HOME/.claude-personal" RUNCAT_OUT_FILE=/tmp/runcat-test.json python3 ~/.claude/runcat-usage.py
   cat /tmp/runcat-test.json
   ```
7. 사용자에게 안내:
   - 각 프로파일로 (`claude`, `claude2`, ...) 한 번씩 실행해 로그인/응답을 받으면 계정별로
     `~/RunCatMetrics/claude-code.json`, `~/RunCatMetrics/claude-personal.json` 등이 생성됨
   - RunCat Neo → 설정 → 메트릭 → Custom Metrics 에서 계정 수만큼 소스를 각각 추가
   - 아이콘은 이메일 도메인 첫 글자로 자동 구분됨 (`hanyang.ac.kr` → H, `gmail.com` → G 등)
8. 완료 후 등록된 프로파일 목록, 각 `settings.json` 내용, 생성된 alias를 정리해서 보고할 것.

## 예상되는 막힘과 대응

이 방법은 자격증명을 직접 다루지 않으므로 자동 모드 보안 정책에 막힐 일이 거의 없다. 각 프로파일에
`/login`으로 실제 로그인하는 것은 사용자가 직접 해야 하는 일이므로, 그 부분은 사용자에게 안내만 하고
자동으로 시도하지 말 것 (인터랙티브 브라우저 인증이 필요함).

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
