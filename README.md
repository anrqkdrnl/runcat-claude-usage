# runcat-claude-usage

[RunCat Neo](https://github.com/runcat-dev/RunCatNeo) 메뉴바에 **Claude Code 사용량**을 띄우는 statusLine 스크립트입니다.
계정이 여러 개면 카드도 계정별로 따로 뜨고, 아이콘은 이메일 도메인 첫 글자(SF Symbol)로 구분됩니다.

> **주의**: 이 스크립트는 Claude Code의 statusLine 훅이 호출될 때만 값을 갱신합니다.
> 즉 **Claude Code를 실행 중일 때만** `~/RunCatMetrics/claude-*.json` 이 최신 상태가 됩니다.
> Claude Code를 켜지 않아도 항상 최신 값을 보고 싶다면 아래 [실시간 갱신](#claude-code를-켜지-않아도-항상-최신값이-필요하면) 섹션을 참고하세요.

- 5시간 / 주간(7일) 한도 사용률 + 리셋 시각
- 로그인 계정 이메일·조직·현재 모델·컨텍스트 사용률
- 계정별 JSON 분리 (`CLAUDE_CONFIG_DIR` 프로파일 지원)

## 동작 방식

```
claude 실행 → statusLine 훅이 stdin으로 세션 JSON 전달
           → runcat-usage.py 가 ~/RunCatMetrics/claude-*.json 으로 저장
           → RunCat Neo 가 파일 변경을 감지해 메뉴바 갱신
```

## 설치

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

## 계정 두 개 이상 쓰기

Claude Code는 자격증명을 설정 디렉터리 단위로 저장하므로, 프로파일을 나누면 됩니다.

```sh
mkdir -p ~/.claude-personal
cp ~/.claude/settings.json ~/.claude-personal/settings.json   # statusLine 항목이 있어야 함
alias claude2='CLAUDE_CONFIG_DIR=$HOME/.claude-personal claude'
```

`claude2` 로 실행해 `/login` 하면 `~/RunCatMetrics/claude-personal.json` 이 따로 생깁니다.
RunCat에 소스를 하나 더 추가하면 카드가 두 장이 됩니다.

## 환경변수

| 변수 | 설명 |
|---|---|
| `RUNCAT_OUT_FILE` | 출력 JSON 경로를 직접 지정 |
| `RUNCAT_SYMBOL` | 아이콘 SF Symbol 이름을 직접 지정 (예: `star.fill`) |
| `CLAUDE_ACCOUNT_EMAIL` | `~/.claude.json` 에서 계정을 못 읽을 때 수동 지정 |

## 한계

- `rate_limits` 는 claude.ai Pro/Max 구독에서, 세션의 첫 응답 이후에만 내려옵니다.
- 값은 **해당 계정으로 claude 를 마지막에 실행한 시점** 기준입니다. Claude Code를 켜지 않으면 그 시점에 멈춰 있습니다.
- Anthropic이 주는 값은 토큰 개수가 아니라 사용률(%)입니다.
- 다중 계정(`CLAUDE_CONFIG_DIR`)을 상시 폴링 방식으로 돌리는 기본 도구는 없습니다 — 이 저장소의 스크립트로 계속 커버해야 합니다.

## Claude Code를 켜지 않아도 항상 최신값이 필요하면

이 저장소의 스크립트는 **이벤트 기반**(statusLine 호출 시점에만 실행)이라 상시 백그라운드 갱신은 지원하지 않습니다.
항상 최신 상태가 필요하면 [Simo-C3/runcat-ai-usage](https://github.com/Simo-C3/runcat-ai-usage) 를 대신(또는 함께) 쓰세요.
이 도구는 1분마다 사용량 API를 직접 폴링해서 같은 위치(`~/RunCatMetrics/claude-code.json`)에 같은 스키마(Custom Metrics JSON)로 써주는
공식 Homebrew tap 기반 데몬입니다.

### 설치

```sh
brew tap Simo-C3/runcat-ai-usage https://github.com/Simo-C3/runcat-ai-usage
brew trust --formula Simo-C3/runcat-ai-usage/runcat-ai-usage   # 이 formula 하나에만 신뢰 부여
brew install runcat-ai-usage
runcat-ai-usage-install --no-open
```

`runcat-ai-usage-install` 이 60초 주기 LaunchAgent와 로컬 OTel Collector를 등록·기동합니다.
1~2분 안에 `~/RunCatMetrics/claude-code.json` 이 갱신되기 시작하며, 이후로는 Claude Code 앱을 켜지 않아도
매분 자동으로 최신 사용률이 반영됩니다. RunCat Neo에 이미 같은 경로를 소스로 등록해 두었다면 추가 설정이 필요 없습니다.

### 상태 확인

```sh
runcat-ai-usage --doctor
```

LaunchAgent 등록/스케줄, Collector·수신기 동작 여부, 각 JSON의 마지막 갱신 시각을 한 번에 점검합니다(값 자체는 출력하지 않음).

### 표시 항목 조정

```sh
runcat-ai-usage config set --rows rate,change,trend --language ko
```

`--rows`(표시 항목), `--rate-format`, `--percentage-precision`, `--trend-period` 등을 바꿀 수 있습니다.
자세한 옵션은 [원본 README](https://github.com/Simo-C3/runcat-ai-usage#commands) 참고.

### 이 저장소 스크립트와의 차이

| | `runcat-usage.py` (이 저장소) | `runcat-ai-usage` 데몬 |
|---|---|---|
| 갱신 시점 | Claude Code statusLine 이벤트 발생 시 (대화 중에만) | 1분마다 상시 (Claude Code를 꺼도 계속) |
| 다중 계정(`CLAUDE_CONFIG_DIR`) | 지원 ("계정 두 개 이상 쓰기" 참고) | 기본 미지원 (계정 하나만) |
| 설치 방식 | 파일 복사 + Python 표준 라이브러리만 | Homebrew + 로컬 OTel Collector |
| 표시 값 | 5시간/주간 사용률, 계정, 모델, 컨텍스트 사용률 | Rate, Today/1h 변화량, 7일 트렌드, 토큰·비용 추정치 |
| 지원 대상 | Claude Code 전용 | Claude Code, Codex, GitHub Copilot |

**두 계정을 동시에 카드로 보고 싶다면**: 메인 계정은 `runcat-ai-usage` 데몬으로 상시 갱신하고,
두 번째 계정(`CLAUDE_CONFIG_DIR` 프로파일)은 이 저장소의 `runcat-usage.py` 를 statusLine으로 계속 사용하는 조합을 권장합니다
(단, 그 계정 카드는 해당 프로파일로 `claude` 를 실행했을 때만 갱신됩니다).

## 참고

- [Claude Code — Customize your status line](https://code.claude.com/docs/en/statusline)
- [RunCat Neo — Custom Metrics Schema](https://github.com/runcat-dev/RunCatNeo/blob/main/docs/CustomMetricsSchema.md)
