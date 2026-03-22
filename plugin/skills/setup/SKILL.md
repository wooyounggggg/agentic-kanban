---
name: setup
description: Dooray 티켓을 칸반 이슈로 등록하고 worktree를 생성합니다.
user-invocable: true
argument-hint: <ticket-number>
---

# agentic-kanban:setup

Dooray 티켓 번호를 받아서 .kanban/issues/{ticket}/ 에 이슈를 생성하고, Git worktree를 자동으로 만듭니다.

## 입력

```
/agentic-kanban:setup <ticket-number>
```

사용자 입력: $ARGUMENTS

## 처리 절차

1. `.kanban/` 디렉토리 존재 확인. 없으면 "agentic-kanban init을 먼저 실행하세요" 안내.

2. `.kanban/config.yaml` 읽기 — tracker 설정 확인.

3. Dooray CLI로 티켓 정보 조회:
   ```bash
   node tools/dooray-cli.js get-post-detail --post {ticket}
   ```

4. `.kanban/issues/{ticket}/issue.yaml` 생성:
   - ticket, title, status: "plan", priority: 99
   - worktree path, branch name 설정
   - tracker info (remote_status, post_id)

5. Git worktree 생성:
   ```bash
   git worktree add -b feature-{ticket} {worktree_path} {base_branch}
   ```

6. 결과 출력:
   ```
   ✅ #{ticket} 이슈 등록 완료
   제목: {title}
   상태: Plan 📝
   Worktree: {worktree_path}
   ```

## 주의사항

- 이미 등록된 티켓이면 "이미 등록된 이슈입니다" 안내
- worktree 생성 실패 시 이슈는 생성하되 경고 표시
- `.kanban/config.yaml`의 `branch_prefix`, `base_branch`, `worktree_base` 설정을 따름
