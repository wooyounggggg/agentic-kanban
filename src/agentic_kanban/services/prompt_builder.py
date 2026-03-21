"""Prompt builder — centralised prompt construction for agent tasks."""

from __future__ import annotations


def build_plan_prompt(issue_dir: str, spec: str, context: str = "", tc: str = "") -> str:
    prompt = f"아래 요구사항을 기반으로 {issue_dir}/plan.md에 구현 계획을 작성하세요.\n{spec}"
    if context:
        prompt += f"\n\n참고 지식:\n{context}"
    if tc:
        prompt += f"\n\n테스트 케이스도 함께 작성하세요.\n{tc}"
    return prompt


def build_implement_prompt(issue_dir: str) -> str:
    return (
        f"{issue_dir}/plan.md를 기반으로 구현을 시작하세요.\n"
        f"작업 완료 후 {issue_dir}/worklog.jsonl에 기록하세요."
    )


def build_review_prompt(issue_dir: str, review: str) -> str:
    return (
        f"아래 수정 요청을 반영하세요.\n{review}\n"
        f"작업 완료 후 {issue_dir}/worklog.jsonl에 기록하세요."
    )
