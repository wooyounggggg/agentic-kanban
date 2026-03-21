---
name: review
description: 구현된 코드를 리뷰하고 수정 요청을 반영합니다.
user-invocable: true
argument-hint: <ticket-number> [수정 요청]
---

# agentic-kanban:review

구현된 코드를 리뷰하거나, 수정 요청을 받아 반영합니다.

## 입력

```
/agentic-kanban:review <ticket-number> [수정 요청 내용]
```

사용자 입력: $ARGUMENTS

## 처리 절차

1. `.board/issues/{ticket}/issue.yaml` 읽기.

2. worktree의 변경사항 확인:
   ```bash
   git diff --stat
   ```

3. 수정 요청이 있으면:
   - 요청 내용을 반영하여 코드 수정
   - 테스트 실행
   - 변경사항 요약

4. 수정 요청이 없으면:
   - 코드 리뷰 수행 (버그, 컨벤션, 성능)
   - 개선 사항 제안
   - 사용자 확인 후 자동 수정

5. `.board/issues/{ticket}/worklog.jsonl` 에 리뷰/수정 내역 기록.

## 산출물

- 코드 수정 (수정 요청 시)
- 리뷰 리포트 (리뷰 모드 시)
- `.board/issues/{ticket}/worklog.jsonl` — 작업 로그

## 주의사항

- worktree에서 실행해야 diff를 정확히 볼 수 있음
- 수정 요청 없이 실행하면 리뷰 모드 (코드 수정 안 함, 제안만)
- 수정 후 기존 테스트가 깨지지 않는지 확인
