"""Flet GUI for Addlib Media Manager - Material design."""

import asyncio
import queue
import threading
import uuid
from datetime import datetime

import flet as ft

from addlib_config import load_rules, save_rules, validate_rule
from addlib_core import move_and_rename

_TYPE_LABEL = {"movie": "Movie", "tv_series": "TV Series"}
LOG_POLL_INTERVAL_SEC = 0.2
RULE_DIALOG_WIDTH = 560

def _tag(text: str) -> ft.Container:
    """Unified tag style for Movie, TV Series, A–Z."""
    return ft.Container(
        content=ft.Text(
            text,
            size=11,
            weight=ft.FontWeight.W_500,
            color=ft.Colors.ON_SURFACE_VARIANT,
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border_radius=12,
    )


def main(page: ft.Page):
    page.title = "Addlib Media Manager"
    page.window.min_width = 900
    page.window.min_height = 600
    page.window.width = 1100
    page.window.height = 720
    page.padding = 0

    log_queue: queue.Queue = queue.Queue()
    state = {"running": False, "dialog_open": False}

    rules_list_ref = ft.Ref[ft.ListView]()
    log_list_ref = ft.Ref[ft.ListView]()
    progress_bar_ref = ft.Ref[ft.ProgressBar]()
    run_all_btn_ref = ft.Ref[ft.FilledButton]()
    rules_count_ref = ft.Ref[ft.Text]()
    rules_panel_container_ref = ft.Ref[ft.Container]()
    toggle_panel_btn_ref = ft.Ref[ft.IconButton]()

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _ts() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def show_snack(msg: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(msg), open=True)
        page.update()

    # ── Log poller ───────────────────────────────────────────────────────────

    def _log_color(msg: str) -> str | None:
        """Return text color for a log message."""
        ml = msg.lower()
        if msg.startswith("---"):
            return ft.Colors.PRIMARY
        if "error" in ml or "failed" in ml:
            return ft.Colors.ERROR
        if "deleted" in ml:
            return ft.Colors.TERTIARY
        if "moved" in ml:
            return ft.Colors.SECONDARY
        if "created" in ml:
            return ft.Colors.GREEN_400
        return None

    def drain_log():
        try:
            while True:
                msg = log_queue.get_nowait()
                lv = log_list_ref.current
                if lv is not None:
                    text_color = _log_color(msg)
                    lv.controls.append(
                        ft.Row(
                            [
                                ft.Text(
                                    f"[{_ts()}]",
                                    size=11,
                                    color=ft.Colors.OUTLINE,
                                    font_family="monospace",
                                    no_wrap=True,
                                ),
                                ft.Text(
                                    msg,
                                    size=12,
                                    color=text_color,
                                    font_family="monospace",
                                    selectable=True,
                                    expand=True,
                                ),
                            ],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        )
                    )
        except queue.Empty:
            pass

        is_running = state["running"]
        if progress_bar_ref.current:
            progress_bar_ref.current.visible = is_running
        if run_all_btn_ref.current:
            run_all_btn_ref.current.disabled = is_running
        page.update()

    async def log_poller():
        while True:
            drain_log()
            await asyncio.sleep(LOG_POLL_INTERVAL_SEC)

    page.run_task(log_poller)

    # ── Rule execution ───────────────────────────────────────────────────────

    def execute_rules(rules: list):
        def worker():
            state["running"] = True
            try:
                for rule in rules:
                    name = rule.get("name", "?")
                    log_queue.put(f"--- Running: {name} ---")

                    def _logger(m):
                        log_queue.put(m)

                    move_and_rename(
                        rule["source"],
                        rule["target"],
                        rule["type"],
                        rule.get("organize_by_initial", False),
                        logger=_logger,
                    )
                    log_queue.put(f"--- Finished: {name} ---")
            except Exception as exc:
                log_queue.put(f"Error: {exc}")
            finally:
                state["running"] = False

        threading.Thread(target=worker, daemon=True).start()

    # ── Rule card ────────────────────────────────────────────────────────────

    def build_rule_card(rule: dict) -> ft.Card:
        name = rule.get("name", "")
        source = rule.get("source", "")
        target = rule.get("target", "")
        typ = rule.get("type", "movie")
        org = rule.get("organize_by_initial", False)

        type_label = _TYPE_LABEL.get(typ, typ)

        def on_run(e):
            if state["running"]:
                show_snack("A run is already in progress.")
                return
            execute_rules([rule])

        def on_edit(e):
            open_rule_dialog(rule)

        def on_delete(e):
            open_delete_dialog(rule)

        return ft.Card(
            elevation=1,
            content=ft.Container(
                content=ft.Column(
                    [
                        # Header: name + type badge + A-Z badge
                        ft.Row(
                            [
                                ft.Text(
                                    name,
                                    weight=ft.FontWeight.W_600,
                                    size=14,
                                    expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Row(
                                    (
                                        [_tag(type_label)]
                                        + ([_tag("A–Z")] if org else [])
                                    ),
                                    spacing=6,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        # Source path
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.FOLDER,
                                    size=14,
                                    color=ft.Colors.OUTLINE,
                                ),
                                ft.Text(
                                    source or "—",
                                    size=12,
                                    color=ft.Colors.OUTLINE,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                            ],
                            spacing=6,
                        ),
                        # Target path
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.ARROW_RIGHT_ALT,
                                    size=14,
                                    color=ft.Colors.OUTLINE,
                                ),
                                ft.Text(
                                    target or "—",
                                    size=12,
                                    color=ft.Colors.OUTLINE,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                            ],
                            spacing=6,
                        ),
                        ft.Divider(height=1),
                        # Footer: action buttons
                        ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.IconButton(
                                            icon=ft.Icons.EDIT,
                                            tooltip="Edit",
                                            on_click=on_edit,
                                            icon_size=20,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.DELETE,
                                            tooltip="Delete rule",
                                            on_click=on_delete,
                                            icon_color=ft.Colors.ERROR,
                                            icon_size=20,
                                        ),
                                    ],
                                    spacing=4,
                                ),
                                ft.FilledButton(
                                    "Run",
                                    icon=ft.Icons.PLAY_ARROW,
                                    on_click=on_run,
                                    tooltip="Run this rule",
                                ),
                            ],
                            spacing=4,
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=10,
                    tight=True,
                ),
                padding=ft.Padding.all(16),
            ),
        )

    # ── Rules list ───────────────────────────────────────────────────────────

    def refresh_rules():
        lv = rules_list_ref.current
        if lv is None:
            return
        rules = load_rules()
        lv.controls.clear()
        count = len(rules)
        if rules_count_ref.current:
            rules_count_ref.current.value = (
                f"{count} rule{'s' if count != 1 else ''}"
            )
        if not rules:
            lv.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.FOLDER_SPECIAL,
                                size=52,
                                color=ft.Colors.OUTLINE,
                            ),
                            ft.Text(
                                "No rules yet",
                                size=15,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Text(
                                'Click "Add Rule" to get started',
                                size=12,
                                color=ft.Colors.OUTLINE,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                    ),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=40,
                )
            )
        else:
            for r in rules:
                lv.controls.append(build_rule_card(r))
        page.update()

    # ── Delete dialog ────────────────────────────────────────────────────────

    def open_delete_dialog(rule: dict):
        if state["dialog_open"]:
            return

        def on_confirm(e):
            updated = [
                r for r in load_rules() if r.get("id") != rule.get("id")
            ]
            try:
                save_rules(updated)
            except OSError as exc:
                show_snack(f"Could not save: {exc}")
                return
            state["dialog_open"] = False
            page.pop_dialog()
            refresh_rules()
            log_queue.put(f"Deleted rule: {rule.get('name', '')}")
            show_snack("Rule deleted.")

        def on_cancel(e):
            state["dialog_open"] = False
            page.pop_dialog()

        state["dialog_open"] = True
        dlg = ft.AlertDialog(
            title=ft.Text("Delete Rule"),
            content=ft.Text(
                f'Delete "{rule.get("name", "")}"? This cannot be undone.'
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.FilledButton("Delete", on_click=on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    # ── Add / Edit dialog ────────────────────────────────────────────────────

    def open_rule_dialog(rule=None):
        if state["dialog_open"]:
            return
        state["dialog_open"] = True
        is_edit = rule is not None

        name_field = ft.TextField(
            label="Rule name",
            value=(rule or {}).get("name", ""),
            hint_text='e.g. "Movies → NAS"',
            autofocus=True,
        )
        source_field = ft.TextField(
            label="Source folder",
            value=(rule or {}).get("source", ""),
            hint_text="/path/to/downloads",
            expand=True,
            prefix_icon=ft.Icons.FOLDER,
        )
        target_field = ft.TextField(
            label="Target folder",
            value=(rule or {}).get("target", ""),
            hint_text="/path/to/library",
            expand=True,
            prefix_icon=ft.Icons.ARROW_RIGHT_ALT,
        )
        type_dropdown = ft.Dropdown(
            label="Content type",
            value=(rule or {}).get("type", "movie"),
            options=[
                ft.dropdown.Option(key="movie", text="Movie"),
                ft.dropdown.Option(key="tv_series", text="TV Series"),
            ],
        )
        org_switch = ft.Switch(
            label="Group files by initial character (A–Z, 0–9)",
            value=bool((rule or {}).get("organize_by_initial", False)),
        )

        async def pick_source(e):
            path = await file_picker.get_directory_path(
                dialog_title="Select source folder"
            )
            if path:
                source_field.value = path
                page.update()

        async def pick_target(e):
            path = await file_picker.get_directory_path(
                dialog_title="Select target folder"
            )
            if path:
                target_field.value = path
                page.update()

        def on_save(e):
            r = (rule or {}).copy()
            r["name"] = (name_field.value or "").strip()
            r["source"] = (source_field.value or "").strip()
            r["target"] = (target_field.value or "").strip()
            r["type"] = (type_dropdown.value or "movie").strip().lower()
            r["organize_by_initial"] = bool(org_switch.value)
            if "id" not in r:
                r["id"] = str(uuid.uuid4())

            ok, err = validate_rule(r)
            if not ok:
                show_snack(f"Validation: {err}")
                return

            rules_list = load_rules()
            name_lower = (r.get("name") or "").strip().lower()
            for rr in rules_list:
                if rr.get("id") == r.get("id"):
                    continue
                if (rr.get("name") or "").strip().lower() == name_lower:
                    show_snack("A rule with this name already exists.")
                    return
            if is_edit:
                for i, rr in enumerate(rules_list):
                    if rr.get("id") == rule.get("id"):
                        rules_list[i] = r
                        break
            else:
                rules_list.append(r)

            try:
                save_rules(rules_list)
            except OSError as exc:
                show_snack(f"Could not save: {exc}")
                return
            state["dialog_open"] = False
            page.pop_dialog()
            refresh_rules()
            action = "Updated" if is_edit else "Added"
            log_queue.put(f"{action} rule: {r.get('name', '')}")
            show_snack(f"Rule {action.lower()}.")

        def on_cancel(e):
            state["dialog_open"] = False
            page.pop_dialog()

        form = ft.Column(
            [
                ft.Text(
                    "Set a name and choose source/target folders.",
                    size=12,
                    color=ft.Colors.OUTLINE,
                ),
                name_field,
                ft.Container(height=4),
                ft.Text("Folders", size=12, weight=ft.FontWeight.W_600),
                ft.Row(
                    [
                        source_field,
                        ft.OutlinedButton(
                            "Browse",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=pick_source,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    [
                        target_field,
                        ft.OutlinedButton(
                            "Browse",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=pick_target,
                        ),
                    ],
                    spacing=8,
                ),
                ft.Container(height=4),
                ft.Text("Options", size=12, weight=ft.FontWeight.W_600),
                ft.Row(
                    [type_dropdown],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Container(
                    content=org_switch,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=10,
                ),
            ],
            spacing=12,
            tight=True,
        )

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.TUNE, size=20),
                    ft.Text(
                        "Edit Rule" if is_edit else "Add Rule",
                        size=20,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Container(content=form, width=RULE_DIALOG_WIDTH),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.FilledButton(
                    "Save",
                    icon=ft.Icons.SAVE,
                    on_click=on_save,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    # ── Toolbar actions ──────────────────────────────────────────────────────

    def on_run_all(e):
        rules = load_rules()
        if not rules:
            show_snack("No rules to run.")
            return
        if state["running"]:
            show_snack("A run is already in progress.")
            return
        execute_rules(rules)

    def on_clear_log(e):
        lv = log_list_ref.current
        if lv is not None:
            lv.controls.clear()
            page.update()

    def on_toggle_panel(e):
        c = rules_panel_container_ref.current
        btn = toggle_panel_btn_ref.current
        if c is None:
            return
        c.visible = not c.visible
        if btn:
            btn.icon = (
                ft.Icons.MENU_OPEN if c.visible else ft.Icons.MENU
            )
            btn.tooltip = (
                "Hide rules panel" if c.visible else "Show rules panel"
            )
        page.update()

    # ── AppBar ───────────────────────────────────────────────────────────────

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.VIDEO_LIBRARY),
        leading_width=48,
        title=ft.Text("Addlib", weight=ft.FontWeight.W_700),
        center_title=False,
        actions=[
            ft.IconButton(
                icon=ft.Icons.MENU_OPEN,
                tooltip="Hide rules panel",
                on_click=on_toggle_panel,
                ref=toggle_panel_btn_ref,
            ),
            ft.Container(width=8),
            ft.FilledButton(
                "Run All",
                icon=ft.Icons.PLAY_ARROW,
                on_click=on_run_all,
                ref=run_all_btn_ref,
                tooltip="Run all rules",
            ),
            ft.Container(width=16),
        ],
    )

    # ── Progress bar (shown while running) ───────────────────────────────────

    progress_bar_widget = ft.ProgressBar(
        ref=progress_bar_ref,
        visible=False,
        height=3,
        color=ft.Colors.PRIMARY,
        bgcolor=ft.Colors.PRIMARY_CONTAINER,
    )

    # ── Rules panel ──────────────────────────────────────────────────────────

    rules_lv = ft.ListView(
        ref=rules_list_ref,
        expand=True,
        spacing=10,
        padding=ft.Padding.all(12),
    )

    rules_panel = ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.FOLDER_SPECIAL, size=18),
                                ft.Text(
                                    "Rules",
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        "0 rules",
                                        size=11,
                                        ref=rules_count_ref,
                                    ),
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                    padding=ft.Padding.symmetric(
                                        horizontal=8, vertical=3
                                    ),
                                    border_radius=10,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.FilledButton(
                            "Add Rule",
                            icon=ft.Icons.ADD,
                            on_click=lambda e: open_rule_dialog(None),
                            tooltip="Add a new rule",
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                border=ft.Border.only(
                    bottom=ft.BorderSide(1, ft.Colors.OUTLINE)
                ),
            ),
            ft.Container(content=rules_lv, expand=True),
        ],
        expand=True,
        spacing=0,
    )

    # ── Log panel ────────────────────────────────────────────────────────────

    log_lv = ft.ListView(
        ref=log_list_ref,
        expand=True,
        spacing=2,
        padding=ft.Padding.all(12),
        auto_scroll=True,
    )

    log_panel = ft.Column(
        [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.RECEIPT_LONG, size=18),
                                ft.Text(
                                    "Activity Log",
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.TextButton(
                            "Clear",
                            icon=ft.Icons.CLEAR_ALL,
                            on_click=on_clear_log,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                border=ft.Border.only(
                    bottom=ft.BorderSide(1, ft.Colors.OUTLINE)
                ),
            ),
            ft.Container(
                content=log_lv,
                expand=True,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            ),
        ],
        expand=True,
        spacing=0,
    )

    # ── Main layout ──────────────────────────────────────────────────────────

    page.add(
        ft.Column(
            [
                progress_bar_widget,
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                ref=rules_panel_container_ref,
                                content=rules_panel,
                                expand=2,
                                border=ft.Border.all(1, ft.Colors.OUTLINE),
                                border_radius=12,
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            ),
                            ft.Container(
                                content=log_panel,
                                expand=3,
                                border=ft.Border.all(1, ft.Colors.OUTLINE),
                                border_radius=12,
                                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                            ),
                        ],
                        spacing=16,
                        expand=True,
                    ),
                    expand=True,
                    padding=ft.Padding.all(16),
                ),
            ],
            expand=True,
            spacing=0,
        )
    )

    refresh_rules()


if __name__ == "__main__":
    ft.run(main)
