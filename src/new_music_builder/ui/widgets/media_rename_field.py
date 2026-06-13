from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont

from new_music_builder.domain.models import MediaRow
from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage


def canonical_media_name(row_id: int, value: str) -> str:
    trimmed = value.strip()
    default_name = f'Media Mix {row_id}'
    legacy_default = f'Media Row {row_id}'
    if not trimmed or trimmed == legacy_default:
        return default_name
    return trimmed


class EditIconButton(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        command: Callable[[], None] | None = None,
        size: tuple[int, int] = spec.MEDIA_ROW_RENAME_EDIT_BUTTON_SIZE,
        bg_color: str = spec.MEDIA_ROW_RENAME_BG,
        hover_bg_color: str = spec.MEDIA_ROW_RENAME_EDIT_HOVER_BG,
        pressed_bg_color: str = spec.MEDIA_ROW_RENAME_EDIT_PRESSED_BG,
    ) -> None:
        super().__init__(
            parent,
            width=size[0],
            height=size[1],
            bg=bg_color,
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._bg_color = bg_color
        self._hover_bg_color = hover_bg_color
        self._pressed_bg_color = pressed_bg_color
        self._command = command
        self._is_pressed = False
        self._image = load_tk_photoimage(icon_path, size)
        self._fill_id = self.create_rectangle(0, 0, size[0], size[1], outline='', fill=bg_color)
        self._icon_id: int | None = None
        if self._image is not None:
            self._icon_id = self.create_image(size[0] // 2, size[1] // 2, image=self._image)
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')
        self.bind('<Double-Button-1>', self._break_event, add='+')

    def _set_fill(self, color: str) -> None:
        self.itemconfigure(self._fill_id, fill=color)
        self.configure(bg=color)

    def _on_enter(self, _event: tk.Event | None = None) -> str:
        if not self._is_pressed:
            self._set_fill(self._hover_bg_color)
        return 'break'

    def _on_leave(self, _event: tk.Event | None = None) -> str:
        self._is_pressed = False
        self._set_fill(self._bg_color)
        return 'break'

    def _on_press(self, _event: tk.Event | None = None) -> str:
        self._is_pressed = True
        self._set_fill(self._pressed_bg_color)
        return 'break'

    def _on_release(self, event: tk.Event | None = None) -> str:
        if self._is_pressed:
            self._is_pressed = False
            inside = event is not None and 0 <= event.x <= self._size[0] and 0 <= event.y <= self._size[1]
            self._set_fill(self._hover_bg_color if inside else self._bg_color)
            if inside and self._command is not None:
                self._command()
        return 'break'

    def _break_event(self, _event: tk.Event | None = None) -> str:
        return 'break'


class MediaRenameField(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        row: MediaRow,
        edit_icon_path: str | Path | None,
        bg_color: str = spec.MEDIA_ROW_RENAME_BG,
        on_name_committed: Callable[[int, str], None] | None = None,
    ) -> None:
        super().__init__(
            parent,
            bg=spec.MEDIA_ROW_RENAME_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.MEDIA_ROW_RENAME_SIZE[0],
            height=spec.MEDIA_ROW_RENAME_SIZE[1],
        )
        self.pack_propagate(False)
        self._row = row
        self._bg_color = bg_color
        self._on_name_committed = on_name_committed
        self._font = tkfont.Font(family=spec.MEDIA_ROW_RENAME_FONT_FAMILY, size=spec.MEDIA_ROW_RENAME_FONT_SIZE)
        self._display_name = canonical_media_name(row.row_id, row.media_name)
        self._pre_edit_name = self._display_name
        self._editing = False
        self._outside_click_binding_id: str | None = None
        self._text_area_width = spec.MEDIA_ROW_RENAME_SIZE[0] - (spec.MEDIA_ROW_RENAME_OUTLINE_WIDTH * 2) - spec.MEDIA_ROW_RENAME_EDIT_BUTTON_SIZE[0]
        self._text_width_limit = (
            spec.MEDIA_ROW_RENAME_SIZE[0]
            - spec.MEDIA_ROW_RENAME_EDIT_BUTTON_SIZE[0]
            - (spec.MEDIA_ROW_RENAME_TEXT_PAD_X * 2)
        )
        self._last_valid_entry_value = self._display_name

        inner_width = spec.MEDIA_ROW_RENAME_SIZE[0] - (spec.MEDIA_ROW_RENAME_OUTLINE_WIDTH * 2)
        inner_height = spec.MEDIA_ROW_RENAME_SIZE[1] - (spec.MEDIA_ROW_RENAME_OUTLINE_WIDTH * 2)
        self.surface = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=inner_width,
            height=inner_height,
        )
        self.surface.place(x=spec.MEDIA_ROW_RENAME_OUTLINE_WIDTH, y=spec.MEDIA_ROW_RENAME_OUTLINE_WIDTH)
        self.surface.pack_propagate(False)

        self.text_area = tk.Frame(
            self.surface,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=self._text_area_width,
            height=inner_height,
        )
        self.text_area.place(x=0, y=0)
        self.text_area.pack_propagate(False)

        self.display_label = tk.Label(
            self.text_area,
            text=self._display_name,
            bg=bg_color,
            fg=spec.MEDIA_ROW_RENAME_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=self._font,
            anchor='w',
            justify='left',
        )
        self.display_label.place(
            x=spec.MEDIA_ROW_RENAME_TEXT_PAD_X,
            y=0,
            width=max(1, self._text_area_width - (spec.MEDIA_ROW_RENAME_TEXT_PAD_X * 2)),
            height=inner_height,
        )

        self._entry_var = tk.StringVar(value=self._display_name)
        self.entry = tk.Entry(
            self.text_area,
            textvariable=self._entry_var,
            bg=bg_color,
            fg=spec.MEDIA_ROW_RENAME_TEXT_COLOR,
            insertbackground=spec.MEDIA_ROW_RENAME_TEXT_COLOR,
            relief='flat',
            bd=0,
            highlightthickness=0,
            font=self._font,
        )
        self.entry.place(
            x=spec.MEDIA_ROW_RENAME_TEXT_PAD_X,
            y=0,
            width=max(1, self._text_area_width - (spec.MEDIA_ROW_RENAME_TEXT_PAD_X * 2)),
            height=inner_height,
        )
        self.entry.place_forget()
        self.entry.configure(insertontime=spec.MEDIA_ROW_RENAME_CURSOR_BLINK_MS, insertofftime=spec.MEDIA_ROW_RENAME_CURSOR_BLINK_MS)
        self.entry.bind('<Return>', self._commit_from_event, add='+')
        self.entry.bind('<Escape>', self._cancel_from_event, add='+')
        self.entry.bind('<FocusOut>', self._on_focus_out, add='+')
        self.entry.bind('<KeyPress>', self._on_entry_keypress, add='+')
        self.entry.bind('<<Paste>>', self._break_event, add='+')
        self.entry.bind('<ButtonRelease-1>', self._break_event, add='+')
        self.entry.bind('<Double-Button-1>', self._break_event, add='+')
        self._entry_var.trace_add('write', self._on_entry_var_changed)

        self.edit_button = EditIconButton(
            self.surface,
            icon_path=edit_icon_path,
            command=self._on_edit_button,
            bg_color=bg_color,
        )
        self.edit_button.place(x=self._text_area_width, y=0)

        for widget in (self, self.surface, self.text_area, self.display_label):
            widget.bind('<ButtonPress-1>', self._break_event, add='+')
            widget.bind('<ButtonRelease-1>', self._break_event, add='+')
            widget.bind('<Double-Button-1>', self._on_text_double_click, add='+')

    def _on_text_double_click(self, _event: tk.Event | None = None) -> str:
        self._enter_edit_mode()
        return 'break'

    def _on_edit_button(self) -> None:
        if self._editing:
            self._commit_name()
            return
        self._enter_edit_mode()

    def _enter_edit_mode(self) -> None:
        if self._editing:
            return
        self._editing = True
        self._install_outside_click_binding()
        self._pre_edit_name = self._display_name
        self._entry_var.set(self._display_name)
        self._last_valid_entry_value = self._display_name
        self.display_label.place_forget()
        self.entry.place(
            x=spec.MEDIA_ROW_RENAME_TEXT_PAD_X,
            y=0,
            width=max(1, self._text_area_width - (spec.MEDIA_ROW_RENAME_TEXT_PAD_X * 2)),
            height=self.text_area.winfo_height(),
        )
        self.entry.focus_set()
        self.entry.icursor('end')

    def _exit_edit_mode(self) -> None:
        if not self._editing:
            return
        self._editing = False
        self._remove_outside_click_binding()
        self.entry.place_forget()
        self.display_label.configure(text=self._display_name)
        self.display_label.place(
            x=spec.MEDIA_ROW_RENAME_TEXT_PAD_X,
            y=0,
            width=max(1, self._text_area_width - (spec.MEDIA_ROW_RENAME_TEXT_PAD_X * 2)),
            height=self.text_area.winfo_height(),
        )

    def _commit_name(self) -> None:
        committed_name = canonical_media_name(self._row.row_id, self._entry_var.get())
        self._display_name = committed_name
        self._entry_var.set(committed_name)
        self._exit_edit_mode()
        if self._on_name_committed is not None:
            self._on_name_committed(self._row.row_id, committed_name)

    def _commit_from_event(self, _event: tk.Event | None = None) -> str:
        self._commit_name()
        return 'break'

    def _cancel_from_event(self, _event: tk.Event | None = None) -> str:
        self._display_name = self._pre_edit_name
        self._entry_var.set(self._pre_edit_name)
        self._exit_edit_mode()
        return 'break'

    def _on_entry_keypress(self, event: tk.Event) -> str | None:
        if event.keysym in {'Return', 'Escape', 'BackSpace', 'Delete', 'Left', 'Right', 'Home', 'End', 'Tab'}:
            return 'break' if event.keysym == 'Tab' else None
        if len(event.char) != 1:
            return None
        selection = self.entry.selection_present()
        start = self.entry.index('sel.first') if selection else self.entry.index('insert')
        end = self.entry.index('sel.last') if selection else self.entry.index('insert')
        current = self._entry_var.get()
        proposed = current[:start] + event.char + current[end:]
        if self._font.measure(proposed) > self._text_width_limit:
            return 'break'
        return None

    def _on_entry_var_changed(self, *_args: object) -> None:
        if not self._editing:
            return
        current = self._entry_var.get()
        if self._font.measure(current) <= self._text_width_limit:
            self._last_valid_entry_value = current
            return
        self._entry_var.set(self._last_valid_entry_value)

    def _on_focus_out(self, _event: tk.Event | None = None) -> None:
        self.after_idle(self._commit_if_focus_left_widget)

    def _commit_if_focus_left_widget(self) -> None:
        if not self._editing:
            return
        focused_widget = self.focus_get()
        if self._is_widget_within_self(focused_widget):
            return
        self._commit_name()

    def _install_outside_click_binding(self) -> None:
        if self._outside_click_binding_id is not None:
            return
        toplevel = self.winfo_toplevel()
        self._outside_click_binding_id = toplevel.bind('<ButtonPress-1>', self._on_toplevel_button_press, add='+')

    def _remove_outside_click_binding(self) -> None:
        if self._outside_click_binding_id is None:
            return
        toplevel = self.winfo_toplevel()
        toplevel.unbind('<ButtonPress-1>', self._outside_click_binding_id)
        self._outside_click_binding_id = None

    def _on_toplevel_button_press(self, event: tk.Event) -> None:
        if not self._editing:
            return
        clicked_widget = getattr(event, 'widget', None)
        if self._is_widget_within_self(clicked_widget):
            return
        self._commit_name()

    def _is_widget_within_self(self, widget: tk.Misc | None) -> bool:
        current = widget
        while current is not None:
            if current is self:
                return True
            current = current.master
        return False

    def destroy(self) -> None:
        self._remove_outside_click_binding()
        super().destroy()

    def _break_event(self, _event: tk.Event | None = None) -> str:
        return 'break'
