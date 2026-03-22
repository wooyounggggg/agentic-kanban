"""Prompt builder — reads skill definitions for SSOT."""

from __future__ import annotations
from pathlib import Path
from typing import Optional

# Skill directory relative to project root
_SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "plugin" / "skills"


def _read_skill_description(skill_name: str) -> str:
    """Read the SKILL.md content for a given skill."""
    skill_path = _SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        content = skill_path.read_text(encoding="utf-8")
        # Strip frontmatter (between ---)
        parts = content.split("---")
        if len(parts) >= 3:
            return "---".join(parts[2:]).strip()
        return content
    return ""


def build_plan_prompt(issue_dir: str, spec: str, context: str = "", tc: str = "") -> str:
    skill_desc = _read_skill_description("plan")
    prompt = f"{issue_dir}/plan.md에 구현 계획을 작성하세요.\n\n{spec}"
    if context:
        prompt += f"\n\n참고 지식:\n{context}"
    if tc:
        prompt += f"\n\n테스트 케이스도 함께 작성하세요.\n{tc}"
    if skill_desc:
        prompt += f"\n\n--- 스킬 가이드 ---\n{skill_desc}"
    return prompt


def build_implement_prompt(issue_dir: str) -> str:
    skill_desc = _read_skill_description("implement")
    prompt = f"{issue_dir}/plan.md를 기반으로 구현을 시작하세요.\n작업 완료 후 {issue_dir}/worklog.jsonl에 기록하세요."
    if skill_desc:
        prompt += f"\n\n--- 스킬 가이드 ---\n{skill_desc}"
    return prompt


def build_review_prompt(issue_dir: str, review: str) -> str:
    skill_desc = _read_skill_description("review")
    prompt = f"아래 수정 요청을 반영하세요.\n{review}\n작업 완료 후 {issue_dir}/worklog.jsonl에 기록하세요."
    if skill_desc:
        prompt += f"\n\n--- 스킬 가이드 ---\n{skill_desc}"
    return prompt
