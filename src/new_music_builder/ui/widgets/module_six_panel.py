from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
import tkinter.font as tkfont

from new_music_builder.domain.models import BuildSummaryStats
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage
from new_music_builder.ui.widgets.module_six_stats_table import ModuleSixStatsTable


class _BuildStatusCard(tk.Canvas):
    def __init__(self, parent: tk.Misc, *, icon_path: str | None = None) -> None:
        super().__init__(
            parent,
            bg=spec.MODULE_SIX_BUTTON_RESET_BG,
            width=spec.MODULE_SIX_BUTTON_COMPLETE_SIZE[0],
            height=spec.MODULE_SIX_BUTTON_COMPLETE_SIZE[1],
            bd=0,
            highlightthickness=0,
        )
        self._icon = load_tk_photoimage(icon_path, spec.MODULE_SIX_BUTTON_COMPLETE_ICON_SIZE)
        self._title_text = 'BUILD COMPLETE'
        self._summary_text = '0/0 Media - 0 Songs'
        self._state: str = 'idle'
        self._title_font = tkfont.Font(
            family=spec.MODULE_SIX_BUTTON_COMPLETE_TITLE_FONT_FAMILY,
            size=spec.MODULE_SIX_BUTTON_COMPLETE_TITLE_FONT_SIZE,
        )
        self._subtitle_font = tkfont.Font(
            family=spec.MODULE_SIX_BUTTON_COMPLETE_SUBTITLE_FONT_FAMILY,
            size=spec.MODULE_SIX_BUTTON_COMPLETE_SUBTITLE_FONT_SIZE,
        )
        self._draw()

    def set_stats(self, stats: BuildSummaryStats) -> None:
        self._title_text = 'BUILD ERROR' if stats.errors else 'BUILD COMPLETE'
        self._summary_text = f'{stats.exported_media_rows}/{stats.media_rows} Media - {stats.built_songs}/{stats.total_songs} Songs'
        self._state = 'error' if stats.errors else 'complete'
        self._draw()

    def reset(self) -> None:
        self._title_text = 'BUILD COMPLETE'
        self._summary_text = '0/0 Media - 0 Songs'
        self._state = 'idle'
        self._draw()

    def _draw(self) -> None:
        self.delete('all')
        width, height = spec.MODULE_SIX_BUTTON_COMPLETE_SIZE
        title_height = self._title_font.metrics('linespace')
        subtitle_height = self._subtitle_font.metrics('linespace')
        gap_height = spec.MODULE_SIX_BUTTON_COMPLETE_TEXT_GAP_Y
        group_height = title_height + gap_height + subtitle_height
        group_top = (height - group_height) / 2
        title_y = group_top + (title_height / 2)
        subtitle_y = group_top + title_height + gap_height + (subtitle_height / 2)
        is_complete = self._state == 'complete'
        is_error = self._state == 'error'
        border_fill = spec.MODULE_SIX_BUTTON_RESET_BORDER_COLOR
        card_fill = spec.MODULE_SIX_BUTTON_RESET_BG
        title_fill = spec.MODULE_SIX_BUTTON_COMPLETE_TEXT_COLOR
        subtitle_fill = spec.MODULE_SIX_BUTTON_COMPLETE_SUBTITLE_COLOR
        if is_complete:
            border_fill = spec.MODULE_SIX_BUTTON_COMPLETE_BORDER_COLOR
            card_fill = spec.MODULE_SIX_BUTTON_COMPLETE_BG
        elif is_error:
            border_fill = spec.MAIN_BUTTON_NEGATIVE_OUTLINE
            card_fill = spec.MAIN_BUTTON_NEGATIVE_BG
            title_fill = spec.MODULE_SIX_STATS_ERROR_TEXT_COLOR

        self.create_rectangle(
            0,
            0,
            width,
            height,
            outline='',
            fill=border_fill,
        )
        self.create_rectangle(
            1,
            1,
            width - 1,
            height - 1,
            outline='',
            fill=card_fill,
        )
        if is_complete and self._icon is not None:
            self.create_image(
                spec.MODULE_SIX_BUTTON_COMPLETE_ICON_CENTER_X,
                height / 2,
                image=self._icon,
                anchor='c',
            )
        if self._state != 'idle':
            self.create_text(
                width / 2,
                title_y,
                text=self._title_text,
                fill=title_fill,
                font=self._title_font,
                anchor='c',
                justify='center',
            )
            self.create_text(
                width / 2,
                subtitle_y,
                text=self._summary_text,
                fill=subtitle_fill,
                font=self._subtitle_font,
                anchor='c',
                justify='center',
            )


