# 작업 지시: RunCat Neo에 Claude Code 사용량 표시 — 방법 B / 계정 1개 (완전 자동)

Claude Code에게 이 파일을 주고 그대로 수행하게 하면 된다.
실행 환경: macOS, `python3` 설치됨, [RunCat Neo](https://github.com/runcat-dev/RunCatNeo) 설치됨.

## 목표

RunCat Neo 메뉴바에 Claude Code 계정 사용량(5시간/주간 한도, 계정, 조직)을 **Claude Code를 켜지 않아도
항상 최신 상태로** 표시한다. macOS 키체인에서 이 계정의 OAuth 세션 토큰을 읽어 사용량 API를 직접 호출하고,
그 결과를 launchd(LaunchAgent)가 5분마다 자동으로 갱신한다.

## 절대 하지 말 것

- 스크립트나 LaunchAgent plist에 실제 이메일 주소, 토큰, 키체인에서 읽은 값을 하드코딩하거나 출력하지 말 것.
- 폴링 주기를 1분보다 짧게 잡지 말 것 (레이트리밋 위험 — 아래 "문제 해결" 참고). 기본값 5분(300초)을 유지할 것.
- 같은 계정을 폴링하는 LaunchAgent나 다른 사용량 도구(예: `runcat-ai-usage` 데몬)가 이미 떠 있다면
  동시에 같은 계정을 중복 폴링하지 않도록 사용자에게 확인할 것 (레이트리밋 원인이 됨).

## 이 작업의 특성 — 반드시 먼저 읽을 것

이 작업은 macOS 키체인에서 OAuth 자격증명을 읽는 로직을 다룬다. Claude Code의 자동 모드 보안 정책은
이런 동작(키체인 조회 명령 실행, 그런 로직이 담긴 파일을 쓰거나 실행하는 것)을 **"자격증명 탐색"으로
분류해 자동으로 차단할 수 있다 — 이것은 의도된 정상 동작이다.** 차단되면:

- **재시도하거나 다른 명령으로 우회하려 하지 말 것.** (예: `cat` 대신 `head`로 시도, 파일 경로만 바꿔서 재시도 등)
- 즉시 멈추고, 아래 순서에서 표시한 대로 **그 단계만 사용자에게 직접 실행해달라고 요청**한 뒤, 결과(출력값,
  파일 생성 여부)만 전달받아 나머지 작업을 이어갈 것.
- 사용자가 실행할 명령은 토큰이나 비밀번호를 화면에 출력하지 않으므로, 결과를 그대로 붙여넣어 달라고 해도 안전하다.

## 순서

**1. 준비**

```sh
mkdir -p ~/.claude ~/RunCatMetrics
```

아래 "파일 내용"의 `runcat-keychain-poll.py`를 `~/.claude/runcat-keychain-poll.py`로 저장 시도.
**만약 이 파일 쓰기 자체가 차단되면**, 파일 내용을 사용자에게 그대로 보여주고 직접
`nano ~/.claude/runcat-keychain-poll.py` 등으로 붙여넣어 저장해달라고 요청할 것. 저장 후:
```sh
chmod +x ~/.claude/runcat-keychain-poll.py
```

**2. 이 계정의 키체인 서비스 이름 확인 (보통 여기서 자동화가 막힘)**

계정이 이 컴퓨터에서 처음 로그인한 유일한 Claude 계정이면 서비스 이름은 보통
`Claude Code-credentials` (접미사 없음) 그대로다. 확실히 하려면 사용자에게 다음을 요청:

1. Spotlight(`Cmd+Space`)에서 **키체인 접근(Keychain Access)** 앱 열기
2. 검색창에 `Claude Code-credentials` 입력
3. 나오는 항목 이름을 그대로 알려달라고 요청 (암호를 보여달라고 하지 말 것 — 이름만 필요함)

**3. 스크립트 테스트 (여기서도 막힐 수 있음)**

2에서 확인한 이름으로 실행 시도:
```sh
RUNCAT_KEYCHAIN_SERVICE="<확인한 이름>" \
RUNCAT_OUT_FILE=/tmp/runcat-test.json \
python3 ~/.claude/runcat-keychain-poll.py
cat /tmp/runcat-test.json
```
**차단되면** 위 명령 그대로를 사용자에게 실행해달라고 요청하고, 출력된 `cat` 결과만 전달받을 것
(토큰은 출력되지 않으므로 안전). `계정`과 `5시간 한도`가 숫자로 나오면 성공. `HTTPError: 401/403`이면
서비스 이름이 틀린 것이니 2번부터 다시.

만약 `SSL: CERTIFICATE_VERIFY_FAILED` 오류가 나면 python.org 배포판의 인증서 미설치 문제이므로:
```sh
"/Applications/Python 3.x/Install Certificates.command"
```
(정확한 버전 폴더명은 `ls /Applications | grep Python`으로 확인) 실행 후 재시도.

**4. LaunchAgent 등록 (자격증명을 직접 다루지 않으므로 보통 자동으로 진행 가능)**

`which python3`로 경로 확인 후, 아래 "파일 내용"의 plist 템플릿을 사용해
`~/Library/LaunchAgents/local.runcat.claude-poll.plist` 를 만든다. 플레이스홀더를 다음처럼 채운다:

| 플레이스홀더 | 값 |
|---|---|
| `LABEL` | `local.runcat.claude-poll` |
| `PYTHON3_PATH` | `which python3` 결과 |
| `SCRIPT_PATH` | `/Users/<user>/.claude/runcat-keychain-poll.py` |
| `KEYCHAIN_SERVICE` | 2번에서 확인한 이름 |
| `CONFIG_DIR` | `/Users/<user>/.claude` |
| `LOG_OUT_PATH` | `/Users/<user>/Library/Logs/runcat-claude-poll.log` |
| `LOG_ERR_PATH` | `/Users/<user>/Library/Logs/runcat-claude-poll.error.log` |

**5. LaunchAgent 실행**

```sh
launchctl unload ~/Library/LaunchAgents/local.runcat.claude-poll.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/local.runcat.claude-poll.plist
launchctl list | grep runcat
```

**6. 동작 확인** (이 단계도 막히면 사용자에게 위임)

```sh
cat ~/Library/Logs/runcat-claude-poll.error.log   # 비어 있어야 정상
cat ~/RunCatMetrics/*.json                        # 값이 채워져 있어야 정상
```

**7. 사용자에게 안내하고 마무리**

- RunCat Neo → 설정 → 메트릭 → Custom Metrics → `+` → `Cmd+Shift+G` → 6번에서 확인한 JSON 경로 입력
- 이 LaunchAgent는 로그인 시 자동 시작되며, 5분마다 자동 갱신된다.

## 문제 해결

- **`HTTP 429 Too Many Requests`**: 같은 계정을 두 프로세스 이상이 동시에 폴링하고 있을 가능성이 높다.
  `launchctl list | grep runcat`으로 중복된 LaunchAgent가 없는지 확인하고, 있다면 하나만 남기고
  `launchctl unload`. 재시도를 반복하지 말고 몇 분 기다렸다가 다음 정기 실행을 기다릴 것.
- **리소스 사용량 우려**: 이 스크립트는 상주 프로세스가 아니라 launchd가 5분마다 잠깐 띄웠다 바로
  끝내는 방식이라 CPU/배터리 영향은 무시할 수 있는 수준이다.

## 파일 내용

### `runcat-keychain-poll.py`

```python
#!/usr/bin/env python3
"""RunCat Neo custom metric — Claude Code usage via direct Keychain + API polling.

Unlike a statusLine-hook script (which only updates when Claude Code's hook
fires, i.e. while you're actively using that terminal session), this script
reads the profile's own OAuth session credential straight from the macOS
Keychain and calls Anthropic's usage endpoint directly. Meant to run on a
schedule (e.g. every 5 minutes) via a launchd LaunchAgent, independent of
whether Claude Code is running.

Required environment variable:
  RUNCAT_KEYCHAIN_SERVICE  Keychain service name for this profile's
                            "Claude Code-credentials" item. For a second (or
                            later) profile this often has a random suffix,
                            e.g. "Claude Code-credentials-xxxxxxxx" — find it
                            in Keychain Access.

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
    sys.exit("RUNCAT_KEYCHAIN_SERVICE is required")

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
```

### `runcat-keychain-poll.plist.template`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>PYTHON3_PATH</string>
        <string>SCRIPT_PATH</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>RUNCAT_KEYCHAIN_SERVICE</key>
        <string>KEYCHAIN_SERVICE</string>
        <key>CLAUDE_CONFIG_DIR</key>
        <string>CONFIG_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>300</integer>
    <key>ProcessType</key>
    <string>Background</string>
    <key>StandardOutPath</key>
    <string>LOG_OUT_PATH</string>
    <key>StandardErrorPath</key>
    <string>LOG_ERR_PATH</string>
</dict>
</plist>
```
