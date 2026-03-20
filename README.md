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

![Board Screenshot](docs/screenshot-board.svg)

## Why agentic-kanban?

> 여러 이슈를 병렬로 AI에게 맡기고, 결과를 한눈에 관리하고 싶다.

기존 AI 코딩 도구는 **한 번에 하나의 작업**만 처리합니다. agentic-kanban은 칸반보드에서 여러 이슈에 각각 AI 에이전트를 할당하고, **정해진 파이프라인**(Plan → Implement → Review)에 따라 자동 실행합니다. 개발자는 프롬프트를 입력하고 결과를 확인하기만 하면 됩니다.

## Features

- 📋 **칸반보드** — 이슈 상태를 한눈에. 마우스/키보드 네비게이션, vim 키바인딩
- 🤖 **AI 파이프라인** — `r`키 하나로 Plan/Implement/Review 단계별 에이전트 실행
- 📡 **실시간 스트리밍** — 에이전트 작업 진행 상황을 Agent 탭에서 실시간 확인
- 🔗 **Dooray 연동** — NHN Dooray 티켓 조회, 댓글, 상태 자동 동기화 (60초 폴링)
- 📁 **멀티 프로젝트** — 사이드바에서 프로젝트 전환, Git worktree 기반 격리
- 🎨 **8가지 테마** — brown, catppuccin, nord, github-dark, dracula, solarized-dark, gruvbox, tokyo-night

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

> **Tip:** pip 설치 없이 바로 실행하려면:
> ```bash
> PYTHONPATH=agentic-kanban/src python3 -m agentic_kanban.cli.main
> ```

## Pipeline

각 이슈는 4단계 파이프라인을 거칩니다. `r`키로 실행합니다.

| 단계 | 설명 | 입력 | 산출물 |
|------|------|------|--------|
| 📝 **Plan** | 구현 계획 수립 | Spec + 참고 지식 + TC(선택) | `plan.md` |
| 🔨 **Implement** | Plan 기반 자동 구현 | 확인(Confirm) | 코드 변경 |
| 🔍 **Review** | 코드 수정 | 수정 프롬프트 | 코드 수정 |
| ✅ **Completed** | 완료 | — | — |

> **Note:** 각 단계에서 에이전트는 프로젝트의 `CLAUDE.md`를 참조하여 코드 컨벤션과 품질을 유지합니다. 작업 결과는 `worklog.jsonl`에 bullet list로 요약 저장됩니다.

## Keyboard Shortcuts

### 칸반보드

| 키 | 동작 |
|---|---|
| `Enter` | 이슈 상세 |
| `r` | 파이프라인 실행 |
| `n` | 새 이슈 추가 (Dooray 조회) |
| `m` | 상태 이동 |
| `x` | 이슈 삭제 |
| `v` | 완료 이슈 토글 |
| `T` | 테마 변경 |
| `?` | 도움말 |
| `←→↑↓` / `hjkl` | 네비게이션 |
| `q` (x2) | 종료 |

### 상세 화면

| 키 | 동작 |
|---|---|
| `r` | 파이프라인 실행 |
| `m` | 상태 이동 |
| `a` | Agent 로그 (실시간 스트리밍) |
| `p` | Plan |
| `t` | Ticket (Dooray 본문) |
| `c` | Comments (Dooray 댓글) |
| `l` | Worklog |
| `f` | Dooray 조회 |
| `Space` | TC 체크 토글 |
| `Esc` | 뒤로 |

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    agentic-kanban                         │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 📝 Plan  │  │🔨 Impl   │  │🔍 Review │  │✅ Done   │ │
│  │          │  │          │  │          │  │          │ │
│  │ #101     │  │ #103 ⟳  │  │ #105     │  │ #106     │ │
│  │ #102     │  │ #104     │  │          │  │          │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│                                                           │
│  r키 → 프롬프트 입력 → claude --print 실행 → 결과 저장    │
│                                                           │
│  .board/issues/{ticket}/                                  │
│  ├── plan.md          ← 에이전트가 작성                    │
│  ├── agent.log        ← 실시간 스트리밍                    │
│  └── worklog.jsonl    ← 작업 요약 자동 기록                │
└─────────────────────────────────────────────────────────┘
```

## Data Structure

```
.board/
├── config.yaml          # 프로젝트 설정 (Dooray API key, 테마 등)
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

## Configuration

```yaml
# .board/config.yaml
project:
  name: my-project
  worktree_base: worktrees
  base_branch: develop

tracker:
  type: dooray
  dooray:
    cli_path: ~/.mcp-global-server/dooray-cli.js
    api_key: <your-api-key>
  sync_interval: 60

agent:
  binary: claude
  max_concurrent: 3

ui:
  theme: brown
```

## License

[MIT](LICENSE)
