<p align="center">
  <h1 align="center">agentic-kanban</h1>
  <p align="center">
    <strong>AI 에이전트가 작업하는 터미널 칸반보드</strong>
  </p>
  <p align="center">
    이슈별 AI 에이전트를 할당하여 Plan → Implement → Review 파이프라인을 자동 실행합니다.
  </p>
</p>

<p align="center">
  <a href="https://github.com/wooyounggggg/agentic-kanban/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python"></a>
  <a href="https://github.com/wooyounggggg/agentic-kanban/issues"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

---

![Board Screenshot](docs/demo.svg)

## Why agentic-kanban?

> 여러 이슈를 병렬로 AI에게 맡기고, 결과를 한눈에 관리하고 싶다.

기존 AI 코딩 도구는 한 번에 하나의 작업만 처리합니다. agentic-kanban은 칸반보드에서 여러 이슈에 각각 AI 에이전트를 할당하고, 정해진 파이프라인에 따라 자동 실행합니다.

- 📋 **칸반보드** — 이슈 상태를 한눈에. vim 키바인딩 지원
- 🤖 **AI 파이프라인** — Plan → Implement → Review 단계별 에이전트 실행
- 📡 **실시간 스트리밍** — 에이전트 작업 진행 상황을 Agent 탭에서 실시간 확인
- 🔗 **Dooray 연동** — [NHN Dooray](https://dooray.com) 티켓 조회, 댓글, 상태 자동 동기화
- 📁 **멀티 프로젝트** — 사이드바에서 프로젝트 전환, Git worktree 기반 격리
- 🎨 **8가지 테마** — brown, catppuccin, nord, github-dark, dracula, solarized-dark, gruvbox, tokyo-night
- 🔌 **Claude Code 플러그인** — TUI 없이 `/agentic-kanban:plan` 등 슬래시 커맨드로 사용 가능

## Quick Start

### 요구사항

- Python 3.9+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude` 명령)
- [NHN Dooray](https://dooray.com) 계정 + API key (이슈 연동 시)

### 설치

```bash
git clone https://github.com/wooyounggggg/agentic-kanban.git
cd agentic-kanban
pip install -e .
```

### 실행

```bash
cd <프로젝트 디렉토리>
agentic-kanban init    # 최초 1회 — .board/ 생성, Dooray API key 설정
agentic-kanban         # TUI 실행
```

## Pipeline

각 이슈는 4단계 파이프라인을 거칩니다. `r`키로 실행합니다.

| 단계 | 설명 | 산출물 |
|------|------|--------|
| 📝 **Plan** | Spec + 참고 지식으로 구현 계획 수립 | `plan.md` |
| 🔨 **Implement** | Plan 기반 자동 구현 | 코드 변경 |
| 🔍 **Review** | 수정 프롬프트로 코드 수정 | 코드 수정 |
| ✅ **Completed** | 완료 | — |

에이전트는 [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)를 백그라운드로 실행하며, 결과는 `agent.log`에 실시간 스트리밍됩니다. 작업 완료 시 `worklog.jsonl`에 bullet list로 요약 저장됩니다.

## Dooray 연동

[NHN Dooray](https://dooray.com) 이슈 트래커와 연동됩니다:

- **티켓 조회** — `n`키로 이슈 추가 시 Dooray 티켓번호 입력 → 제목 자동 조회
- **본문 + 댓글** — `f`키로 Dooray 본문/댓글 fetch → Ticket/Comments 탭에 표시
- **상태 동기화** — 60초 주기 자동 폴링 (제목, 상태, 담당자)
- **한글 상태명** — Dooray workflow 한글명을 카드에 chip으로 표시

연동에는 `tools/dooray-cli.js` (프로젝트에 포함)와 Dooray API key가 필요합니다.

## Claude Code Plugin

TUI 없이 Claude Code 세션에서 직접 사용할 수 있는 스킬 플러그인을 제공합니다.

### 설치

```bash
claude plugin add ./plugin
```

### 사용

```
/agentic-kanban:setup 3724        # 티켓 → 칸반 이슈 + worktree 생성
/agentic-kanban:plan 3724         # plan.md 대화형 작성
/agentic-kanban:implement 3724    # plan 기반 코드 구현
/agentic-kanban:review 3724       # 코드 리뷰 + 수정
```

스킬은 `.board/` 데이터를 TUI와 공유합니다. 스킬로 만든 plan.md를 TUI에서 확인하고, TUI에서 만든 이슈를 스킬에서 작업할 수 있습니다.

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    agentic-kanban                         │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Plan 📝  │  │ Impl 🔨  │  │Review 🔍 │  │ Done ✅  │ │
│  │ #101     │  │ #103 ⟳  │  │ #105     │  │ #106     │ │
│  │ #102     │  │ #104     │  │          │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                           │
│  r키 → 프롬프트 입력 → claude 실행 → 결과 저장             │
│  /agentic-kanban:plan → 대화형 → plan.md 저장             │
└─────────────────────────────────────────────────────────┘
```

## Configuration

```yaml
# .board/config.yaml (프로젝트별)
project:
  name: my-project
  worktree_base: worktrees   # 절대경로도 가능: ~/worktrees/my-project
  base_branch: develop

tracker:
  type: dooray
  dooray:
    cli_path: tools/dooray-cli.js
    api_key: <your-api-key>
  sync_interval: 60

agent:
  binary: claude
  max_concurrent: 3
```

```yaml
# ~/.config/agentic-kanban/settings.yaml (전역)
theme: dracula
```

## Data Structure

```
.board/
├── config.yaml          # 프로젝트 설정
├── issues/
│   └── {ticket}/
│       ├── issue.yaml     # 이슈 메타데이터
│       ├── plan.md        # 구현 계획
│       ├── checklist.yaml # TC 체크리스트
│       ├── worklog.jsonl  # 작업 로그
│       ├── agent.log      # 에이전트 실시간 로그
│       ├── description.md # Dooray 본문
│       └── comments.md    # Dooray 댓글
├── archive/              # 완료 이슈
└── cache/                # 캐시
```

## License

[MIT](LICENSE)
