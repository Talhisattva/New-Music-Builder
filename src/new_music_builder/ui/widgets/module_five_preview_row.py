from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from new_music_builder.domain.models import GeneratedPreviewCell, GeneratedPreviewRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.cursor_tooltip import CursorTooltip
from new_music_builder.ui.widgets.images import (
    load_tk_photoimage_contained,
    load_tk_photoimage_horizontal_fill,
)

_SLOT_KEYS = ('cassette', 'vinyl', 'cd', 'case', 'jacket', 'cd_cover')


class ModuleFivePreviewRow(tk.Canvas):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=spec.PHASE_THREE_MODULE_FIVE_CELL_BG,
            bd=0,
            highlightthickness=0,
            width=spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[0],
            height=spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE[1],
        )
        self._row = None
        self._tooltip_hide_after_id: str | None = None
        self._cursor_tooltip = CursorTooltip(self)
        self._icon_images: list[tk.PhotoImage | None] = []
        self._cover_images: list[tk.PhotoImage | None] = []
        self._header_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FIVE_TITLE_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FIVE_TITLE_FONT_SIZE,
        )
        self._section_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FIVE_SECTION_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FIVE_SECTION_FONT_SIZE,
        )
        self._meta_font = tkfont.Font(
            family=spec.PHASE_THREE_MODULE_FIVE_META_FONT_FAMILY,
            size=spec.PHASE_THREE_MODULE_FIVE_META_FONT_SIZE,
        )

    def set_row(self, row: GeneratedPreviewRow) -> None:
        self._row = row
        self._redraw()

    def _redraw(self) -> None:
        self.delete('all')
        self._icon_images.clear()
        self._cover_images.clear()
        if self._row is None:
            return

        row_width, row_height = spec.PHASE_THREE_MODULE_FIVE_ROW_SIZE
        cell_width, cell_height = spec.PHASE_THREE_MODULE_FIVE_CELL_SIZE
        divider_x = cell_width

        self.create_rectangle(
            0,
            0,
            row_width,
            row_height,
            outline='',
            fill=spec.PHASE_THREE_MODULE_FIVE_CELL_BG,
        )
        self._draw_cell(0, self._row.inventory_cell, tooltip_world=False)
        self._draw_cell(cell_width, self._row.world_cell, tooltip_world=True)
        self.create_rectangle(
            divider_x,
            0,
            divider_x + spec.PHASE_THREE_MODULE_FIVE_CELL_DIVIDER_WIDTH,
            row_height,
            outline='',
            fill=spec.PHASE_THREE_MODULE_FIVE_CELL_DIVIDER_COLOR,
        )
        self.create_rectangle(
            0,
            row_height - spec.PHASE_THREE_MODULE_FIVE_CELL_DIVIDER_WIDTH,
            row_width,
            row_height,
            outline='',
            fill=spec.PHASE_THREE_MODULE_FIVE_CELL_DIVIDER_COLOR,
        )

    def _draw_cell(self, cell_x: int, cell: GeneratedPreviewCell, *, tooltip_world: bool) -> None:
        cell_width, cell_height = spec.PHASE_THREE_MODULE_FIVE_CELL_SIZE
        cover_image = load_tk_photoimage_horizontal_fill(
            cell.cover_path,
            spec.PHASE_THREE_MODULE_FIVE_CELL_SIZE,
            opacity_percent=spec.PHASE_THREE_MODULE_FIVE_COVER_OPACITY_PERCENT,
        )
        self._cover_images.append(cover_image)
        if cover_image is not None:
            self.create_image(cell_x, 0, image=cover_image, anchor='nw')

        title_x = cell_x + spec.PHASE_THREE_MODULE_FIVE_TITLE_POS[0]
        title_y = spec.PHASE_THREE_MODULE_FIVE_TITLE_POS[1]
        self.create_text(
            title_x,
            title_y,
            text=cell.label_text,
            fill=spec.PHASE_THREE_MODULE_FIVE_TITLE_COLOR,
            font=self._header_font,
            anchor='nw',
        )
        self.create_text(
            title_x,
            title_y + spec.PHASE_THREE_MODULE_FIVE_SECTION_GAP_Y,
            text=cell.section_text,
            fill=spec.PHASE_THREE_MODULE_FIVE_SECTION_COLOR,
            font=self._section_font,
            anchor='nw',
        )

        right_x = cell_x + cell_width - spec.PHASE_THREE_MODULE_FIVE_META_RIGHT_INSET
        self._draw_meta_line(
            right_x,
            title_y,
            prefix='Songs:',
            value=f'{cell.song_count} Songs',
        )
        self._draw_meta_line(
            right_x,
            title_y + spec.PHASE_THREE_MODULE_FIVE_META_DURATION_GAP_Y,
            prefix='Duration:',
            value=cell.duration_text,
        )

        icon_x = cell_x + spec.PHASE_THREE_MODULE_FIVE_ICON_START[0]
        icon_y = spec.PHASE_THREE_MODULE_FIVE_ICON_START[1]
        icon_width, _icon_height = spec.PHASE_THREE_MODULE_FIVE_ICON_SIZE
        for index, path in enumerate(cell.slot_paths):
            slot_left = icon_x + (index * (icon_width + spec.PHASE_THREE_MODULE_FIVE_ICON_GAP_X))
            self.create_rectangle(
                slot_left,
                icon_y,
                slot_left + icon_width,
                icon_y + spec.PHASE_THREE_MODULE_FIVE_ICON_SIZE[1],
                outline='',
                fill='',
            )
            icon_image = load_tk_photoimage_contained(path, spec.PHASE_THREE_MODULE_FIVE_ICON_SIZE) if path else None
            self._icon_images.append(icon_image)
            if icon_image is not None:
                self.create_image(slot_left, icon_y, image=icon_image, anchor='nw')
            if tooltip_world:
                hover_tag = f'world_slot_{cell_x}_{index}'
                self.create_rectangle(
                    slot_left,
                    icon_y,
                    slot_left + icon_width,
                    icon_y + spec.PHASE_THREE_MODULE_FIVE_ICON_SIZE[1],
                    outline='',
                    fill='',
                    tags=(hover_tag,),
                )
                self.tag_bind(hover_tag, '<Enter>', lambda event, value=path: self._on_world_enter(value, event), add='+')
                self.tag_bind(hover_tag, '<Motion>', lambda event, value=path: self._on_world_motion(value, event), add='+')
                self.tag_bind(hover_tag, '<Leave>', self._on_world_leave, add='+')

    def _draw_meta_line(self, right_x: int, y: int, *, prefix: str, value: str) -> None:
        value_width = self._meta_font.measure(value)
        prefix_width = self._meta_font.measure(prefix)
        gap_width = self._meta_font.measure(' ')
        self.create_text(
            right_x - value_width - gap_width,
            y,
            text=prefix,
            fill=spec.PHASE_THREE_MODULE_FIVE_META_LABEL_COLOR,
            font=self._meta_font,
            anchor='ne',
        )
        self.create_text(
            right_x,
            y,
            text=value,
            fill=spec.PHASE_THREE_MODULE_FIVE_META_VALUE_COLOR,
            font=self._meta_font,
            anchor='ne',
        )

    def _on_world_enter(self, path: str | None, event: tk.Event) -> None:
        if not path:
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        self._cursor_tooltip.set_image(path)
        self._cursor_tooltip.show_at_cursor(int(event.x_root), int(event.y_root), direction='left')

    def _on_world_motion(self, path: str | None, event: tk.Event) -> None:
        if not path:
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        self._cursor_tooltip.set_image(path)
        self._cursor_tooltip.move_to_cursor(int(event.x_root), int(event.y_root))

    def _on_world_leave(self, _event: tk.Event) -> None:
        self._schedule_tooltip_hide()

    def _schedule_tooltip_hide(self) -> None:
        self._cancel_tooltip_hide()
        self._tooltip_hide_after_id = self.after(spec.MODULE_THREE_GRID_HOVER_HIDE_DELAY_MS, self._hide_tooltip_now)

    def _cancel_tooltip_hide(self) -> None:
        if self._tooltip_hide_after_id is not None:
            try:
                self.after_cancel(self._tooltip_hide_after_id)
            except tk.TclError:
                pass
            self._tooltip_hide_after_id = None

    def _hide_tooltip_now(self) -> None:
        self._tooltip_hide_after_id = None
        self._cursor_tooltip.hide()
