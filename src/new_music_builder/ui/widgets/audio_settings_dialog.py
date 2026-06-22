from __future__ import annotations

from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.audio_compression_dialog import _CompressionSlider
from new_music_builder.ui.widgets.dialog_shell import DialogShell
from new_music_builder.ui.widgets.labeled_checkbox import ImageCheckbox
from new_music_builder.ui.widgets.main_button import MainButton
from new_music_builder.ui.widgets.sample_rate_dialog import SampleRateDropdown


class AudioSettingsDialog(DialogShell):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        initial_sample_rate: int,
        initial_compression_quality: float,
        initial_reencode_existing_ogg: bool,
        check_icon_path: str | Path | None,
    ) -> None:
        super().__init__(
            parent,
            title=spec.AUDIO_SETTINGS_DIALOG_TITLE,
            icon_path=icon_path,
            size=spec.AUDIO_SETTINGS_DIALOG_SIZE,
            label_text="",
            label_wraplength=0,
        )
        self.result: tuple[int, float, bool] | None = None

        self.sample_label = tk.Label(
            self.panel_inner,
            text=spec.AUDIO_SETTINGS_SAMPLE_LABEL_TEXT,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.SAMPLE_RATE_DIALOG_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.SAMPLE_RATE_DIALOG_LABEL_FONT_FAMILY, spec.SAMPLE_RATE_DIALOG_LABEL_FONT_SIZE),
            anchor="w",
            justify="left",
        )
        self.sample_label.place(
            x=spec.AUDIO_SETTINGS_SAMPLE_LABEL_POS[0],
            y=spec.AUDIO_SETTINGS_SAMPLE_LABEL_POS[1],
            width=spec.AUDIO_SETTINGS_SAMPLE_LABEL_SIZE[0],
            height=spec.AUDIO_SETTINGS_SAMPLE_LABEL_SIZE[1],
        )

        self.sample_dropdown = SampleRateDropdown(
            self.panel_inner,
            options=[
                ("32000 Hz", 32000),
                ("44100 Hz", 44100),
                ("48000 Hz", 48000),
            ],
            initial_value=initial_sample_rate,
        )
        self.sample_dropdown.place(
            x=spec.AUDIO_SETTINGS_SAMPLE_DROPDOWN_POS[0],
            y=spec.AUDIO_SETTINGS_SAMPLE_DROPDOWN_POS[1],
        )

        self.quality_label = tk.Label(
            self.panel_inner,
            text=spec.AUDIO_SETTINGS_QUALITY_LABEL_TEXT,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.SAMPLE_RATE_DIALOG_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.SAMPLE_RATE_DIALOG_LABEL_FONT_FAMILY, spec.SAMPLE_RATE_DIALOG_LABEL_FONT_SIZE),
            anchor="w",
            justify="left",
        )
        self.quality_label.place(
            x=spec.AUDIO_SETTINGS_QUALITY_LABEL_POS[0],
            y=spec.AUDIO_SETTINGS_QUALITY_LABEL_POS[1],
            width=spec.AUDIO_SETTINGS_QUALITY_LABEL_SIZE[0],
            height=spec.AUDIO_SETTINGS_QUALITY_LABEL_SIZE[1],
        )

        self.status_label = tk.Label(
            self.panel_inner,
            text="",
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.COMPRESSION_DIALOG_STATUS_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.COMPRESSION_DIALOG_STATUS_FONT_FAMILY, spec.COMPRESSION_DIALOG_STATUS_FONT_SIZE),
            anchor="center",
            justify="center",
        )
        self.status_label.place(
            x=spec.AUDIO_SETTINGS_STATUS_POS[0],
            y=spec.AUDIO_SETTINGS_STATUS_POS[1],
            width=spec.AUDIO_SETTINGS_STATUS_SIZE[0],
            height=spec.AUDIO_SETTINGS_STATUS_SIZE[1],
        )

        self.compression_slider = _CompressionSlider(
            self.panel_inner,
            initial_value=initial_compression_quality,
            on_change=self._update_status_label,
        )
        self.compression_slider.place(
            x=spec.AUDIO_SETTINGS_SLIDER_POS[0],
            y=spec.AUDIO_SETTINGS_SLIDER_POS[1],
            width=spec.COMPRESSION_DIALOG_SLIDER_SIZE[0],
            height=spec.COMPRESSION_DIALOG_SLIDER_SIZE[1],
        )
        self._update_status_label(self.compression_slider.get_label())
        hint_row_y = spec.COMPRESSION_DIALOG_HINT_ROW_Y + (spec.AUDIO_SETTINGS_SLIDER_POS[1] - spec.COMPRESSION_DIALOG_SLIDER_POS[1])
        self.lowest_label = tk.Label(
            self.panel_inner,
            text="Lowest",
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.COMPRESSION_DIALOG_HINT_PRIMARY_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.COMPRESSION_DIALOG_HINT_PRIMARY_FONT_FAMILY, spec.COMPRESSION_DIALOG_HINT_PRIMARY_FONT_SIZE),
            anchor="w",
            justify="left",
        )
        self.lowest_label.place(
            x=spec.COMPRESSION_DIALOG_HINT_LEFT_LABEL_X,
            y=hint_row_y,
            width=spec.COMPRESSION_DIALOG_HINT_LEFT_LABEL_WIDTH,
            height=spec.COMPRESSION_DIALOG_HINT_ROW_HEIGHT,
        )
        self.lowest_hint_label = tk.Label(
            self.panel_inner,
            text="(Largest File Size)",
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.COMPRESSION_DIALOG_HINT_SECONDARY_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.COMPRESSION_DIALOG_HINT_SECONDARY_FONT_FAMILY, spec.COMPRESSION_DIALOG_HINT_SECONDARY_FONT_SIZE),
            anchor="w",
            justify="left",
        )
        self.lowest_hint_label.place(
            x=spec.COMPRESSION_DIALOG_HINT_LEFT_TEXT_X,
            y=hint_row_y,
            width=spec.COMPRESSION_DIALOG_HINT_LEFT_TEXT_WIDTH,
            height=spec.COMPRESSION_DIALOG_HINT_ROW_HEIGHT,
        )
        self.highest_label = tk.Label(
            self.panel_inner,
            text="Highest",
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.COMPRESSION_DIALOG_HINT_PRIMARY_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.COMPRESSION_DIALOG_HINT_PRIMARY_FONT_FAMILY, spec.COMPRESSION_DIALOG_HINT_PRIMARY_FONT_SIZE),
            anchor="w",
            justify="left",
        )
        self.highest_label.place(
            x=spec.COMPRESSION_DIALOG_HINT_RIGHT_LABEL_X,
            y=hint_row_y,
            width=spec.COMPRESSION_DIALOG_HINT_RIGHT_LABEL_WIDTH,
            height=spec.COMPRESSION_DIALOG_HINT_ROW_HEIGHT,
        )
        self.highest_hint_label = tk.Label(
            self.panel_inner,
            text="(Smallest File Size)",
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.COMPRESSION_DIALOG_HINT_SECONDARY_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.COMPRESSION_DIALOG_HINT_SECONDARY_FONT_FAMILY, spec.COMPRESSION_DIALOG_HINT_SECONDARY_FONT_SIZE),
            anchor="w",
            justify="left",
        )
        self.highest_hint_label.place(
            x=spec.COMPRESSION_DIALOG_HINT_RIGHT_TEXT_X,
            y=hint_row_y,
            width=spec.COMPRESSION_DIALOG_HINT_RIGHT_TEXT_WIDTH,
            height=spec.COMPRESSION_DIALOG_HINT_ROW_HEIGHT,
        )

        self.reencode_label = tk.Label(
            self.panel_inner,
            text=spec.AUDIO_SETTINGS_REENCODE_LABEL_TEXT,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.SAMPLE_RATE_DIALOG_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.SAMPLE_RATE_DIALOG_LABEL_FONT_FAMILY, spec.SAMPLE_RATE_DIALOG_LABEL_FONT_SIZE),
            anchor="w",
            justify="left",
        )
        self.reencode_label.place(
            x=spec.AUDIO_SETTINGS_REENCODE_LABEL_POS[0],
            y=spec.AUDIO_SETTINGS_REENCODE_LABEL_POS[1],
            width=spec.AUDIO_SETTINGS_REENCODE_LABEL_SIZE[0],
            height=spec.AUDIO_SETTINGS_REENCODE_LABEL_SIZE[1],
        )

        self.reencode_checkbox = ImageCheckbox(
            self.panel_inner,
            icon_path=check_icon_path,
            bg_color=spec.POSTER_NAME_CHECKBOX_BG,
            outline_color=spec.POSTER_NAME_CHECKBOX_OUTLINE,
            checked=initial_reencode_existing_ogg,
        )
        self.reencode_checkbox.place(
            x=spec.AUDIO_SETTINGS_CHECKBOX_POS[0],
            y=spec.AUDIO_SETTINGS_CHECKBOX_POS[1],
        )

        button_width = spec.MAIN_BUTTON_SIZE[0]
        total_buttons_width = (button_width * 2) + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X
        button_x = ((spec.AUDIO_SETTINGS_DIALOG_SIZE[0] - 20) - total_buttons_width) // 2
        self.ok_button = MainButton(self.panel_inner, text="OK", command=self._accept, variant="positive")
        self.ok_button.place(x=button_x, y=spec.AUDIO_SETTINGS_BUTTON_Y, width=button_width, height=spec.MAIN_BUTTON_SIZE[1])
        self.cancel_button = MainButton(self.panel_inner, text="CANCEL", command=self._cancel, variant="negative")
        self.cancel_button.place(
            x=button_x + button_width + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X,
            y=spec.AUDIO_SETTINGS_BUTTON_Y,
            width=button_width,
            height=spec.MAIN_BUTTON_SIZE[1],
        )

    def show(self) -> tuple[int, float, bool] | None:
        self.show_modal()
        self.wait_window()
        return self.result

    def _update_status_label(self, label: str) -> None:
        self.status_label.configure(text=label)

    def _accept(self) -> None:
        self.result = (
            self.sample_dropdown.get(),
            self.compression_slider.get(),
            self.reencode_checkbox.is_checked(),
        )
        self.close_dialog()

    def _cancel(self) -> None:
        self.result = None
        self.close_dialog()

    def _on_window_close(self) -> None:
        self._cancel()
