from __future__ import annotations

from pathlib import Path
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.dialog_shell import DialogShell
from new_music_builder.ui.widgets.main_button import MainButton


class SampleRateDropdown(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        options: list[tuple[str, int]],
        initial_value: int,
    ) -> None:
        super().__init__(
            parent,
            bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_OUTLINE,
            bd=0,
            highlightthickness=0,
            width=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[0],
            height=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[1],
        )
        self.pack_propagate(False)
        self._choices = options
        self._value = initial_value if any(value == initial_value for _label, value in options) else options[1][1]
        self._menu: tk.Toplevel | None = None
        self._outside_bind_id: str | None = None

        self.inner = tk.Frame(
            self,
            bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_BG,
            bd=0,
            highlightthickness=0,
            width=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[0] - (spec.TYPEABLE_FIELD_OUTLINE_WIDTH * 2),
            height=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[1] - (spec.TYPEABLE_FIELD_OUTLINE_WIDTH * 2),
        )
        self.inner.place(x=spec.TYPEABLE_FIELD_OUTLINE_WIDTH, y=spec.TYPEABLE_FIELD_OUTLINE_WIDTH)

        self.label = tk.Label(
            self.inner,
            text='',
            bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_BG,
            fg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.SAMPLE_RATE_DIALOG_DROPDOWN_FONT_FAMILY, spec.SAMPLE_RATE_DIALOG_DROPDOWN_FONT_SIZE),
            anchor='w',
        )
        self.label.place(
            x=spec.TYPEABLE_FIELD_TEXT_PAD_X,
            y=0,
            width=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[0] - 36,
            height=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[1] - (spec.TYPEABLE_FIELD_OUTLINE_WIDTH * 2),
        )
        self.arrow = tk.Label(
            self.inner,
            text='v',
            bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_BG,
            fg=spec.HEADER_TEXT,
            bd=0,
            highlightthickness=0,
            font=('Orbitron Medium', 8),
            anchor='center',
        )
        self.arrow.place(
            x=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[0] - 26,
            y=0,
            width=20,
            height=spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[1] - (spec.TYPEABLE_FIELD_OUTLINE_WIDTH * 2),
        )
        for widget in (self, self.inner, self.label, self.arrow):
            widget.bind('<ButtonPress-1>', self._toggle_menu, add='+')
        self._refresh_label()

    def get(self) -> int:
        return self._value

    def destroy(self) -> None:
        self._close_menu()
        super().destroy()

    def _refresh_label(self) -> None:
        self.label.configure(text=next(label for label, value in self._choices if value == self._value))

    def _toggle_menu(self, _event: tk.Event | None = None) -> str:
        if self._menu is None:
            self._open_menu()
        else:
            self._close_menu()
        return 'break'

    def _open_menu(self) -> None:
        self._close_menu()
        width = spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[0]
        height = len(self._choices) * spec.SAMPLE_RATE_DIALOG_DROPDOWN_ROW_HEIGHT
        self._menu = tk.Toplevel(self.winfo_toplevel())
        self._menu.overrideredirect(True)
        self._menu.configure(bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_OUTLINE)
        self._menu.geometry(f'{width}x{height}+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}')
        inner = tk.Frame(self._menu, bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_BG, bd=0, highlightthickness=0)
        inner.place(x=1, y=1, width=width - 2, height=height - 2)
        for index, (label, value) in enumerate(self._choices):
            row = tk.Label(
                inner,
                text=label,
                bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_BG,
                fg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_TEXT_COLOR,
                bd=0,
                highlightthickness=0,
                font=(spec.SAMPLE_RATE_DIALOG_DROPDOWN_FONT_FAMILY, spec.SAMPLE_RATE_DIALOG_DROPDOWN_FONT_SIZE),
                anchor='w',
                padx=spec.TYPEABLE_FIELD_TEXT_PAD_X,
            )
            row.place(x=0, y=index * spec.SAMPLE_RATE_DIALOG_DROPDOWN_ROW_HEIGHT, width=width - 2, height=spec.SAMPLE_RATE_DIALOG_DROPDOWN_ROW_HEIGHT)
            row.bind('<Enter>', lambda _e, target=row: target.configure(bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_HOVER_BG), add='+')
            row.bind('<Leave>', lambda _e, target=row: target.configure(bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_BG), add='+')
            row.bind('<ButtonPress-1>', lambda _e, selected=value: self._select_value(selected), add='+')
        self._outside_bind_id = self.winfo_toplevel().bind('<ButtonPress-1>', self._handle_outside_press, add='+')

    def _close_menu(self) -> None:
        if self._menu is not None:
            self._menu.destroy()
            self._menu = None
        if self._outside_bind_id is not None:
            try:
                self.winfo_toplevel().unbind('<ButtonPress-1>', self._outside_bind_id)
            except tk.TclError:
                pass
            self._outside_bind_id = None

    def _select_value(self, value: int) -> str:
        self._value = value
        self._refresh_label()
        self._close_menu()
        return 'break'

    def _handle_outside_press(self, event: tk.Event) -> None:
        widget = event.widget
        current = widget
        while isinstance(current, tk.Misc):
            if current is self or current is self._menu:
                return
            current = current.master
        self._close_menu()


