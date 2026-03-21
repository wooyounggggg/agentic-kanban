---
name: implement
description: plan.md를 기반으로 코드를 구현합니다.
user-invocable: true
argument-hint: <ticket-number>
---

# agentic-kanban:implement

plan.md를 읽고 코드를 구현합니다. 프로젝트의 CLAUDE.md 컨벤션을 따릅니다.

## 입력

```
/agentic-kanban:implement <ticket-number>
```

사용자 입력: $ARGUMENTS

## 처리 절차

1. `.board/issues/{ticket}/plan.md` 읽기. 없으면 "/agentic-kanban:plan을 먼저 실행하세요" 안내.

2. `.board/issues/{ticket}/checklist.yaml` 읽기 (TC가 있으면 참고).

3. plan.md의 구현 단계를 순서대로 실행:
   - 파일 생성/수정
   - 테스트 작성 (TC가 있으면)
   - 빌드 확인

4. 프로젝트의 `CLAUDE.md`를 참조하여 코드 컨벤션/품질 유지.

5. 구현 완료 후:
   - `.board/issues/{ticket}/worklog.jsonl` 에 작업 기록
   - checklist.yaml의 TC 항목 체크 (통과 시)
   - 변경 파일 목록 요약

## 산출물

- 코드 변경 (worktree 내)
- `.board/issues/{ticket}/worklog.jsonl` — 구현 내역 기록

## 주의사항

- 반드시 worktree 디렉토리에서 실행 (또는 worktree 경로 자동 탐지)
- plan.md가 없으면 실행하지 않음 (gate)
- 기존 코드 컨벤션을 따르며, CLAUDE.md가 있으면 우선 참조
