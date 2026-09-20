# runcat-claude-usage

[RunCat Neo](https://github.com/runcat-dev/RunCatNeo) 메뉴바에 **Claude Code 사용량**을 띄우는 statusLine 스크립트입니다.
계정이 여러 개면 카드도 계정별로 따로 뜨고, 아이콘은 이메일 도메인 첫 글자(SF Symbol)로 구분됩니다.

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
- 값은 **해당 계정으로 claude 를 마지막에 실행한 시점** 기준입니다. 상시 실시간이 필요하면
  [Simo-C3/runcat-ai-usage](https://github.com/Simo-C3/runcat-ai-usage) 처럼 폴링하는 데몬을 쓰세요.
- Anthropic이 주는 값은 토큰 개수가 아니라 사용률(%)입니다.

## 참고

- [Claude Code — Customize your status line](https://code.claude.com/docs/en/statusline)
- [RunCat Neo — Custom Metrics Schema](https://github.com/runcat-dev/RunCatNeo/blob/main/docs/CustomMetricsSchema.md)