class SampleRateDialog(DialogShell):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        initial_value: int,
    ) -> None:
        super().__init__(
            parent,
            title=spec.SAMPLE_RATE_DIALOG_TITLE,
            icon_path=icon_path,
            size=spec.SAMPLE_RATE_DIALOG_SIZE,
            label_text=spec.SAMPLE_RATE_DIALOG_LABEL_TEXT,
            label_wraplength=spec.SAMPLE_RATE_DIALOG_LABEL_SIZE[0],
        )
        self.result: int | None = None
        self.label.place(
            x=spec.SAMPLE_RATE_DIALOG_LABEL_POS[0],
            y=spec.SAMPLE_RATE_DIALOG_LABEL_POS[1],
            width=spec.SAMPLE_RATE_DIALOG_LABEL_SIZE[0],
            height=spec.SAMPLE_RATE_DIALOG_LABEL_SIZE[1],
        )

        self.dropdown = SampleRateDropdown(
            self.panel_inner,
            options=[
                ('32000 Hz', 32000),
                ('44100 Hz', 44100),
                ('48000 Hz', 48000),
            ],
            initial_value=initial_value,
        )
        self.dropdown.place(
            x=spec.SAMPLE_RATE_DIALOG_DROPDOWN_POS[0],
            y=spec.SAMPLE_RATE_DIALOG_DROPDOWN_POS[1],
        )

        button_width = spec.MAIN_BUTTON_SIZE[0]
        total_buttons_width = (button_width * 2) + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X
        button_x = ((spec.SAMPLE_RATE_DIALOG_SIZE[0] - 20) - total_buttons_width) // 2
        self.ok_button = MainButton(self.panel_inner, text='OK', command=self._accept, variant='positive')
        self.ok_button.place(x=button_x, y=spec.SAMPLE_RATE_DIALOG_BUTTON_Y, width=button_width, height=spec.MAIN_BUTTON_SIZE[1])
        self.cancel_button = MainButton(self.panel_inner, text='CANCEL', command=self._cancel, variant='negative')
        self.cancel_button.place(
            x=button_x + button_width + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X,
            y=spec.SAMPLE_RATE_DIALOG_BUTTON_Y,
            width=button_width,
            height=spec.MAIN_BUTTON_SIZE[1],
        )

    def show(self) -> int | None:
        self.show_modal()
        self.wait_window()
        return self.result

    def _accept(self) -> None:
        self.result = self.dropdown.get()
        self.close_dialog()

    def _cancel(self) -> None:
        self.result = None
        self.close_dialog()

    def _on_window_close(self) -> None:
        self._cancel()
