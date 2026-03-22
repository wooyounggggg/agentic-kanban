<p align="center">
  <h1 align="center">agentic-kanban</h1>
  <p align="center">
    <strong>AI 에이전트 기반 터미널 칸반보드</strong>
  </p>
  <p align="center">
    이슈마다 AI 에이전트를 할당하고, Plan → Implement → Review 파이프라인을 실행합니다.
  </p>
</p>

<p align="center">
  <a href="https://github.com/wooyounggggg/agentic-kanban/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python"></a>
  <a href="https://github.com/wooyounggggg/agentic-kanban/issues"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

---

![Board Screenshot](docs/demo.svg)

## 왜 만들었나

AI 코딩 도구는 보통 한 번에 하나의 작업만 처리합니다. 여러 이슈를 병렬로 돌리고 싶으면 터미널을 여러 개 열고, 각각 프롬프트를 입력하고, 결과를 따로 확인해야 합니다.

agentic-kanban은 이 과정을 칸반보드 하나로 통합합니다. 이슈를 등록하고, `r`키 하나로 에이전트를 실행하고, 결과를 한 화면에서 확인합니다.

## 주요 기능

- **칸반보드** — Plan 📝 → Implement 🔨 → Review 🔍 → Completed ✅ 4단계 파이프라인
- **AI 에이전트** — `r`키로 실행, [Claude Code](https://docs.anthropic.com/en/docs/claude-code)가 백그라운드에서 작업
- **실시간 로그** — Agent 탭에서 에이전트 출력을 실시간 스트리밍으로 확인
- **Dooray 연동** — [NHN Dooray](https://dooray.com) 티켓 조회, 댓글, 60초 자동 동기화
- **멀티 프로젝트** — 사이드바에서 프로젝트 전환, Git worktree 기반 격리
- **테마** — 8가지 (brown, catppuccin, nord, github-dark, dracula, solarized-dark, gruvbox, tokyo-night)
- **Claude Code 플러그인** — TUI 없이 `/agentic-kanban:plan` 등 슬래시 커맨드로도 사용 가능

## 시작하기

### 요구사항

- Python 3.9+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- [NHN Dooray](https://dooray.com) 계정 + API key (이슈 연동 시)

### 설치

```bash
git clone https://github.com/wooyounggggg/agentic-kanban.git
cd agentic-kanban
./install.sh   # pip install + Claude Code 스킬 설치
```

또는 수동으로:
```bash
pip install -e .
```

### 실행

```bash
cd <프로젝트 디렉토리>
agentic-kanban init    # 최초 1회 — .kanban/ 생성
agentic-kanban         # TUI 실행
```

## 사용 흐름

### 1. 이슈 등록

`n`키를 누르고 Dooray 티켓 번호를 입력하면, 제목을 자동 조회하고 이슈를 등록합니다. Git worktree도 함께 생성됩니다.

### 2. Plan 작성

이슈를 선택하고 `r`키를 누르면, Spec과 참고 지식을 입력하는 창이 뜹니다. 실행하면 에이전트가 `plan.md`를 작성합니다.

### 3. 구현

`m`키로 Implement 상태로 이동한 뒤 `r`키를 누르면, plan.md를 기반으로 에이전트가 코드를 구현합니다.

### 4. 리뷰

Review 상태에서 `r`키를 누르면, 수정 요청을 입력할 수 있습니다. 에이전트가 코드를 수정합니다.

### 5. 완료

`m`키로 Completed로 이동. `v`키로 칸반에서 숨기기/보이기.

## Dooray 연동

[NHN Dooray](https://dooray.com) 이슈 트래커와 연동됩니다:

- `n`키로 이슈 추가 시 티켓번호 입력 → 제목 자동 조회
- `f`키로 Dooray 본문/댓글 fetch
- 60초 주기 자동 폴링 (제목, 상태, 담당자)
- Dooray workflow 한글명을 카드에 chip으로 표시

## Claude Code 플러그인

TUI 없이 Claude Code 세션에서 직접 사용할 수 있습니다.

```
/agentic-kanban:setup 3724        # 티켓 → 이슈 + worktree 생성
/agentic-kanban:plan 3724         # plan.md 대화형 작성
/agentic-kanban:implement 3724    # plan 기반 구현
/agentic-kanban:review 3724       # 코드 리뷰 + 수정
```

스킬과 TUI는 `.kanban/` 데이터를 공유합니다. 스킬로 작성한 plan.md를 TUI에서 확인하고, TUI에서 등록한 이슈를 스킬에서 작업할 수 있습니다.

## 구조

```
┌─────────────────────────────────────────────────────────┐
│                    agentic-kanban                         │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Plan 📝  │  │ Impl 🔨  │  │Review 🔍 │  │Completed✅│ │
│  │ #101     │  │ #103 ⟳  │  │ #105     │  │ #106     │ │
│  │ #102     │  │ #104     │  │          │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                           │
│  r → 프롬프트 입력 → claude 실행 → 결과 저장               │
│  /agentic-kanban:plan → 대화형 → plan.md 저장             │
└─────────────────────────────────────────────────────────┘
```

## 설정

```yaml
# .kanban/config.yaml (프로젝트별)
project:
  name: my-project
  worktree_base: worktrees
  base_branch: develop

tracker:
  type: dooray
  dooray:
    cli_path: tools/dooray-cli.js
    api_key: <your-api-key>
  sync_interval: 60
```

```yaml
# ~/.config/agentic-kanban/settings.yaml (전역)
theme: dracula
```

## 데이터

```
.kanban/
├── config.yaml          # 프로젝트 설정
├── issues/
│   └── {ticket}/
│       ├── issue.yaml     # 이슈 메타
│       ├── plan.md        # 구현 계획
│       ├── checklist.yaml # TC
│       ├── worklog.jsonl  # 작업 로그
│       ├── agent.log      # 에이전트 실시간 로그
│       ├── description.md # Dooray 본문
│       └── comments.md    # Dooray 댓글
├── archive/
└── cache/
```

## 라이선스

[MIT](LICENSE)
