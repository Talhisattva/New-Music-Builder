from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.services.audio_profile import AUDIO_COMPRESSION_PRESETS, nearest_compression_preset
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.dialog_shell import DialogShell
from new_music_builder.ui.widgets.main_button import MainButton


class _CompressionSlider(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        initial_value: float,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        width, height = spec.COMPRESSION_DIALOG_SLIDER_SIZE
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            bd=0,
            highlightthickness=0,
        )
        self._on_change = on_change
        self._presets = AUDIO_COMPRESSION_PRESETS
        self._selected_index = self._nearest_index(initial_value)
        self.bind("<ButtonPress-1>", self._handle_pointer, add="+")
        self.bind("<B1-Motion>", self._handle_pointer, add="+")
        self._draw()

    def get(self) -> float:
        return self._presets[self._selected_index].value

    def get_label(self) -> str:
        return self._presets[self._selected_index].label

    def _nearest_index(self, value: float) -> int:
        preset = nearest_compression_preset(value)
        for index, candidate in enumerate(self._presets):
            if candidate == preset:
                return index
        return 2

    def _handle_pointer(self, event: tk.Event) -> str:
        margin = spec.COMPRESSION_DIALOG_SLIDER_SIDE_MARGIN
        track_width = spec.COMPRESSION_DIALOG_SLIDER_TRACK_WIDTH
        x = max(margin, min(int(getattr(event, "x", 0)), margin + track_width))
        self._set_index_from_x(x)
        return "break"

    def _set_index_from_x(self, x: int) -> None:
        margin = spec.COMPRESSION_DIALOG_SLIDER_SIDE_MARGIN
        normalized_x = x - margin
        if len(self._presets) == 1:
            index = 0
        else:
            step = spec.COMPRESSION_DIALOG_SLIDER_TRACK_WIDTH / (len(self._presets) - 1)
            index = int(round(normalized_x / step))
        index = max(0, min(index, len(self._presets) - 1))
        if index == self._selected_index:
            return
        self._selected_index = index
        self._draw()
        if self._on_change is not None:
            self._on_change(self.get_label())

    def _draw(self) -> None:
        self.delete("all")
        knob_size = spec.COMPRESSION_DIALOG_SLIDER_KNOB_SIZE
        track_height = spec.COMPRESSION_DIALOG_SLIDER_TRACK_HEIGHT
        width = spec.COMPRESSION_DIALOG_SLIDER_TRACK_WIDTH
        height = spec.COMPRESSION_DIALOG_SLIDER_SIZE[1]
        margin = spec.COMPRESSION_DIALOG_SLIDER_SIDE_MARGIN
        track_top = (height - track_height) // 2
        track_bottom = track_top + track_height
        self.create_rectangle(
            margin,
            track_top,
            margin + width,
            track_bottom,
            fill=spec.COMPRESSION_DIALOG_SLIDER_TRACK_COLOR,
            outline="",
        )
        x = self._knob_center_x(self._selected_index)
        top = (height - knob_size) // 2
        self.create_oval(
            x - (knob_size // 2),
            top,
            x + (knob_size // 2),
            top + knob_size,
            fill=spec.COMPRESSION_DIALOG_SLIDER_KNOB_COLOR,
            outline="",
        )

    def _knob_center_x(self, index: int) -> int:
        margin = spec.COMPRESSION_DIALOG_SLIDER_SIDE_MARGIN
        if len(self._presets) == 1:
            return margin + (spec.COMPRESSION_DIALOG_SLIDER_TRACK_WIDTH // 2)
        step = spec.COMPRESSION_DIALOG_SLIDER_TRACK_WIDTH / (len(self._presets) - 1)
        return margin + int(round(index * step))


class AudioCompressionDialog(DialogShell):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        initial_value: float,
    ) -> None:
        super().__init__(
            parent,
            title=spec.COMPRESSION_DIALOG_TITLE,
            icon_path=icon_path,
            size=spec.COMPRESSION_DIALOG_SIZE,
            label_text=spec.COMPRESSION_DIALOG_LABEL_TEXT,
            label_wraplength=spec.COMPRESSION_DIALOG_LABEL_SIZE[0],
        )
        self.result: float | None = None
        self.label.place(
            x=spec.COMPRESSION_DIALOG_LABEL_POS[0],
            y=spec.COMPRESSION_DIALOG_LABEL_POS[1],
            width=spec.COMPRESSION_DIALOG_LABEL_SIZE[0],
            height=spec.COMPRESSION_DIALOG_LABEL_SIZE[1],
        )
        self.label.configure(anchor="center", justify="center")

        initial_label = nearest_compression_preset(initial_value).label
        self.status_label = tk.Label(
            self.panel_inner,
            text=initial_label,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.COMPRESSION_DIALOG_STATUS_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.COMPRESSION_DIALOG_STATUS_FONT_FAMILY, spec.COMPRESSION_DIALOG_STATUS_FONT_SIZE),
            anchor="center",
            justify="center",
        )
        self.status_label.place(
            x=spec.COMPRESSION_DIALOG_STATUS_POS[0],
            y=spec.COMPRESSION_DIALOG_STATUS_POS[1],
            width=spec.COMPRESSION_DIALOG_STATUS_SIZE[0],
            height=spec.COMPRESSION_DIALOG_STATUS_SIZE[1],
        )

        self.slider = _CompressionSlider(
            self.panel_inner,
            initial_value=initial_value,
            on_change=self._update_status_label,
        )
        self.slider.place(
            x=spec.COMPRESSION_DIALOG_SLIDER_POS[0],
            y=spec.COMPRESSION_DIALOG_SLIDER_POS[1],
            width=spec.COMPRESSION_DIALOG_SLIDER_SIZE[0],
            height=spec.COMPRESSION_DIALOG_SLIDER_SIZE[1],
        )

        button_width = spec.MAIN_BUTTON_SIZE[0]
        total_buttons_width = (button_width * 2) + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X
        button_x = ((spec.COMPRESSION_DIALOG_SIZE[0] - 20) - total_buttons_width) // 2
        self.ok_button = MainButton(self.panel_inner, text="OK", command=self._accept, variant="positive")
        self.ok_button.place(x=button_x, y=spec.COMPRESSION_DIALOG_BUTTON_Y, width=button_width, height=spec.MAIN_BUTTON_SIZE[1])
        self.cancel_button = MainButton(self.panel_inner, text="CANCEL", command=self._cancel, variant="negative")
        self.cancel_button.place(
            x=button_x + button_width + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X,
            y=spec.COMPRESSION_DIALOG_BUTTON_Y,
            width=button_width,
            height=spec.MAIN_BUTTON_SIZE[1],
        )

    def show(self) -> float | None:
        self.show_modal()
        self.wait_window()
        return self.result

    def _update_status_label(self, label: str) -> None:
        self.status_label.configure(text=label)

    def _accept(self) -> None:
        self.result = self.slider.get()
        self.close_dialog()

    def _cancel(self) -> None:
        self.result = None
        self.close_dialog()

    def _on_window_close(self) -> None:
        self._cancel()
