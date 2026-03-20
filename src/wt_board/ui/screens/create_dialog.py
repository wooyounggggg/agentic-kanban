"""Dialogs — 이슈 생성, 프로젝트 추가/전환, 온보딩, 상태 이동."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, OptionList, Static

from wt_board.models.config import StatusDef
from wt_board.ui.themes import THEME_NAMES


_DIALOG_CSS = """
    background: #161b22;
    border: double #58a6ff;
    padding: 1 2;
    height: auto;
"""


# ---------------------------------------------------------------------------
# 이슈 생성 다이얼로그 (조회 → 미리보기 → 생성)
# ---------------------------------------------------------------------------

class CreateDialog(ModalScreen):
    """티켓번호 입력 → Dooray 조회 → 미리보기 → 생성 플로우."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
    ]

    DEFAULT_CSS = f"""
    CreateDialog {{
        align: center middle;
    }}
    CreateDialog > Vertical {{
        {_DIALOG_CSS}
        width: 72;
        max-height: 28;
    }}
    CreateDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    CreateDialog .dialog-label {{
        color: #8b949e;
        margin-top: 1;
    }}
    CreateDialog .preview-box {{
        background: #0d1117;
        border: round #30363d;
        padding: 1;
        margin-top: 1;
        height: auto;
        max-height: 12;
        overflow-y: auto;
    }}
    CreateDialog .preview-title {{
        color: #58a6ff;
        text-style: bold;
    }}
    CreateDialog .preview-field {{
        color: #c9d1d9;
    }}
    CreateDialog .preview-desc {{
        color: #8b949e;
    }}
    CreateDialog .btn-row {{
        margin-top: 1;
        height: 3;
    }}
    CreateDialog #btn-create {{
        display: none;
    }}
    CreateDialog #btn-create.visible {{
        display: block;
    }}
    """

    def __init__(self, tracker=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._tracker = tracker  # Optional[TrackerPlugin]
        self._fetched_title = ""
        self._fetched_desc = ""
        self._fetched_assignee = ""
        self._fetched_status = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("새 이슈 추가", classes="dialog-title")
            yield Static("Dooray 티켓 번호:", classes="dialog-label")
            with Horizontal():
                yield Input(placeholder="예: 3399", id="input-ticket")
                yield Button("조회", variant="primary", id="btn-lookup")
            yield Static("", id="preview-area", classes="preview-box")
            with Horizontal(classes="btn-row"):
                yield Button("생성", variant="success", id="btn-create")
                yield Button("취소", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#input-ticket", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-lookup":
            self._do_lookup()
        elif event.button.id == "btn-create":
            self._do_create()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-ticket":
            self._do_lookup()

    def _do_lookup(self) -> None:
        ticket = self.query_one("#input-ticket", Input).value.strip()
        if not ticket:
            self.notify("티켓 번호를 입력해주세요.", severity="error")
            return

        preview = self.query_one("#preview-area", Static)
        btn_create = self.query_one("#btn-create", Button)

        if self._tracker is None:
            # No tracker — allow manual creation
            preview.update(
                f"[dim]트래커 미연결 — 수동으로 생성합니다.[/]\n"
                f"[bold cyan]#{ticket}[/]"
            )
            self._fetched_title = ""
            btn_create.add_class("visible")
            btn_create.focus()
            return

        # Fetch from Dooray
        preview.update("[dim]조회 중...[/]")
        try:
            result = self._tracker.get_issue(ticket)
        except Exception as e:
            preview.update(f"[red]조회 실패:[/] {e}")
            return

        if result is None:
            preview.update(f"[red]#{ticket} — 이슈를 찾을 수 없습니다.[/]")
            return

        self._fetched_title = result.title
        self._fetched_desc = result.description
        self._fetched_assignee = result.assignee
        self._fetched_status = result.status

        desc_preview = result.description[:200] + "..." if len(result.description) > 200 else result.description
        desc_preview = desc_preview.replace("\n", " ") if desc_preview else "(본문 없음)"

        preview.update(
            f"[bold cyan]#{ticket}[/]  {result.title}\n"
            f"[dim]상태:[/] {result.status}    "
            f"[dim]담당:[/] {result.assignee or '미지정'}\n"
            f"[dim]내용:[/] {desc_preview}"
        )
        btn_create.add_class("visible")
        btn_create.focus()

    def _do_create(self) -> None:
        ticket = self.query_one("#input-ticket", Input).value.strip()
        if not ticket:
            self.notify("티켓 번호를 입력해주세요.", severity="error")
            return
        self.dismiss({
            "ticket": ticket,
            "title": self._fetched_title,
            "description": self._fetched_desc,
            "assignee": self._fetched_assignee,
        })

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# 온보딩 다이얼로그 (최초 실행 시 Dooray API key)
# ---------------------------------------------------------------------------

class OnboardingDialog(ModalScreen):
    """최초 실행 시 Dooray API key를 입력받는 온보딩 화면."""

    BINDINGS = [
        Binding("escape", "cancel", "건너뛰기"),
    ]

    DEFAULT_CSS = f"""
    OnboardingDialog {{
        align: center middle;
    }}
    OnboardingDialog > Vertical {{
        {_DIALOG_CSS}
        width: 65;
    }}
    OnboardingDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    OnboardingDialog .dialog-label {{
        color: #8b949e;
        margin-top: 1;
    }}
    OnboardingDialog .dialog-hint {{
        color: #6e7681;
        margin-top: 1;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("wt-board 초기 설정", classes="dialog-title")
            yield Static(
                "Dooray 연동을 위해 API key가 필요합니다.\n"
                "Dooray > 설정 > API 키에서 발급할 수 있습니다.",
                classes="dialog-label",
            )
            yield Input(placeholder="Dooray API key", password=True, id="input-api-key")
            yield Static(
                "[dim]건너뛰려면 Esc를 누르세요. 나중에 config.yaml에서 설정할 수 있습니다.[/]",
                classes="dialog-hint",
            )
            with Horizontal():
                yield Button("저장", variant="primary", id="btn-save")
                yield Button("건너뛰기", variant="default", id="btn-skip")

    def on_mount(self) -> None:
        self.query_one("#input-api-key", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-skip":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            self._do_save()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_save()

    def _do_save(self) -> None:
        api_key = self.query_one("#input-api-key", Input).value.strip()
        if not api_key:
            self.notify("API key를 입력해주세요.", severity="error")
            return
        self.dismiss(api_key)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# 프로젝트 추가 다이얼로그 (확장)
# ---------------------------------------------------------------------------

class AddProjectDialog(ModalScreen):
    """프로젝트 등록 — 이름, Dooray project ID, 메인 디렉토리, worktree 경로."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
    ]

    DEFAULT_CSS = f"""
    AddProjectDialog {{
        align: center middle;
    }}
    AddProjectDialog > Vertical {{
        {_DIALOG_CSS}
        width: 65;
    }}
    AddProjectDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    AddProjectDialog .dialog-label {{
        color: #8b949e;
        margin-top: 1;
    }}
    AddProjectDialog .dialog-hint {{
        color: #6e7681;
    }}
    """

    def compose(self) -> ComposeResult:
        cwd = str(Path.cwd())
        with Vertical():
            yield Static("프로젝트 추가", classes="dialog-title")

            yield Static("프로젝트 이름:", classes="dialog-label")
            yield Input(placeholder="nc-dms", id="input-name")

            yield Static("프로젝트 루트 경로:", classes="dialog-label")
            yield Input(placeholder=cwd, value=cwd, id="input-path")

            yield Static("Worktree 디렉토리 (프로젝트 루트 기준 상대 경로):", classes="dialog-label")
            yield Input(placeholder="worktrees", value="worktrees", id="input-wt-base")

            yield Static("Dooray Project ID:", classes="dialog-label")
            yield Input(placeholder="예: 3939952010186161882", id="input-dooray-pid")
            yield Static("[dim]Dooray 프로젝트 URL에서 확인 가능[/]", classes="dialog-hint")

            with Horizontal():
                yield Button("추가", variant="primary", id="btn-add")
                yield Button("취소", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#input-name", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-add":
            self._do_submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_submit()

    def _do_submit(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        path = self.query_one("#input-path", Input).value.strip()
        wt_base = self.query_one("#input-wt-base", Input).value.strip()
        dooray_pid = self.query_one("#input-dooray-pid", Input).value.strip()

        if not name:
            self.notify("프로젝트 이름을 입력해주세요.", severity="error")
            return
        if not path:
            self.notify("프로젝트 경로를 입력해주세요.", severity="error")
            return

        self.dismiss({
            "name": name,
            "path": path,
            "worktree_base": wt_base or "worktrees",
            "dooray_project_id": dooray_pid,
        })

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# 프로젝트 전환 다이얼로그
# ---------------------------------------------------------------------------

class SwitchProjectDialog(ModalScreen):
    """프로젝트 전환 다이얼로그."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
        Binding("enter", "select", "선택", show=False),
    ]

    DEFAULT_CSS = f"""
    SwitchProjectDialog {{
        align: center middle;
    }}
    SwitchProjectDialog > Vertical {{
        {_DIALOG_CSS}
        width: 50;
        max-height: 20;
    }}
    SwitchProjectDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    """

    def __init__(self, names: List[str], current: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._names = names
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("프로젝트 전환", classes="dialog-title")
            options = OptionList(id="project-list")
            for name in self._names:
                marker = " [green]\u25c0[/]" if name == self._current else ""
                options.add_option(f"{name}{marker}")
            yield options
            yield Button("취소", variant="default", id="btn-cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        opt_list = self.query_one("#project-list", OptionList)
        idx = opt_list.highlighted
        if idx is not None and 0 <= idx < len(self._names):
            self.dismiss(self._names[idx])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if 0 <= idx < len(self._names):
            self.dismiss(self._names[idx])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)


# ---------------------------------------------------------------------------
# 상태 이동 다이얼로그
# ---------------------------------------------------------------------------

class MoveDialog(ModalScreen):
    """이슈 상태 이동 다이얼로그 — 현재 상태 표시 후 이동 가능한 상태 목록 제공."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
        Binding("enter", "select", "선택", show=False),
    ]

    DEFAULT_CSS = f"""
    MoveDialog {{
        align: center middle;
    }}
    MoveDialog > Vertical {{
        {_DIALOG_CSS}
        width: 50;
        max-height: 22;
    }}
    MoveDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    MoveDialog .current-status {{
        color: #8b949e;
        margin-bottom: 1;
    }}
    """

    def __init__(
        self,
        ticket: str,
        current_status: str,
        target_statuses: List[StatusDef],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._ticket = ticket
        self._current_status = current_status
        self._targets = target_statuses

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(f"이슈 이동 — #{self._ticket}", classes="dialog-title")
            yield Static(
                f"현재 상태: [bold]{self._current_status}[/]",
                classes="current-status",
            )
            opt = OptionList()
            for s in self._targets:
                opt.add_option(f"{s.icon} {s.label}  [dim]({s.name})[/]")
            yield opt
            yield Button("취소", variant="default", id="move-btn-cancel")

    def on_mount(self) -> None:
        opt = self.query_one(OptionList)
        opt.focus()
        if opt.option_count > 0:
            opt.highlighted = 0

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        opt = self.query_one(OptionList)
        idx = opt.highlighted
        if idx is not None and 0 <= idx < len(self._targets):
            self.dismiss(self._targets[idx].name)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if 0 <= idx < len(self._targets):
            self.dismiss(self._targets[idx].name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "move-btn-cancel":
            self.dismiss(None)


# ---------------------------------------------------------------------------
# 테마 선택 다이얼로그
# ---------------------------------------------------------------------------

class ThemeDialog(ModalScreen):
    """테마 선택 다이얼로그 — 4종 테마 중 선택."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
        Binding("enter", "select", "선택", show=False),
    ]

    DEFAULT_CSS = f"""
    ThemeDialog {{
        align: center middle;
    }}
    ThemeDialog > Vertical {{
        {_DIALOG_CSS}
        width: 44;
        max-height: 16;
    }}
    ThemeDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    """

    THEME_NAMES = THEME_NAMES
    THEME_LABELS = {
        "brown": "Brown (default warm earth tones)",
        "catppuccin": "Catppuccin (soft pastel)",
        "nord": "Nord (arctic blue)",
        "github-dark": "GitHub Dark",
    }

    def __init__(self, current_theme: str = "brown", **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_theme = current_theme

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("테마 선택", classes="dialog-title")
            opt = OptionList(id="theme-list")
            for name in self.THEME_NAMES:
                label = self.THEME_LABELS.get(name, name)
                marker = " [green]◀[/]" if name == self._current_theme else ""
                opt.add_option(f"{label}{marker}")
            yield opt
            yield Button("취소", variant="default", id="theme-btn-cancel")

    def on_mount(self) -> None:
        opt = self.query_one("#theme-list", OptionList)
        opt.focus()
        # Highlight current theme
        try:
            idx = self.THEME_NAMES.index(self._current_theme)
            opt.highlighted = idx
        except (ValueError, Exception):
            pass

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        opt = self.query_one("#theme-list", OptionList)
        idx = opt.highlighted
        if idx is not None and 0 <= idx < len(self.THEME_NAMES):
            self.dismiss(self.THEME_NAMES[idx])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if 0 <= idx < len(self.THEME_NAMES):
            self.dismiss(self.THEME_NAMES[idx])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "theme-btn-cancel":
            self.dismiss(None)


# ---------------------------------------------------------------------------
# Plan 프롬프트 다이얼로그
# ---------------------------------------------------------------------------

class PlanPromptDialog(ModalScreen):
    """Plan 단계 — Spec 프롬프트(필수)와 TC 프롬프트(선택) 입력."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
    ]

    DEFAULT_CSS = f"""
    PlanPromptDialog {{
        align: center middle;
    }}
    PlanPromptDialog > Vertical {{
        {_DIALOG_CSS}
        width: 72;
        height: auto;
    }}
    PlanPromptDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    PlanPromptDialog .dialog-label {{
        color: #8b949e;
        margin-top: 1;
    }}
    PlanPromptDialog .dialog-hint {{
        color: #6e7681;
    }}
    PlanPromptDialog .btn-row {{
        margin-top: 1;
        height: 3;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Plan 작성", classes="dialog-title")
            yield Static("Spec 프롬프트 (필수):", classes="dialog-label")
            yield Input(placeholder="구현할 기능을 설명하세요", id="input-spec")
            yield Static("TC 프롬프트 (선택):", classes="dialog-label")
            yield Input(placeholder="테스트 케이스 요구사항 (비워두면 생략)", id="input-tc")
            with Horizontal(classes="btn-row"):
                yield Button("실행", variant="primary", id="btn-submit")
                yield Button("취소", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#input-spec", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-submit":
            self._do_submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "input-spec":
            self.query_one("#input-tc", Input).focus()
        elif event.input.id == "input-tc":
            self._do_submit()

    def _do_submit(self) -> None:
        spec = self.query_one("#input-spec", Input).value.strip()
        if not spec:
            self.notify("Spec 프롬프트를 입력해주세요.", severity="error")
            return
        tc = self.query_one("#input-tc", Input).value.strip()
        self.dismiss({"spec": spec, "tc": tc})

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Implement 확인 다이얼로그
# ---------------------------------------------------------------------------

class ImplementConfirmDialog(ModalScreen):
    """Implement 단계 — Plan 기반 구현 시작 확인."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
        Binding("enter", "confirm", "확인", show=False),
    ]

    DEFAULT_CSS = f"""
    ImplementConfirmDialog {{
        align: center middle;
    }}
    ImplementConfirmDialog > Vertical {{
        {_DIALOG_CSS}
        width: 56;
        height: auto;
    }}
    ImplementConfirmDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    ImplementConfirmDialog .dialog-message {{
        color: #c9d1d9;
        margin-bottom: 1;
    }}
    ImplementConfirmDialog .btn-row {{
        margin-top: 1;
        height: 3;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("구현 시작", classes="dialog-title")
            yield Static(
                "Plan 기반으로 구현을 시작합니다. 실행할까요?",
                classes="dialog-message",
            )
            with Horizontal(classes="btn-row"):
                yield Button("예", variant="primary", id="btn-yes")
                yield Button("아니오", variant="default", id="btn-no")

    def on_mount(self) -> None:
        self.query_one("#btn-yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(None)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# Review 프롬프트 다이얼로그
# ---------------------------------------------------------------------------

class ReviewPromptDialog(ModalScreen):
    """Review 단계 — 수정 프롬프트 입력."""

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
    ]

    DEFAULT_CSS = f"""
    ReviewPromptDialog {{
        align: center middle;
    }}
    ReviewPromptDialog > Vertical {{
        {_DIALOG_CSS}
        width: 72;
        height: auto;
    }}
    ReviewPromptDialog .dialog-title {{
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }}
    ReviewPromptDialog .dialog-label {{
        color: #8b949e;
        margin-top: 1;
    }}
    ReviewPromptDialog .btn-row {{
        margin-top: 1;
        height: 3;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("수정 요청", classes="dialog-title")
            yield Static("수정 프롬프트:", classes="dialog-label")
            yield Input(placeholder="수정할 내용을 설명하세요", id="input-review")
            with Horizontal(classes="btn-row"):
                yield Button("실행", variant="primary", id="btn-submit")
                yield Button("취소", variant="default", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#input-review", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-submit":
            self._do_submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_submit()

    def _do_submit(self) -> None:
        review = self.query_one("#input-review", Input).value.strip()
        if not review:
            self.notify("수정 프롬프트를 입력해주세요.", severity="error")
            return
        self.dismiss({"review": review})

    def action_cancel(self) -> None:
        self.dismiss(None)
