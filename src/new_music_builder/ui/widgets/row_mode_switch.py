from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.domain.models import MediaRow
from new_music_builder.platform.i18n import t
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


class RowModeSwitch(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        base_image_path: str | None,
        pill_image_path: str | None,
        command: Callable[[str], None] | None = None,
        bg_color: str | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else str(parent.cget("bg"))
        super().__init__(
            parent,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_MODE_SWITCH_SIZE[0],
            height=spec.MEDIA_ROW_MODE_SWITCH_SIZE[1],
        )
        self.pack_propagate(False)
        self._row = row
        self._command = command
        self._bg_color = resolved_bg
        self._anim_after_id: str | None = None
        self._base_image = load_tk_photoimage(base_image_path, spec.MEDIA_ROW_MODE_SWITCH_TRACK_SIZE)
        self._pill_image = load_tk_photoimage(pill_image_path, spec.MEDIA_ROW_MODE_SWITCH_PILL_SIZE)
        self._track_x = (spec.MEDIA_ROW_MODE_SWITCH_SIZE[0] - spec.MEDIA_ROW_MODE_SWITCH_TRACK_SIZE[0]) // 2

        label_font = (
            spec.MEDIA_ROW_MODE_SWITCH_FONT_FAMILY,
            spec.MEDIA_ROW_MODE_SWITCH_FONT_SIZE,
        )
        self.left_label = tk.Label(
            self,
            text=t("MIXTAPE"),
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            font=label_font,
            anchor="e",
            justify="right",
        )
        self.right_label = tk.Label(
            self,
            text=t("SINGLES"),
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            font=label_font,
            anchor="w",
            justify="left",
        )
        left_width = max(1, self._track_x - spec.MEDIA_ROW_MODE_SWITCH_LABEL_GAP_X)
        right_x = self._track_x + spec.MEDIA_ROW_MODE_SWITCH_TRACK_SIZE[0] + spec.MEDIA_ROW_MODE_SWITCH_LABEL_GAP_X
        right_width = max(1, spec.MEDIA_ROW_MODE_SWITCH_SIZE[0] - right_x)
        self.left_label.place(x=0, y=spec.MEDIA_ROW_MODE_SWITCH_LABEL_Y, width=left_width)
        self.right_label.place(x=right_x, y=spec.MEDIA_ROW_MODE_SWITCH_LABEL_Y, width=right_width)

        self.track = tk.Canvas(
            self,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_MODE_SWITCH_TRACK_SIZE[0],
            height=spec.MEDIA_ROW_MODE_SWITCH_TRACK_SIZE[1],
        )
        self.track.place(x=self._track_x, y=spec.MEDIA_ROW_MODE_SWITCH_LABEL_Y)
        self.track.create_image(0, 0, image=self._base_image, anchor="nw")
        self._pill_item = self.track.create_image(0, 0, image=self._pill_image, anchor="nw")

        for widget in (self, self.left_label, self.right_label, self.track):
            widget.bind("<ButtonRelease-1>", self._on_toggle, add="+")

        self.refresh()

    def tooltip_widgets(self) -> tuple[tk.Misc, ...]:
        return (self, self.left_label, self.right_label, self.track)

    def set_bg_color(self, color: str) -> None:
        self._bg_color = color
        self.configure(bg=color)
        self.left_label.configure(bg=color)
        self.right_label.configure(bg=color)
        self.track.configure(bg=color)

    def set_row(self, row: MediaRow) -> None:
        self._row = row
        self.refresh()

    def refresh(self) -> None:
        active_mode = getattr(self._row, "row_mode", "mixtape")
        self.left_label.configure(
            fg=spec.MEDIA_ROW_MODE_SWITCH_LABEL_COLOR_ACTIVE if active_mode == "mixtape" else spec.MEDIA_ROW_MODE_SWITCH_LABEL_COLOR_INACTIVE
        )
        self.right_label.configure(
            fg=spec.MEDIA_ROW_MODE_SWITCH_LABEL_COLOR_ACTIVE if active_mode == "singles" else spec.MEDIA_ROW_MODE_SWITCH_LABEL_COLOR_INACTIVE
        )
        self._move_pill(immediate=True)

    def _target_x(self) -> int:
        return 15 if getattr(self._row, "row_mode", "mixtape") == "singles" else 0

    def _move_pill(self, *, immediate: bool) -> None:
        if self._anim_after_id is not None:
            try:
                self.after_cancel(self._anim_after_id)
            except tk.TclError:
                pass
            self._anim_after_id = None
        target_x = self._target_x()
        current = int(float(self.track.coords(self._pill_item)[0])) if self.track.coords(self._pill_item) else 0
        if immediate or current == target_x:
            self.track.coords(self._pill_item, target_x, 0)
            return
        distance = target_x - current
        steps = max(1, spec.MEDIA_ROW_MODE_SWITCH_ANIMATION_STEPS)
        step_index = 0

        def _advance() -> None:
            nonlocal step_index
            step_index += 1
            next_x = target_x if step_index >= steps else current + int(round(distance * (step_index / steps)))
            self.track.coords(self._pill_item, next_x, 0)
            if step_index < steps:
                self._anim_after_id = self.after(max(1, spec.MEDIA_ROW_MODE_SWITCH_ANIMATION_MS // steps), _advance)
            else:
                self._anim_after_id = None

        _advance()

    def _on_toggle(self, _event: tk.Event | None = None) -> str:
        next_mode = "singles" if getattr(self._row, "row_mode", "mixtape") == "mixtape" else "mixtape"
        if self._command is not None:
            self._command(next_mode)
        else:
            self._row.row_mode = next_mode
            self._move_pill(immediate=False)
            self.refresh()
        return "break"
