"""PipelineService — manages per-issue pipeline step progression."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from wt_board.models.config import BoardConfig, PipelineStep
from wt_board.store.board_store import BoardStore
from wt_board.services.agent_service import AgentService


class PipelineService:
    def __init__(
        self,
        store: BoardStore,
        config: BoardConfig,
        agent_service: AgentService,
    ) -> None:
        self._store = store
        self._config = config
        self._agent = agent_service

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _steps(self) -> List[PipelineStep]:
        return self._config.pipeline

    def _step_by_name(self, name: str) -> Optional[PipelineStep]:
        for s in self._steps():
            if s.name == name:
                return s
        return None

    def _step_index(self, name: str) -> int:
        for idx, s in enumerate(self._steps()):
            if s.name == name:
                return idx
        return 0

    def _artifact_path(self, ticket: str, artifact: str) -> Path:
        return self._store.issue_dir(ticket) / artifact

    def _artifact_exists(self, ticket: str, step: PipelineStep) -> bool:
        if not step.artifact:
            return True  # no artifact required
        return self._artifact_path(ticket, step.artifact).exists()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current_step(self, ticket: str) -> PipelineStep:
        """Get current pipeline step for this issue."""
        try:
            issue = self._store.read_issue(ticket)
            step_name = issue.pipeline_step or "plan"
        except FileNotFoundError:
            step_name = "plan"
        step = self._step_by_name(step_name)
        if step is None and self._steps():
            step = self._steps()[0]
        return step or PipelineStep(name="plan", label="Plan")

    def can_advance(self, ticket: str) -> Tuple[bool, str]:
        """Check if we can advance from the current step.

        Returns (ok, reason).
        For plan->implement: plan.md must exist.
        """
        steps = self._steps()
        if not steps:
            return False, "파이프라인 단계가 없습니다"

        current = self.current_step(ticket)
        current_idx = self._step_index(current.name)

        if current_idx >= len(steps) - 1:
            return False, "이미 마지막 단계입니다"

        # Gate check: artifact must exist for current step
        if not self._artifact_exists(ticket, current):
            return False, (
                f"'{current.artifact}' 파일이 없습니다. "
                f"에이전트가 {current.label} 단계를 완료한 후 다시 시도하세요."
            )

        return True, ""

    def advance(self, ticket: str) -> Tuple[bool, str]:
        """Advance to next step (no agent command — caller handles prompting).

        Returns (success, reason).
        """
        ok, reason = self.can_advance(ticket)
        if not ok:
            return False, reason

        steps = self._steps()
        current = self.current_step(ticket)
        current_idx = self._step_index(current.name)
        next_step = steps[current_idx + 1]

        try:
            issue = self._store.read_issue(ticket)
            issue.pipeline_step = next_step.name
            issue.touch_updated()
            self._store.write_issue(ticket, issue)
        except Exception as exc:
            return False, f"이슈 저장 실패: {exc}"

        return True, f"{next_step.label} 단계로 이동했습니다"

    def step_statuses(self, ticket: str) -> List[Tuple[PipelineStep, str]]:
        """Return all steps with status: done / active / pending.

        Based on issue.pipeline_step (kanban position), NOT artifact existence.
        """
        steps = self._steps()
        if not steps:
            return []

        current = self.current_step(ticket)
        current_idx = self._step_index(current.name)

        result: List[Tuple[PipelineStep, str]] = []
        for idx, step in enumerate(steps):
            if idx < current_idx:
                status = "done"
            elif idx == current_idx:
                status = "active"
            else:
                status = "pending"
            result.append((step, status))
        return result
