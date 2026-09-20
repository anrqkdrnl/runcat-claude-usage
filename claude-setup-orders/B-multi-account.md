# 작업 지시: RunCat Neo에 Claude Code 사용량 표시 — 방법 B / 계정 2개 이상 (완전 자동)

Claude Code에게 이 파일을 주고 그대로 수행하게 하면 된다.
실행 환경: macOS, `python3` 설치됨, [RunCat Neo](https://github.com/runcat-dev/RunCatNeo) 설치됨.

## 목표

RunCat Neo 메뉴바에 **여러 개의 Claude Code 계정** 사용량을 각각 **Claude Code를 켜지 않아도 항상 최신
상태**로 표시한다. 계정마다 macOS 키체인에서 그 계정의 OAuth 세션 토큰을 읽어 사용량 API를 직접
호출하고, launchd(LaunchAgent)가 계정마다 하나씩 독립적으로 5분마다 갱신한다.

## 절대 하지 말 것

- 스크립트나 LaunchAgent plist에 실제 이메일 주소, 토큰, 키체인에서 읽은 값을 하드코딩하거나 출력하지 말 것.
- 폴링 주기를 1분보다 짧게 잡지 말 것 (기본값 5분/300초 유지).
- **같은 계정**을 두 개 이상의 LaunchAgent가 동시에 폴링하게 만들지 말 것 (레이트리밋 원인). 계정이
  다르면 각자 독립적인 API 요청 한도를 가지므로 동시에 폴링해도 문제없다.
- 서로 다른 계정의 키체인 서비스 이름이나 설정 디렉터리를 혼동하지 말 것 — 계정마다 반드시 구분되는
  `Label`, `RUNCAT_KEYCHAIN_SERVICE`, `CLAUDE_CONFIG_DIR`, 출력 파일 경로, 로그 경로를 쓸 것.

## 이 작업의 특성 — 반드시 먼저 읽을 것

이 작업은 macOS 키체인에서 OAuth 자격증명을 읽는 로직을 계정 수만큼 반복해서 다룬다. Claude Code의
자동 모드 보안 정책은 이런 동작을 **"자격증명 탐색"으로 분류해 자동으로 차단할 수 있다 — 의도된 정상
동작이다.** 차단되면:

- **재시도하거나 다른 명령으로 우회하려 하지 말 것.**
- 즉시 멈추고, 그 단계만 사용자에게 직접 실행해달라고 요청한 뒤 결과만 전달받아 이어갈 것.
- 이 과정은 **계정마다 반복**되므로, 몇 번이고 다시 막힐 수 있다는 것을 미리 사용자에게 알려줄 것.

## 순서

**0. 먼저 사용자에게 확인**

몇 개의 계정을 등록할지, 각 계정을 어떤 이름/용도로 구분할지(예: "회사 계정", "개인 계정") 확인한다.
아래 1~7번을 **계정 수만큼 반복**하되, 계정마다 아래 표의 값들을 서로 겹치지 않게 정한다.

| 항목 | 계정 A 예시 | 계정 B 예시 |
|---|---|---|
| Claude 설정 디렉터리 (`CLAUDE_CONFIG_DIR`) | `~/.claude` (기본) | `~/.claude-work` |
| 스크립트 저장 경로 | `~/.claude/runcat-keychain-poll.py` | `~/.claude-work/runcat-keychain-poll.py` |
| LaunchAgent `Label` | `local.runcat.claude-a-poll` | `local.runcat.claude-b-poll` |
| 출력 JSON 경로 | `~/RunCatMetrics/claude-a.json` | `~/RunCatMetrics/claude-b.json` |
| 로그 경로 | `~/Library/Logs/runcat-claude-a-poll.*.log` | `~/Library/Logs/runcat-claude-b-poll.*.log` |

계정 B, C, ...가 아직 이 컴퓨터에 로그인된 적이 없다면, 먼저 사용자에게 해당 프로파일로 로그인해달라고
요청한다 (인터랙티브 브라우저 인증이 필요하므로 자동화하지 말 것):
```sh
CLAUDE_CONFIG_DIR=~/.claude-work claude    # 이후 /login
```

**계정마다 아래 1~7을 반복:**

**1. 준비**

```sh
mkdir -p <해당 계정의 CLAUDE_CONFIG_DIR> ~/RunCatMetrics
```

아래 "파일 내용"의 `runcat-keychain-poll.py`를 해당 계정의 스크립트 경로에 저장 시도.
**파일 쓰기 자체가 차단되면**, 내용을 사용자에게 보여주고 직접 붙여넣어 저장해달라고 요청할 것. 저장 후:
```sh
chmod +x <스크립트 경로>
```
같은 파일 내용을 계정마다 그대로 복사하면 된다 (계정별 차이는 환경변수로만 준다).

**2. 이 계정의 키체인 서비스 이름 확인 (보통 여기서 자동화가 막힘)**

첫 번째로 로그인한 계정은 보통 `Claude Code-credentials` (접미사 없음), 두 번째부터는
`Claude Code-credentials-xxxxxxxx`처럼 임의 접미사가 붙는다. 사용자에게 요청:

1. Spotlight → **키체인 접근(Keychain Access)** 열기
2. 검색창에 `Claude Code-credentials` 입력
3. 여러 항목이 보이면, **각 항목의 정확한 이름**을 알려달라고 요청 (암호는 필요 없음)

여러 계정의 서비스 이름을 한 번에 다 받아뒀다면, 이후 계정마다 반복할 때 다시 물어볼 필요는 없다.
어느 이름이 어느 계정인지 확실치 않으면 3번 테스트에서 나오는 이메일로 구분한다.

**3. 스크립트 테스트 (여기서도 막힐 수 있음)**

```sh
RUNCAT_KEYCHAIN_SERVICE="<이 계정의 이름>" \
CLAUDE_CONFIG_DIR="<이 계정의 설정 디렉터리>" \
RUNCAT_OUT_FILE=/tmp/runcat-test.json \
python3 <스크립트 경로>
cat /tmp/runcat-test.json
```
**차단되면** 위 명령을 사용자에게 그대로 실행해달라고 요청하고 `cat` 결과만 전달받을 것. 이메일이
이 계정과 일치하는지, `계정`/`5시간 한도`가 정상적으로 나오는지 확인. 다른 계정의 이메일이 나오면
2번의 서비스 이름이 잘못 매칭된 것이니 다른 이름으로 다시 시도.

SSL 인증서 오류가 나면:
```sh
"/Applications/Python 3.x/Install Certificates.command"
```

**4. LaunchAgent 등록**

`which python3` 확인 후, "파일 내용"의 plist 템플릿으로 이 계정 전용 plist를 만든다
(`~/Library/LaunchAgents/<이 계정의 Label>.plist`). 위 표에서 정한 값으로 플레이스홀더를 채운다.
**Label과 출력 경로가 다른 계정과 절대 겹치지 않아야 한다.**

**5. LaunchAgent 실행**

```sh
launchctl unload ~/Library/LaunchAgents/<Label>.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/<Label>.plist
launchctl list | grep runcat
```

**6. 동작 확인**

```sh
cat ~/Library/Logs/<이 계정의 에러 로그>
cat <이 계정의 출력 JSON>
```

**7. 다음 계정으로 반복, 모두 끝나면 RunCat Neo 등록 안내**

모든 계정에 대해 1~6을 마쳤으면, RunCat Neo → 설정 → 메트릭 → Custom Metrics 에서 계정 수만큼
소스를 각각 추가하도록 안내. 완료 후 등록된 모든 계정의 Label/경로를 표로 정리해서 보고할 것.

## 문제 해결

- **`HTTP 429 Too Many Requests`**: 같은 계정을 두 프로세스 이상이 동시에 폴링 중일 가능성이 높다.
  `launchctl list | grep runcat`으로 계정별 LaunchAgent가 정확히 하나씩만 있는지 확인. 서로 다른
  계정끼리는 이 문제가 생기지 않는다.
- **아이콘이 겹쳐 보임**: 도메인 첫 글자가 우연히 같은 계정이 있으면 `RUNCAT_SYMBOL` 환경변수로
  plist의 `EnvironmentVariables`에 직접 다른 SF Symbol을 지정할 수 있다.
- **리소스 사용량 우려**: 계정마다 5분에 한 번, 0.5초 남짓 짧게 도는 수준이라 계정이 여러 개여도
  CPU/배터리 영향은 무시할 수 있는 수준이다.

## 파일 내용

### `runcat-keychain-poll.py`

```python
#!/usr/bin/env python3
"""RunCat Neo custom metric — Claude Code usage via direct Keychain + API polling.

Reads this profile's OAuth session credential straight from the macOS
Keychain and calls Anthropic's usage endpoint directly, so it works even
when Claude Code isn't running. Meant to run on a schedule (e.g. every 5
minutes) via a launchd LaunchAgent — one instance per account, each pointed
at that account's own Keychain service name via environment variables.

Required environment variable:
  RUNCAT_KEYCHAIN_SERVICE  Keychain service name for this profile's
                            "Claude Code-credentials" item (may have a
                            per-profile suffix, e.g.
                            "Claude Code-credentials-xxxxxxxx").

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
