from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.domain.models import AppearanceKind, MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.cursor_tooltip import CursorTooltip
from new_music_builder.ui.widgets.images import cache_token_for_path, load_tk_photoimage_contained
from new_music_builder.ui.widgets.preview_mode_toggle import PreviewModeToggle


class MediaLivePreview(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        bg_color: str,
        resolve_preview_path: Callable[[MediaRow, AppearanceKind, str, bool], str | None] | None = None,
        on_mode_selected: Callable[[int, str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[1],
        )
        self.pack_propagate(False)
        self._row = row
        self._row_id = row.row_id
        self._selected_mode = row.preview_mode
        self._resolve_preview_path = resolve_preview_path
        self._on_mode_selected = on_mode_selected
        self._content_bg = spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_BG
        self._slot_keys = (
            ('cassette', 'case'),
            ('vinyl', 'jacket'),
            ('cd', 'cd_cover'),
        )
        self._slot_frames: list[tk.Frame] = []
        self._slot_labels: list[tk.Label] = []
        self._slot_kinds: list[AppearanceKind] = []
        self._images: dict[tuple[str, str, object], tk.PhotoImage | None] = {}
        self._tooltip_hide_after_id: str | None = None
        self._dual_phase_show_empty = False
        self._dual_phase_after_id: str | None = None
        self._cursor_tooltip = CursorTooltip(self)

        self.header = tk.Frame(
            self,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_HEIGHT,
        )
        self.header.place(x=0, y=0)
        self.header.pack_propagate(False)

        self.header_fill = tk.Frame(
            self.header,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0] - (spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH * 2),
            height=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_HEIGHT - (spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH * 2),
        )
        self.header_fill.place(
            x=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH,
            y=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_OUTLINE_WIDTH,
        )
        self.header_fill.pack_propagate(False)

        self.header_label = tk.Label(
            self.header_fill,
            text=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_TEXT,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_BG,
            fg=spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_TEXT_COLOR,
            font=(
                spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_FONT_FAMILY,
                spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_FONT_SIZE,
            ),
        )
        self.header_label.place(relx=0.5, rely=0.5, anchor='c')

        strip_y = spec.MEDIA_ROW_LIVE_PREVIEW_HEADER_HEIGHT
        self.mode_strip = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_STRIP_HEIGHT,
        )
        self.mode_strip.place(x=0, y=strip_y)
        self.mode_strip.pack_propagate(False)

        self.mode_toggle = PreviewModeToggle(
            self.mode_strip,
            left_text='Inventory',
            right_text='World',
            left_mode='inventory',
            right_mode='world',
            left_width=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_BUTTON_SIZE[0],
            right_width=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_BUTTON_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_STRIP_HEIGHT,
            initial_mode=self._selected_mode,
            command=self._select_mode,
            bg_color=bg_color,
            outline_color=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE,
            outline_width=spec.MEDIA_ROW_LIVE_PREVIEW_MODE_OUTLINE_WIDTH,
        )
        self.mode_toggle.place(x=0, y=0)

        content_y = strip_y + spec.MEDIA_ROW_LIVE_PREVIEW_MODE_STRIP_HEIGHT
        self.content_border = tk.Frame(
            self,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[1],
        )
        self.content_border.place(x=0, y=content_y)
        self.content_border.pack_propagate(False)

        self.content_area = tk.Frame(
            self.content_border,
            bg=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[0] - (spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH * 2),
            height=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_SIZE[1] - (spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH * 2),
        )
        self.content_area.place(
            x=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH,
            y=spec.MEDIA_ROW_LIVE_PREVIEW_CONTENT_OUTLINE_WIDTH,
        )
        self.content_area.pack_propagate(False)

        self._build_content_slots()
        self._build_column_labels()

        self._apply_state()

    def _image_for_slot(self, mode: str, kind: AppearanceKind) -> tk.PhotoImage | None:
        if self._resolve_preview_path is None:
            return None
        path = self._resolve_preview_path(self._row, kind, mode, self._dual_phase_show_empty)
        if not path:
            return None
        cache_key = (mode, kind, self._dual_phase_show_empty, cache_token_for_path(path) or path)
        if cache_key not in self._images:
            self._images[cache_key] = load_tk_photoimage_contained(path, spec.MEDIA_ROW_LIVE_PREVIEW_IMAGE_SIZE)
        return self._images[cache_key]

    def _build_content_slots(self) -> None:
        left_x = spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_LEFT_X
        top_y = spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_TOP_Y
        slot_width, slot_height = spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_SIZE
        right_x = left_x + slot_width + spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_GAP_X

        for row_index, pair in enumerate(self._slot_keys):
            slot_y = top_y + (row_index * slot_height)
            for index_within_row, slot_x in enumerate((left_x, right_x)):
                slot_kind = pair[index_within_row]
                slot = tk.Frame(
                    self.content_area,
                    bg=self._content_bg,
                    bd=0,
                    highlightthickness=0,
                    width=slot_width,
                    height=slot_height,
                )
                slot.place(x=slot_x, y=slot_y)
                slot.pack_propagate(False)
                label = tk.Label(
                    slot,
                    bg=self._content_bg,
                    bd=0,
                    highlightthickness=0,
                )
                label.place(relx=0.5, rely=0.5, anchor='center')
                self._slot_frames.append(slot)
                self._slot_labels.append(label)
                self._slot_kinds.append(slot_kind)
                for widget in (slot, label):
                    widget.bind('<Enter>', lambda event, kind=slot_kind: self._on_slot_enter(kind, event), add='+')
                    widget.bind('<Motion>', lambda event, kind=slot_kind: self._on_slot_motion(kind, event), add='+')
                    widget.bind('<Leave>', lambda _event, kind=slot_kind: self._on_slot_leave(kind), add='+')

    def _build_column_labels(self) -> None:
        left_x = spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_LEFT_X
        right_x = left_x + spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_SIZE[0] + spec.MEDIA_ROW_LIVE_PREVIEW_SLOT_GAP_X
        label_font = (
            spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_FONT_FAMILY,
            spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_FONT_SIZE,
        )
        self.media_label = tk.Label(
            self.content_area,
            text='MEDIA',
            bg=self._content_bg,
            fg=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=label_font,
            anchor='center',
        )
        self.media_label.place(
            x=left_x,
            y=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_Y,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_SIZE[1],
        )
        self.case_label = tk.Label(
            self.content_area,
            text='CASE',
            bg=self._content_bg,
            fg=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=label_font,
            anchor='center',
        )
        self.case_label.place(
            x=right_x,
            y=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_Y,
            width=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_SIZE[0],
            height=spec.MEDIA_ROW_LIVE_PREVIEW_COLUMN_LABEL_SIZE[1],
        )

    def _select_mode(self, mode: str) -> None:
        if mode == self._selected_mode:
            return
        self._selected_mode = mode
        self._apply_state()
        if self._on_mode_selected is not None:
            self._on_mode_selected(self._row_id, mode)

    def _apply_state(self) -> None:
        self.mode_toggle.set_mode(self._selected_mode)
        if self._selected_mode != 'world':
            self._cancel_tooltip_hide()
            self._cursor_tooltip.hide()
        self._restart_dual_phase()
        self._apply_preview_images()

    def _apply_preview_images(self) -> None:
        for row_index, (media_key, container_key) in enumerate(self._slot_keys):
            left_label = self._slot_labels[row_index * 2]
            right_label = self._slot_labels[(row_index * 2) + 1]
            enabled = self._row.enabled_media[media_key]
            left_label.configure(
                image=self._image_for_slot(self._selected_mode, media_key) if enabled else '',
                bg=self._content_bg,
            )
            right_label.configure(
                image=self._image_for_slot(self._selected_mode, container_key) if enabled else '',
                bg=self._content_bg,
            )

    def refresh_content(self) -> None:
        resolved_mode = 'world' if self._row.preview_mode == 'world' else 'inventory'
        if resolved_mode != self._selected_mode:
            self._selected_mode = resolved_mode
        self._apply_state()

    def destroy(self) -> None:
        self._cancel_dual_phase()
        self._cancel_tooltip_hide()
        super().destroy()

    def set_bg_color(self, color: str) -> None:
        self.configure(bg=color)
        self.mode_strip.configure(bg=color)

    def _slot_world_path(self, kind: AppearanceKind) -> str | None:
        if self._resolve_preview_path is None:
            return None
        return self._resolve_preview_path(self._row, kind, 'world', self._dual_phase_show_empty)

    def _restart_dual_phase(self) -> None:
        self._cancel_dual_phase()
        self._dual_phase_show_empty = False
        if not self._has_visible_dual_slots():
            return
        self._dual_phase_after_id = self.after(spec.MODULE_THREE_DUAL_GRID_SWAP_INTERVAL_MS, self._advance_dual_phase)

    def _advance_dual_phase(self) -> None:
        self._dual_phase_after_id = None
        if not self._has_visible_dual_slots():
            self._dual_phase_show_empty = False
            self._apply_preview_images()
            return
        self._dual_phase_show_empty = not self._dual_phase_show_empty
        self._apply_preview_images()
        self._dual_phase_after_id = self.after(spec.MODULE_THREE_DUAL_GRID_SWAP_INTERVAL_MS, self._advance_dual_phase)

    def _cancel_dual_phase(self) -> None:
        if self._dual_phase_after_id is not None:
            try:
                self.after_cancel(self._dual_phase_after_id)
            except tk.TclError:
                pass
            self._dual_phase_after_id = None

    def _has_visible_dual_slots(self) -> bool:
        if self._resolve_preview_path is None:
            return False
        for media_kind, container_kind in self._slot_keys:
            if not self._row.enabled_media.get(media_kind, False):
                continue
            full_path = self._resolve_preview_path(self._row, container_kind, self._selected_mode, False)
            empty_path = self._resolve_preview_path(self._row, container_kind, self._selected_mode, True)
            if empty_path and empty_path != full_path:
                return True
        return False

    def _on_slot_enter(self, kind: AppearanceKind, event: tk.Event) -> None:
        if self._selected_mode != 'world':
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        self._cursor_tooltip.set_image(self._slot_world_path(kind))
        self._cursor_tooltip.show_at_cursor(int(event.x_root), int(event.y_root), direction='left')

    def _on_slot_motion(self, kind: AppearanceKind, event: tk.Event) -> None:
        if self._selected_mode != 'world':
            self._cursor_tooltip.hide()
            return
        self._cancel_tooltip_hide()
        self._cursor_tooltip.set_image(self._slot_world_path(kind))
        self._cursor_tooltip.move_to_cursor(int(event.x_root), int(event.y_root))

    def _on_slot_leave(self, _kind: AppearanceKind) -> None:
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
