from __future__ import annotations

import ctypes
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.main_button import MainButton


class DialogShell(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        icon_path: str | Path | None,
        size: tuple[int, int],
        label_text: str,
        label_wraplength: int,
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=spec.SAMPLE_RATE_DIALOG_BG)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self._window_icon_image: ImageTk.PhotoImage | None = None
        self.protocol('WM_DELETE_WINDOW', self._on_window_close)
        self.bind('<Escape>', lambda _event: self._on_window_close(), add='+')
        self._apply_icon(icon_path)
        self._try_apply_dark_titlebar()

        width, height = size
        parent_window = parent.winfo_toplevel()
        x = parent_window.winfo_rootx() + max(0, (parent_window.winfo_width() - width) // 2)
        y = parent_window.winfo_rooty() + max(0, (parent_window.winfo_height() - height) // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        self.panel = tk.Frame(
            self,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BORDER,
            bd=0,
            highlightthickness=0,
            width=width - 20,
            height=height - 20,
        )
        self.panel.place(x=10, y=10)

        self.panel_inner = tk.Frame(
            self.panel,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            bd=0,
            highlightthickness=0,
            width=(width - 20) - 2,
            height=(height - 20) - 2,
        )
        self.panel_inner.place(x=1, y=1)

        self.label = tk.Label(
            self.panel_inner,
            text=label_text,
            bg=spec.SAMPLE_RATE_DIALOG_PANEL_BG,
            fg=spec.SAMPLE_RATE_DIALOG_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.SAMPLE_RATE_DIALOG_LABEL_FONT_FAMILY, spec.SAMPLE_RATE_DIALOG_LABEL_FONT_SIZE),
            anchor='w',
            justify='left',
            wraplength=label_wraplength,
        )

    def show_modal(self) -> None:
        self.deiconify()
        self.lift()
        self.update_idletasks()
        self.grab_set()
        self.focus_force()

    def close_dialog(self) -> None:
        self._release_grab()
        self.destroy()

    def _on_window_close(self) -> None:
        self.close_dialog()

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
        applied_native = False
        if resolved.suffix.lower() == '.ico':
            try:
                self.iconbitmap(default=str(resolved))
                applied_native = True
            except tk.TclError:
                pass
        try:
            image = Image.open(resolved)
            self._window_icon_image = ImageTk.PhotoImage(image)
            self.iconphoto(True, self._window_icon_image)
            return
        except Exception:
            if applied_native:
                return

    def _try_apply_dark_titlebar(self) -> None:
        if not str(self.tk.call('tk', 'windowingsystem')).startswith('win'):
            return
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass


class ConfirmDialog(DialogShell):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        icon_path: str | Path | None,
        title: str,
        label_text: str,
        accept_text: str,
        cancel_text: str,
    ) -> None:
        super().__init__(
            parent,
            title=title,
            icon_path=icon_path,
            size=spec.CONFIRM_DIALOG_SIZE,
            label_text=label_text,
            label_wraplength=spec.CONFIRM_DIALOG_LABEL_SIZE[0],
        )
        self.result = False
        self.label.place(
            x=spec.CONFIRM_DIALOG_LABEL_POS[0],
            y=spec.CONFIRM_DIALOG_LABEL_POS[1],
            width=spec.CONFIRM_DIALOG_LABEL_SIZE[0],
            height=spec.CONFIRM_DIALOG_LABEL_SIZE[1],
        )

        button_width = spec.MAIN_BUTTON_SIZE[0]
        total_buttons_width = (button_width * 2) + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X
        button_x = ((spec.CONFIRM_DIALOG_SIZE[0] - 20) - total_buttons_width) // 2
        self.accept_button = MainButton(
            self.panel_inner,
            text=accept_text,
            command=self._accept,
            variant='positive',
        )
        self.accept_button.place(x=button_x, y=spec.CONFIRM_DIALOG_BUTTON_Y, width=button_width, height=spec.MAIN_BUTTON_SIZE[1])
        self.cancel_button = MainButton(
            self.panel_inner,
            text=cancel_text,
            command=self._cancel,
            variant='negative',
        )
        self.cancel_button.place(
            x=button_x + button_width + spec.SAMPLE_RATE_DIALOG_BUTTON_GAP_X,
            y=spec.CONFIRM_DIALOG_BUTTON_Y,
            width=button_width,
            height=spec.MAIN_BUTTON_SIZE[1],
        )

    def show(self) -> bool:
        self.show_modal()
        self.wait_window()
        return self.result

    def _accept(self) -> None:
        self.result = True
        self.close_dialog()

    def _cancel(self) -> None:
        self.result = False
        self.close_dialog()

    def _on_window_close(self) -> None:
        self._cancel()
