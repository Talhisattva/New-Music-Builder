from __future__ import annotations

import math
import tkinter as tk
import tkinter.font as tkfont

from new_music_builder.domain.models import ExportLogLine
from new_music_builder.ui import spec


class ModuleFourLogView(tk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=spec.PHASE_THREE_FOREGROUND_BG,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_MODULE_FOUR_LOG_VIEWPORT_SIZE[0],
            height=spec.PHASE_THREE_MODULE_FOUR_LOG_VIEWPORT_SIZE[1],
        )
        self.pack_propagate(False)
        self._width = spec.PHASE_THREE_MODULE_FOUR_LOG_VIEWPORT_SIZE[0]
        self._min_height = spec.PHASE_THREE_MODULE_FOUR_LOG_VIEWPORT_SIZE[1]
        self._lines: list[ExportLogLine] = []
        self._font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FOUR_LOG_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FOUR_LOG_FONT_SIZE,
        )

        border = spec.PHASE_THREE_MODULE_FOUR_LOG_INNER_BORDER_WIDTH
        self._surface = tk.Frame(
            self,
            bg=spec.PHASE_THREE_MODULE_FOUR_LOG_INNER_BG,
            bd=0,
            highlightthickness=border * 2,
            highlightbackground=spec.PHASE_THREE_MODULE_FOUR_LOG_INNER_BORDER_COLOR,
            highlightcolor=spec.PHASE_THREE_MODULE_FOUR_LOG_INNER_BORDER_COLOR,
        )
        self._surface.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        self._text = tk.Text(
            self._surface,
            bg=spec.PHASE_THREE_MODULE_FOUR_LOG_INNER_BG,
            fg=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_NEUTRAL,
            bd=0,
            highlightthickness=0,
            relief='flat',
            wrap='word',
            font=self._font,
            insertwidth=0,
            padx=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_ORIGIN[0],
            pady=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_ORIGIN[1],
            undo=False,
            exportselection=True,
            cursor='xterm',
            selectbackground=spec.MODULE_ACTION_HEADER_BG,
            selectforeground=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_NEUTRAL,
        )
        self._text.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self._text.tag_configure('neutral', foreground=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_NEUTRAL)
        self._text.tag_configure('queued', foreground=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_QUEUED)
        self._text.tag_configure('converting', foreground=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_CONVERTING)
        self._text.tag_configure('done', foreground=spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_DONE)
        self._text.tag_configure('error', foreground=spec.MAIN_BUTTON_NEGATIVE_TEXT_COLOR)
        self._text.bind('<KeyPress>', self._block_editing, add='+')
        self._text.bind('<Control-a>', self._select_all, add='+')
        self._text.bind('<Control-A>', self._select_all, add='+')
        self._text.bind('<Control-c>', self._copy_selection, add='+')
        self._text.bind('<Control-C>', self._copy_selection, add='+')
        self._text.bind('<<Copy>>', self._copy_selection, add='+')
        self._last_width = self._width
        self.redraw()

    def resize(self, width: int) -> None:
        if self._last_width == width:
            return
        self._width = width
        self._last_width = width
        self.redraw()

    def set_lines(self, lines: list[ExportLogLine]) -> None:
        self._lines = list(lines)
        self.redraw()

    def append_line(self, line: ExportLogLine) -> None:
        self._lines.append(line)
        self.redraw()

    def update_active_line(self, line: ExportLogLine) -> None:
        if self._lines:
            self._lines[-1] = line
        else:
            self._lines.append(line)
        self.redraw()

    def clear_lines(self) -> None:
        self._lines = []
        self.redraw()

    def content_height(self) -> int:
        rendered_lines = self._rendered_line_count()
        line_spacing = self._line_spacing()
        inner_height = (
            (spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_ORIGIN[1] * 2)
            + (rendered_lines * line_spacing)
            + 8
        )
        return max(self._min_height, inner_height)

    def redraw(self) -> None:
        height = self.content_height()
        self.configure(width=self._width, height=height)
        self._surface.place_configure(width=self._width, height=height)
        self._render_text()

    def _render_text(self) -> None:
        self._text.configure(state='normal')
        self._text.delete('1.0', 'end')
        for index, line in enumerate(self._lines):
            if index > 0:
                self._text.insert('end', '\n')
            self._text.insert('end', self._line_text(line), (self._tag_name(line.color_role),))
        self._text.configure(state='disabled')

    def _line_text(self, line: ExportLogLine) -> str:
        parts = [f'[{line.timestamp}]']
        if line.prefix_text:
            parts.append(line.prefix_text)
        if line.subject_text:
            parts.append(line.subject_text)
        if line.trailing_text:
            parts.append(line.trailing_text)
        if line.size_text:
            parts.append(line.size_text)
        return ' '.join(part for part in parts if part).rstrip()

    def _tag_name(self, role: str) -> str:
        if role == 'queued':
            return 'queued'
        if role == 'converting':
            return 'converting'
        if role == 'done':
            return 'done'
        if role == 'error':
            return 'error'
        return 'neutral'

    def _rendered_line_count(self) -> int:
        if not self._lines:
            return 1
        available_width = max(
            1,
            self._width - (spec.PHASE_THREE_MODULE_FOUR_LOG_TEXT_ORIGIN[0] * 2) - 8,
        )
        rendered_lines = 0
        for line in self._lines:
            text = self._line_text(line) or ' '
            line_width = max(1, self._font.measure(text))
            rendered_lines += max(1, math.ceil(line_width / available_width))
        return rendered_lines

    def _line_spacing(self) -> int:
        return max(spec.PHASE_THREE_MODULE_FOUR_LOG_LINE_GAP, self._font.metrics('linespace'))

    def _block_editing(self, event: tk.Event[tk.Text]) -> str:
        allowed = {
            'Left',
            'Right',
            'Up',
            'Down',
            'Home',
            'End',
            'Prior',
            'Next',
        }
        if (event.state & 0x4) and event.keysym.lower() in {'a', 'c'}:
            return ''
        if event.keysym in allowed:
            return ''
        return 'break'

    def _select_all(self, _event: tk.Event[tk.Text] | None = None) -> str:
        self._text.tag_add('sel', '1.0', 'end-1c')
        self._text.mark_set('insert', '1.0')
        self._text.see('insert')
        return 'break'

    def _copy_selection(self, _event: tk.Event[tk.Text] | None = None) -> str:
        try:
            selected_text = self._text.get('sel.first', 'sel.last')
        except tk.TclError:
            return 'break'
        self.clipboard_clear()
        self.clipboard_append(selected_text)
        return 'break'