class _IconActionButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int],
        bg_color: str,
        hover_bg_color: str | None,
        pressed_bg_color: str | None,
        border_color: str | None,
        text: str,
        text_color: str,
        font: tuple[str, int],
        icon_path: str | None,
        icon_size: tuple[int, int],
        icon_center_x: int,
        command: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            width=size[0],
            height=size[1],
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._bg_color = bg_color
        self._hover_bg_color = hover_bg_color or bg_color
        self._pressed_bg_color = pressed_bg_color or self._hover_bg_color
        self._border_color = border_color
        self._text = text
        self._text_color = text_color
        self._font = font
        self._icon = load_tk_photoimage(icon_path, icon_size)
        self._icon_center_x = icon_center_x
        self._command = command
        self._hovered = False
        self._pressed = False
        self._bind_events()
        self._draw()

    def _bind_events(self) -> None:
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _current_fill(self) -> str:
        if self._pressed:
            return self._pressed_bg_color
        if self._hovered:
            return self._hover_bg_color
        return self._bg_color

    def _draw(self) -> None:
        self.delete('all')
        width, height = self._size
        fill = self._current_fill()
        if self._border_color is not None:
            self.create_rectangle(0, 0, width, height, outline='', fill=self._border_color)
            self.create_rectangle(1, 1, width - 1, height - 1, outline='', fill=fill)
        else:
            self.create_rectangle(0, 0, width, height, outline='', fill=fill)
        if self._icon is not None:
            self.create_image(self._icon_center_x, height / 2, image=self._icon, anchor='c')
        self.create_text(
            width / 2,
            height / 2,
            text=self._text,
            fill=self._text_color,
            font=self._font,
            anchor='c',
            justify='center',
        )

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._hovered = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event: tk.Event | None = None) -> str:
        self._pressed = True
        self._draw()
        return 'break'

    def _on_release(self, event: tk.Event | None = None) -> str:
        was_pressed = self._pressed
        self._pressed = False
        inside = event is not None and 0 <= event.x <= self._size[0] and 0 <= event.y <= self._size[1]
        self._draw()
        if was_pressed and inside and self._command is not None:
            self._command()
        return 'break'


class ModuleSixPanel(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        build_complete_icon_path: str | None = None,
        open_folder_icon_path: str | None = None,
        reset_icon_path: str | None = None,
        on_open_output_folder: Callable[[], None] | None = None,
        on_reset: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=spec.MODULE_MIDGROUND_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_SIX_MIDGROUND_SIZE[0],
            height=spec.MODULE_SIX_MIDGROUND_SIZE[1],
        )
        self.pack_propagate(False)

        self.stats_table = ModuleSixStatsTable(self)
        self.stats_table.place(
            x=spec.MODULE_SIX_STATS_PANE_POS[0],
            y=spec.MODULE_SIX_STATS_PANE_POS[1],
        )

        self.complete_card = _BuildStatusCard(self, icon_path=build_complete_icon_path)
        self.complete_card.place(
            x=spec.MODULE_SIX_BUTTON_COMPLETE_POS[0],
            y=spec.MODULE_SIX_BUTTON_COMPLETE_POS[1],
        )

        self.open_folder_button = _IconActionButton(
            self,
            size=spec.MODULE_SIX_BUTTON_OPEN_SIZE,
            bg_color=spec.MODULE_SIX_BUTTON_OPEN_BG,
            hover_bg_color=spec.MODULE_ACTION_HEADER_HOVER_BG,
            pressed_bg_color=spec.MODULE_ACTION_HEADER_PRESSED_BG,
            border_color=None,
            text='OPEN OUTPUT FOLDER',
            text_color=spec.MODULE_SIX_BUTTON_OPEN_TEXT_COLOR,
            font=(
                spec.MODULE_SIX_BUTTON_OPEN_FONT_FAMILY,
                spec.MODULE_SIX_BUTTON_OPEN_FONT_SIZE,
            ),
            icon_path=open_folder_icon_path,
            icon_size=spec.MODULE_SIX_BUTTON_OPEN_ICON_SIZE,
            icon_center_x=spec.MODULE_SIX_BUTTON_OPEN_ICON_CENTER_X,
            command=on_open_output_folder,
        )
        self.open_folder_button.place(
            x=spec.MODULE_SIX_BUTTON_OPEN_POS[0],
            y=spec.MODULE_SIX_BUTTON_OPEN_POS[1],
        )

        self.reset_button = _IconActionButton(
            self,
            size=spec.MODULE_SIX_BUTTON_RESET_SIZE,
            bg_color=spec.MODULE_SIX_BUTTON_RESET_BG,
            hover_bg_color=spec.MODULE_SIX_BUTTON_RESET_HOVER_BG,
            pressed_bg_color=spec.MODULE_SIX_BUTTON_RESET_PRESSED_BG,
            border_color=spec.MODULE_SIX_BUTTON_RESET_BORDER_COLOR,
            text='RESET',
            text_color=spec.MODULE_SIX_BUTTON_RESET_TEXT_COLOR,
            font=(
                spec.MODULE_SIX_BUTTON_RESET_FONT_FAMILY,
                spec.MODULE_SIX_BUTTON_RESET_FONT_SIZE,
            ),
            icon_path=reset_icon_path,
            icon_size=spec.MODULE_SIX_BUTTON_RESET_ICON_SIZE,
            icon_center_x=spec.MODULE_SIX_BUTTON_RESET_ICON_CENTER_X,
            command=on_reset,
        )
        self.reset_button.place(
            x=spec.MODULE_SIX_BUTTON_RESET_POS[0],
            y=spec.MODULE_SIX_BUTTON_RESET_POS[1],
        )

    def set_stats(self, stats: BuildSummaryStats) -> None:
        self.stats_table.set_stats(stats)
        self.complete_card.set_stats(stats)

    def reset(self) -> None:
        self.stats_table.reset_stats()
        self.complete_card.reset()
