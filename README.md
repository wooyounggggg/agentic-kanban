# wt-board

Git worktree 기반 병렬 개발을 위한 TUI 칸반보드.

## 설치

```bash
pip install -e .
```

## 실행

```bash
cd <프로젝트 디렉토리>
wt-board init  # 최초 1회
wt-board        # TUI 실행
```

## 파이프라인

각 이슈는 4단계를 거칩니다:

### Plan
구현 계획 수립. m키를 누르면 Spec과 TC(선택) 프롬프트를 입력받습니다.

**프롬프트 decorating:**
```
아래 요구사항을 기반으로 .board/issues/{ticket}/plan.md에 구현 계획을 작성하세요.
{사용자 입력}

[TC 입력이 있으면]
테스트 케이스를 .board/issues/{ticket}/checklist.yaml에 작성하세요.
{TC 입력}
```

### Implement
Plan 기반 자동 구현. m키를 누르면 확인 후 실행됩니다.
프로젝트의 CLAUDE.md가 코드 품질/컨벤션을 관리합니다.

**프롬프트 decorating:**
```
.board/issues/{ticket}/plan.md를 기반으로 구현을 시작하세요.
작업 완료 후 .board/issues/{ticket}/worklog.jsonl에 기록하세요.
```

### Review
코드 수정 단계. m키를 누르면 수정 프롬프트를 입력받습니다.

**프롬프트 decorating:**
```
아래 수정 요청을 반영하세요.
{사용자 입력}
작업 완료 후 .board/issues/{ticket}/worklog.jsonl에 기록하세요.
```

### Completed
완료. h키로 칸반에서 숨기기/보이기.

## 단축키

### 칸반보드
| 키 | 동작 |
|---|---|
| Enter | 이슈 상세 |
| n | 새 이슈 |
| m | 이동 모드 (←→ 로 상태 변경) |
| s | Dooray 동기화 |
| T | 테마 변경 |
| h | 완료 이슈 토글 |
| q (x2) | 종료 |

### 상세 화면
| 키 | 동작 |
|---|---|
| m | 현재 단계 실행 (프롬프트 입력) |
| r | 현재 단계 재실행 안내 |
| a | 에이전트 세션 보기 |
| p | Plan 토글 |
| t | Ticket 토글 |
| c | Comments 토글 |
| l | Worklog 토글 |
| f | Dooray 조회 |
| Esc | 뒤로 |

## 테마

T키로 8가지 테마 선택 가능:
brown, catppuccin, nord, github-dark, dracula, solarized-dark, gruvbox, tokyo-night
