from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.icon_button import FolderIconButton


class FolderPathDisplay(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        width: int = spec.OUTPUT_FOLDER_DISPLAY_SIZE[0],
        height: int = spec.OUTPUT_FOLDER_DISPLAY_SIZE[1],
        bg_color: str = spec.OUTPUT_FOLDER_DISPLAY_BG,
        outline_color: str = spec.OUTPUT_FOLDER_DISPLAY_OUTLINE,
        outline_width: int = spec.OUTPUT_FOLDER_DISPLAY_OUTLINE_WIDTH,
        text_color: str = spec.OUTPUT_FOLDER_DISPLAY_TEXT_COLOR,
        font_family: str = spec.OUTPUT_FOLDER_DISPLAY_FONT_FAMILY,
        font_size: int = spec.OUTPUT_FOLDER_DISPLAY_FONT_SIZE,
        textvariable: tk.StringVar | None = None,
    ) -> None:
        super().__init__(parent, bg=outline_color, bd=0, highlightthickness=0, width=width, height=height)
        self.pack_propagate(False)

        self._variable = textvariable or tk.StringVar(master=self)
        inner_width = width - (outline_width * 2)
        inner_height = height - (outline_width * 2)

        self.inner = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=inner_width,
            height=inner_height,
        )
        self.inner.place(x=outline_width, y=outline_width)
        self.inner.pack_propagate(False)

        self.text_label = tk.Label(
            self.inner,
            textvariable=self._variable,
            bg=bg_color,
            fg=text_color,
            bd=0,
            highlightthickness=0,
            font=(font_family, font_size),
            anchor='w',
            justify='left',
        )
        self.text_label.place(
            x=spec.OUTPUT_FOLDER_DISPLAY_TEXT_PAD_X,
            y=0,
            width=max(1, inner_width - (spec.OUTPUT_FOLDER_DISPLAY_TEXT_PAD_X * 2)),
            height=inner_height,
        )


class OutputFolderField(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        label_text: str,
        folder_icon_path: str | Path | None,
        textvariable: tk.StringVar | None = None,
        command: Callable[[], None] | None = None,
        bg_color: str | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        self._left_inset = max(0, -spec.OUTPUT_FOLDER_ROW_X_OFFSET)
        label_x = self._left_inset
        display_x = self._left_inset + spec.OUTPUT_FOLDER_ROW_X_OFFSET
        button_x = (
            display_x
            + spec.OUTPUT_FOLDER_DISPLAY_SIZE[0]
            + spec.OUTPUT_FOLDER_BUTTON_GAP
        )
        total_width = max(
            label_x + spec.OUTPUT_FOLDER_LABEL_SIZE[0],
            button_x + spec.OUTPUT_FOLDER_BUTTON_SIZE[0],
        )
        total_height = (
            spec.OUTPUT_FOLDER_LABEL_SIZE[1]
            + spec.OUTPUT_FOLDER_ROW_GAP
            + spec.OUTPUT_FOLDER_DISPLAY_SIZE[1]
        )
        super().__init__(parent, bg=resolved_bg, bd=0, highlightthickness=0, width=total_width, height=total_height)
        self.pack_propagate(False)

        self.label_frame = tk.Frame(
            self,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=spec.OUTPUT_FOLDER_LABEL_SIZE[0],
            height=spec.OUTPUT_FOLDER_LABEL_SIZE[1],
        )
        self.label_frame.place(x=label_x, y=0)

        self.label = tk.Label(
            self.label_frame,
            text=label_text,
            bg=resolved_bg,
            fg=spec.TYPEABLE_LABEL_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=('Orbitron Medium', spec.TYPEABLE_LABEL_FONT_SIZE),
            anchor='w',
            justify='left',
        )
        self.label.place(x=0, y=0, width=spec.OUTPUT_FOLDER_LABEL_SIZE[0], height=spec.OUTPUT_FOLDER_LABEL_SIZE[1])

        row_y = spec.OUTPUT_FOLDER_LABEL_SIZE[1] + spec.OUTPUT_FOLDER_ROW_GAP
        self.path_display = FolderPathDisplay(self, textvariable=textvariable)
        self.path_display.place(x=display_x, y=row_y)

        self.folder_button = FolderIconButton(
            self,
            icon_path=folder_icon_path,
            command=command,
            size=spec.OUTPUT_FOLDER_BUTTON_SIZE,
        )
        self.folder_button.place(x=button_x, y=row_y)

    def set_enabled(self, enabled: bool) -> None:
        self.label.configure(fg=spec.TYPEABLE_LABEL_TEXT_COLOR if enabled else '#8f8a92')
        self.path_display.inner.configure(bg=spec.OUTPUT_FOLDER_DISPLAY_BG if enabled else '#4a474c')
        self.path_display.text_label.configure(
            bg=spec.OUTPUT_FOLDER_DISPLAY_BG if enabled else '#4a474c',
            fg=spec.OUTPUT_FOLDER_DISPLAY_TEXT_COLOR if enabled else '#a9a5ab',
        )
        self.folder_button.set_enabled(enabled)
