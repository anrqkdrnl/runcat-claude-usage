# runcat-claude-usage

[RunCat Neo](https://github.com/runcat-dev/RunCatNeo) 메뉴바에 **Claude Code 사용량**(5시간/주간 한도, 계정, 조직)을
띄우는 두 가지 스크립트입니다. 계정이 여러 개면 카드도 계정별로 따로 뜨고, 아이콘은 이메일 도메인 첫 글자(SF Symbol,
예: `hanyang.ac.kr` → **H**, `gmail.com` → **G**)로 구분됩니다.

## 방법이 두 가지인 이유

| | `runcat-usage.py`<br>(간단, statusLine 훅) | `runcat-keychain-poll.py`<br>(완전 자동, 백그라운드 폴링) |
|---|---|---|
| 갱신 시점 | Claude Code statusLine 이벤트 발생 시 (**대화 중에만**) | LaunchAgent가 **5분마다 상시** (Claude Code를 꺼도 계속) |
| 설치 난이도 | 아주 쉬움 (파일 복사 1개 + 설정 1줄) | 계정마다 키체인 서비스 이름을 확인하는 수동 단계 필요 |
| 의존성 | 없음 (Python 표준 라이브러리만) | 없음 (Python 표준 라이브러리 + macOS `security` CLI) |
| 다중 계정 | 프로파일(`CLAUDE_CONFIG_DIR`)별로 자동 분리 | 계정마다 LaunchAgent를 하나씩 따로 설치 |

**Claude Code를 계속 켜놓고 쓴다면 방법 A로 충분합니다.** Claude Code를 안 켜도 메뉴바 값이 항상 최신이길
원한다면 방법 B를 쓰세요. 계정이 2개면 "계정 1개짜리 방법 B"를 계정 수만큼 반복하면 됩니다 — 아래
[계정 2개 이상](#계정-2개-이상-쓰기-방법-b) 섹션에 그대로 정리해 뒀습니다.

### Claude Code에게 통째로 맡기기

아래 문서를 직접 따라 하는 대신, 4가지 경우에 맞는 작업지시서를 [`claude-setup-orders/`](claude-setup-orders/)에
준비해 뒀습니다. 해당하는 파일 하나를 그대로 Claude Code에게 주면 처음부터 끝까지 자동으로 진행합니다
(단, 방법 B는 키체인 자격증명을 다루는 특성상 몇몇 단계에서 사용자 확인/직접 실행을 요청할 수 있습니다 —
각 문서에 그 부분이 명시돼 있습니다):

- [`A-single-account.md`](claude-setup-orders/A-single-account.md) — 방법 A, 계정 1개
- [`A-multi-account.md`](claude-setup-orders/A-multi-account.md) — 방법 A, 계정 2개 이상
- [`B-single-account.md`](claude-setup-orders/B-single-account.md) — 방법 B, 계정 1개
- [`B-multi-account.md`](claude-setup-orders/B-multi-account.md) — 방법 B, 계정 2개 이상

---

## 방법 A: 간단 설치 (statusLine 훅)

### 동작 방식

```
claude 실행 → statusLine 훅이 stdin으로 세션 JSON 전달
           → runcat-usage.py 가 ~/RunCatMetrics/claude-*.json 으로 저장
           → RunCat Neo 가 파일 변경을 감지해 메뉴바 갱신
```

### 계정 1개

```sh
mkdir -p ~/.claude ~/RunCatMetrics
cp runcat-usage.py ~/.claude/runcat-usage.py
chmod +x ~/.claude/runcat-usage.py
```

`~/.claude/settings.json` 에 등록:

```json
{
  "statusLine": { "type": "command", "command": "python3 $HOME/.claude/runcat-usage.py" }
}
```

`claude` 를 실행해 응답을 한 번 받으면 `~/RunCatMetrics/claude-code.json` 이 생깁니다.
RunCat Neo → 설정 → 메트릭 → `+ 사용자 설정 메트릭 소스 추가` → `Cmd+Shift+G` → 그 경로 입력.

### 계정 2개 이상

Claude Code는 자격증명을 설정 디렉터리 단위로 저장하므로, 프로파일을 나누면 됩니다.

```sh
mkdir -p ~/.claude-personal
cp ~/.claude/settings.json ~/.claude-personal/settings.json   # statusLine 항목이 있어야 함
alias claude2='CLAUDE_CONFIG_DIR=$HOME/.claude-personal claude'
```

`claude2` 로 실행해 `/login` 하면 `~/RunCatMetrics/claude-personal.json` 이 따로 생깁니다.
RunCat에 소스를 하나 더 추가하면 카드가 두 장이 됩니다. 세 번째 계정도 같은 방식(`~/.claude-work` 등)으로 늘리면 됩니다.

### 방법 A의 한계

- **Claude Code를 실행 중일 때만** 값이 갱신됩니다. 마지막으로 그 계정의 `claude`를 실행한 시점에서 멈춰 있습니다.
- `rate_limits`는 claude.ai Pro/Max 구독에서, 세션의 첫 응답 이후에만 내려옵니다.
- Anthropic이 주는 값은 토큰 개수가 아니라 사용률(%)입니다.

항상 최신값이 필요하면 아래 방법 B로 넘어가세요.

---

## 방법 B: 완전 자동 (Keychain 폴링 + LaunchAgent)

### 동작 방식

Claude Code는 로그인한 계정의 OAuth 세션 토큰을 macOS **키체인**에 저장합니다.
`runcat-keychain-poll.py`는 이 토큰을 직접 읽어(`security find-generic-password`) Anthropic 사용량 API
(`https://api.anthropic.com/api/oauth/usage`)를 호출하고 결과를 RunCat용 JSON으로 저장합니다.
이 과정을 **launchd(LaunchAgent)**가 5분마다 자동으로 실행해주므로, Claude Code를 아예 켜지 않아도
메뉴바 값이 항상 최신 상태로 유지됩니다.

```
launchd (5분마다) → runcat-keychain-poll.py
                     → security find-generic-password 로 키체인에서 토큰 읽기
                     → api.anthropic.com/api/oauth/usage 호출
                     → ~/RunCatMetrics/<계정>.json 으로 저장
                     → RunCat Neo 가 파일 변경 감지해 메뉴바 갱신
```

### 계정 1개짜리 설치, A부터 Z까지

**a. 저장소 파일 받기**

```sh
git clone https://github.com/<your-username>/runcat-claude-usage.git
cd runcat-claude-usage
```

**b. 이 계정의 키체인 서비스 이름 확인하기**

Claude Code에 로그인된 계정마다 macOS 키체인에 `Claude Code-credentials`라는 이름의 항목이 생깁니다.
계정이 하나뿐이면 이름 그대로지만, 두 번째 계정부터는 `Claude Code-credentials-xxxxxxxx`처럼 임의의
접미사가 붙습니다. 정확한 이름을 확인하려면:

1. Spotlight(`Cmd+Space`)에서 **키체인 접근(Keychain Access)** 앱을 엽니다.
2. 검색창에 `Claude Code-credentials` 를 입력합니다.
3. 항목이 여러 개면(계정이 여러 개면) **수정일**로 어떤 게 방금 로그인한 계정인지 짐작할 수 있고,
   확실히 하려면 아래 "d. 스크립트 테스트"에서 각 이름으로 실행해보고 나오는 이메일로 구분하세요.
4. **이름 열을 그대로 복사**해 둡니다. (예: `Claude Code-credentials` 또는 `Claude Code-credentials-xxxxxxxx`)

**c. 스크립트 설치**

```sh
mkdir -p ~/.claude ~/RunCatMetrics
cp runcat-keychain-poll.py ~/.claude/runcat-keychain-poll.py
chmod +x ~/.claude/runcat-keychain-poll.py
```

**d. 스크립트 테스트 실행**

`b`에서 확인한 이름을 그대로 넣어 실행합니다 (따옴표 안의 값만 본인 것으로 교체):

```sh
RUNCAT_KEYCHAIN_SERVICE="Claude Code-credentials" \
RUNCAT_OUT_FILE=/tmp/runcat-test.json \
python3 ~/.claude/runcat-keychain-poll.py

cat /tmp/runcat-test.json
```

`계정: your@email.com` 이 보이고 `5시간 한도`/`주간 한도`가 숫자로 나오면 성공입니다. macOS가 "키체인 접근을
허용하시겠습니까?" 팝업을 띄우면 **항상 허용**을 눌러주세요 (매번 물어보지 않게 됩니다). `HTTPError: 401/403`이 뜨면
서비스 이름이 틀린 것이니 `b`로 돌아가 다른 이름으로 다시 시도하세요.

**e. LaunchAgent 등록 (실제 경로로 자동 실행되게 만들기)**

먼저 python3 경로를 확인합니다: `which python3`

템플릿(`runcat-keychain-poll.plist.template`)을 복사해서 값을 채웁니다:

```sh
cp runcat-keychain-poll.plist.template ~/Library/LaunchAgents/local.runcat.claude-poll.plist
```

에디터로 열어(`nano ~/Library/LaunchAgents/local.runcat.claude-poll.plist`) 아래 6곳을 본인 값으로 바꿉니다:

| 플레이스홀더 | 채울 값 | 예시 |
|---|---|---|
| `LABEL` | 아무 고유 이름 | `local.runcat.claude-poll` |
| `PYTHON3_PATH` | `which python3` 결과 | `/usr/bin/python3` |
| `SCRIPT_PATH` | `c`에서 복사한 스크립트 경로 | `/Users/you/.claude/runcat-keychain-poll.py` |
| `KEYCHAIN_SERVICE` | `b`에서 확인한 이름 | `Claude Code-credentials` |
| `CONFIG_DIR` | 이 계정의 Claude 설정 디렉터리 | `/Users/you/.claude` |
| `LOG_OUT_PATH` / `LOG_ERR_PATH` | 로그 저장 경로 | `/Users/you/Library/Logs/runcat-claude-poll.log` 등 |

**f. LaunchAgent 실행**

```sh
launchctl unload ~/Library/LaunchAgents/local.runcat.claude-poll.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/local.runcat.claude-poll.plist
launchctl list | grep runcat   # 방금 등록한 Label이 보이면 정상
```

**g. 정상 동작 확인**

```sh
cat ~/RunCatMetrics/claude-code-credentials.json   # 파일명은 서비스 이름을 슬러그화한 것
```

값이 채워져 있고 `lastUpdatedDate`가 방금이면 성공입니다. 5분 뒤 다시 확인해서 시각이 갱신됐는지도 보세요.

**h. RunCat Neo에 등록**

설정 → 메트릭 → Custom Metrics → `+ 사용자 설정 메트릭 소스 추가` → `Cmd+Shift+G` → `g`에서 확인한 경로 입력.

**i. (선택) 로그인 시 자동 시작 확인**

`~/Library/LaunchAgents/`에 넣은 LaunchAgent는 로그인할 때 macOS가 자동으로 로드합니다. 재부팅 후에도
`launchctl list | grep runcat`으로 떠 있는지 확인하면 끝입니다.

### 계정 2개 이상 쓰기 (방법 B)

위 a~i를 계정 수만큼 반복하되, 매번 아래 값만 바꿔주면 됩니다:

- `b`에서 확인하는 키체인 서비스 이름 (계정마다 다름)
- `c`에서 스크립트를 복사할 경로 — 계정별로 구분되는 디렉터리에 두는 걸 권장 (예: 두 번째 계정이
  `CLAUDE_CONFIG_DIR=~/.claude-personal` 프로파일이면 `~/.claude-personal/runcat-keychain-poll.py`)
- `e`의 `LABEL`, `KEYCHAIN_SERVICE`, `CONFIG_DIR`, 로그 경로 — 계정마다 겹치지 않게

예시 (계정 A: 기본 프로파일, 계정 B: `CLAUDE_CONFIG_DIR=~/.claude-work` 프로파일):

```sh
# 계정 A (기본)
RUNCAT_KEYCHAIN_SERVICE="Claude Code-credentials" \
CLAUDE_CONFIG_DIR="$HOME/.claude" \
RUNCAT_OUT_FILE="$HOME/RunCatMetrics/claude-a.json" \
python3 ~/.claude/runcat-keychain-poll.py

# 계정 B (두 번째 프로파일)
RUNCAT_KEYCHAIN_SERVICE="Claude Code-credentials-xxxxxxxx" \
CLAUDE_CONFIG_DIR="$HOME/.claude-work" \
RUNCAT_OUT_FILE="$HOME/RunCatMetrics/claude-b.json" \
python3 ~/.claude-work/runcat-keychain-poll.py
```

각각 잘 나오면 `e`~`h`를 계정별로 반복해서 LaunchAgent 2개(`Label`이 서로 달라야 함)와 RunCat 소스 2개를 등록하세요.
**중요**: 계정마다 LaunchAgent는 하나씩만 유지하세요 — 같은 계정을 두 프로세스가 동시에 폴링하면 아래
[429 오류](#레이트리밋-http-429-too-many-requests) 문제가 생깁니다.

---

## 문제 해결

### SSL 인증서 오류 (`CERTIFICATE_VERIFY_FAILED`)

python.org에서 받은 Python(프레임워크 설치)은 CA 인증서 번들이 기본으로 없습니다. 아래를 한 번 실행하세요:

```sh
"/Applications/Python 3.x/Install Certificates.command"
```

### 레이트리밋 (`HTTP 429 Too Many Requests`)

같은 계정을 여러 프로세스가 동시에 폴링하면(예: 이 스크립트 + 다른 사용량 도구를 같은 계정에 같이 돌리는 경우)
Anthropic 사용량 API가 요청을 거부할 수 있습니다.

- 같은 계정을 폴링하는 프로세스가 두 개 이상 떠 있지 않은지 확인하세요 (`launchctl list | grep runcat`).
- 폴링 주기는 1분보다 **5분(`StartInterval: 300`) 이상을 권장**합니다. 5시간/주간 사용률은 그렇게 빨리
  바뀌지 않으므로 5분 간격으로도 체감 차이가 거의 없고, 리소스도 더 적게 씁니다.
- 한 번 429가 뜨면 몇 분간 쿨다운이 걸릴 수 있습니다. 재시도를 반복하지 말고 다음 정기 실행(5분 뒤)까지 기다리세요.

### 리소스 사용량이 걱정된다면

`runcat-keychain-poll.py`는 상주 프로세스가 아니라 launchd가 주기적으로 잠깐 띄웠다 바로 끝내는 방식입니다.
한 번 실행에 키체인 조회 1번 + API 요청 1번 + 파일 쓰기 1번 정도로, 5분에 한 번 0.5초 남짓 짧게 도는 수준이라
CPU/배터리에 미치는 영향은 무시할 수 있는 수준입니다.

### Claude Code(AI 어시스턴트)에게 이 설치를 대신 시키면?

이 저장소를 Claude Code에게 주고 "설치해줘"라고 하면, **키체인에서 자격증명을 읽는 부분(위 b, d 단계)은
자동으로 진행되지 않을 수 있습니다.** Claude Code의 안전장치가 "OAuth 세션 토큰을 자동으로 찾아 읽는 동작"을
자격증명 탐색으로 분류해 차단하기 때문입니다(의도된 보안 동작입니다). 이 경우 Claude Code가 스크립트 내용을
보여주며 직접 파일에 붙여넣기를 요청하거나, 키체인 접근 앱에서 서비스 이름을 확인해달라고 요청할 수 있습니다 —
위 b, d 단계를 안내받은 대로 직접 실행해주시면 나머지(LaunchAgent 설치, RunCat 등록 등)는 이어서 진행됩니다.

---

## 환경변수

### `runcat-usage.py` (방법 A)

| 변수 | 설명 |
|---|---|
| `RUNCAT_OUT_FILE` | 출력 JSON 경로를 직접 지정 |
| `RUNCAT_SYMBOL` | 아이콘 SF Symbol 이름을 직접 지정 (예: `star.fill`) |
| `CLAUDE_ACCOUNT_EMAIL` | `~/.claude.json` 에서 계정을 못 읽을 때 수동 지정 |

### `runcat-keychain-poll.py` (방법 B)

| 변수 | 필수 | 설명 |
|---|---|---|
| `RUNCAT_KEYCHAIN_SERVICE` | 예 | 이 계정의 키체인 서비스 이름 (위 "b" 단계 참고) |
| `CLAUDE_CONFIG_DIR` | 아니오 | 계정 이메일/조직을 읽어올 설정 디렉터리 (기본: `~/.claude`) |
| `RUNCAT_OUT_FILE` | 아니오 | 출력 JSON 경로 (기본: 서비스 이름을 슬러그화해서 `~/RunCatMetrics/`에 저장) |
| `RUNCAT_SYMBOL` | 아니오 | 아이콘 SF Symbol 이름을 직접 지정 |

## 한계

- Anthropic이 주는 값은 토큰 개수가 아니라 사용률(%)입니다.
- 방법 A는 Claude Code를 켜지 않으면 갱신되지 않고, 방법 B는 macOS 키체인에 의존하므로 Windows/Linux에서는
  동작하지 않습니다 (둘 다 macOS + RunCat Neo 전용입니다).
- 키체인 서비스 이름의 접미사(`-xxxxxxxx`)는 Claude Code 내부 구현이라 향후 버전에서 규칙이 바뀔 수 있습니다.

## 참고

- [Claude Code — Customize your status line](https://code.claude.com/docs/en/statusline)
- [RunCat Neo — Custom Metrics Schema](https://github.com/runcat-dev/RunCatNeo/blob/main/docs/CustomMetricsSchema.md)
