from __future__ import annotations

from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.main_button import MainButton


class _SampleRateDropdown(tk.Frame):
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
        self._options = options
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
        self.label.configure(text=next(label for label, value in self._options if value == self._value))

    def _toggle_menu(self, _event: tk.Event | None = None) -> str:
        if self._menu is None:
            self._open_menu()
        else:
            self._close_menu()
        return 'break'

    def _open_menu(self) -> None:
        self._close_menu()
        width = spec.SAMPLE_RATE_DIALOG_DROPDOWN_SIZE[0]
        height = len(self._options) * spec.SAMPLE_RATE_DIALOG_DROPDOWN_ROW_HEIGHT
        self._menu = tk.Toplevel(self.winfo_toplevel())
        self._menu.overrideredirect(True)
        self._menu.configure(bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_OUTLINE)
        self._menu.geometry(f'{width}x{height}+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}')
        inner = tk.Frame(self._menu, bg=spec.SAMPLE_RATE_DIALOG_DROPDOWN_BG, bd=0, highlightthickness=0)
        inner.place(x=1, y=1, width=width - 2, height=height - 2)
        for index, (label, value) in enumerate(self._options):
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


class SampleRateDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        initial_value: int,
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.title(spec.SAMPLE_RATE_DIALOG_TITLE)
        self.configure(bg=spec.SAMPLE_RATE_DIALOG_BG)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.result: int | None = None
        self._window_icon_image: ImageTk.PhotoImage | None = None
        self.protocol('WM_DELETE_WINDOW', self._cancel)
        self.bind('<Escape>', lambda _event: self._cancel(), add='+')
        self._apply_icon(icon_path)

        width, height = spec.SAMPLE_RATE_DIALOG_SIZE
        parent_window = parent.winfo_toplevel()
        x = parent_window.winfo_rootx() + max(0, (parent_window.winfo_width() - width) // 2)
        y = parent_window.winfo_rooty() + max(0, (parent_window.winfo_height() - height) // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        panel = tk.Frame(
            self,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BORDER,
            bd=0,
            highlightthickness=0,
            width=width - 20,
            height=height - 20,
        )
        panel.place(x=10, y=10)
        panel_inner = tk.Frame(
            panel,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            bd=0,
            highlightthickness=0,
            width=(width - 20) - 2,
            height=(height - 20) - 2,
        )
        panel_inner.place(x=1, y=1)

        self.label = tk.Label(
            panel_inner,
            text=spec.SAMPLE_RATE_DIALOG_LABEL_TEXT,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.SAMPLE_RATE_DIALOG_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.SAMPLE_RATE_DIALOG_LABEL_FONT_FAMILY, spec.SAMPLE_RATE_DIALOG_LABEL_FONT_SIZE),
            anchor='w',
        )
        self.label.place(x=30, y=20, width=300, height=20)

        self.dropdown = _SampleRateDropdown(
            panel_inner,
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
        button_x = ((width - 20) - total_buttons_width) // 2
        self.ok_button = MainButton(panel_inner, text='OK', command=self._accept, variant='positive')
        self.ok_button.place(x=button_x, y=spec.SAMPLE_RATE_DIALOG_BUTTON_Y, width=button_width, height=spec.MAIN_BUTTON_SIZE[1])
        self.cancel_button = MainButton(panel_inner, text='CANCEL', command=self._cancel, variant='positive')
        self.cancel_button.place(
            x=button_x + button_width + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X,
            y=spec.SAMPLE_RATE_DIALOG_BUTTON_Y,
            width=button_width,
            height=spec.MAIN_BUTTON_SIZE[1],
        )

    def show(self) -> int | None:
        self.deiconify()
        self.lift()
        self.update_idletasks()
        self.grab_set()
        self.focus_force()
        self.wait_window()
        return self.result

    def _accept(self) -> None:
        self.result = self.dropdown.get()
        self._release_grab()
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self._release_grab()
        self.destroy()

    def _release_grab(self) -> None:
        try:
            if self.grab_current() is self:
                self.grab_release()
        except tk.TclError:
            pass

    def _apply_icon(self, icon_path: str | Path | None) -> None:
        if icon_path is None:
            return
        resolved = Path(icon_path)
        if not resolved.exists():
            return
        if resolved.suffix.lower() == '.ico':
            try:
                self.iconbitmap(default=str(resolved))
                return
            except tk.TclError:
                pass
        try:
            image = Image.open(resolved)
            self._window_icon_image = ImageTk.PhotoImage(image)
            self.iconphoto(True, self._window_icon_image)
        except Exception:
            pass
