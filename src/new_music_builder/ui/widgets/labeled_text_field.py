from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.text_edit_bindings import bind_standard_text_shortcuts


class TextField(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        width: int = spec.TYPEABLE_FIELD_SIZE[0],
        height: int = spec.TYPEABLE_FIELD_SIZE[1],
        bg_color: str = spec.TYPEABLE_FIELD_BG,
        outline_color: str = spec.TYPEABLE_FIELD_OUTLINE,
        outline_width: int = spec.TYPEABLE_FIELD_OUTLINE_WIDTH,
        text_color: str = spec.TYPEABLE_FIELD_TEXT_COLOR,
        placeholder_color: str = spec.TYPEABLE_FIELD_PLACEHOLDER_COLOR,
        font_family: str = spec.TYPEABLE_FIELD_FONT_FAMILY,
        font_size: int = spec.TYPEABLE_FIELD_FONT_SIZE,
        placeholder_text: str = '',
        textvariable: tk.StringVar | None = None,
    ) -> None:
        super().__init__(parent, bg=outline_color, bd=0, highlightthickness=0, width=width, height=height)
        self.pack_propagate(False)

        self._bg_color = bg_color
        self._text_color = text_color
        self._placeholder_color = placeholder_color
        self._placeholder_text = placeholder_text
        self._placeholder_visible = False
        self._enabled = True
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

        self.entry = tk.Entry(
            self.inner,
            textvariable=self._variable,
            bg=bg_color,
            fg=text_color,
            insertbackground=text_color,
            relief='flat',
            bd=0,
            highlightthickness=0,
            font=(font_family, font_size),
        )
        self.entry.place(
            x=spec.TYPEABLE_FIELD_TEXT_PAD_X,
            y=0,
            width=max(1, inner_width - (spec.TYPEABLE_FIELD_TEXT_PAD_X * 2)),
            height=inner_height,
        )

        self.entry.bind('<FocusIn>', self._clear_placeholder, add='+')
        self.entry.bind('<FocusOut>', self._restore_placeholder_if_needed, add='+')
        bind_standard_text_shortcuts(self.entry)
        self._restore_placeholder_if_needed()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self.inner.configure(bg=self._bg_color)
            self.entry.configure(
                state='normal',
                bg=self._bg_color,
                disabledbackground=self._bg_color,
                disabledforeground=self._text_color,
            )
            self._restore_placeholder_if_needed()
            return
        disabled_bg = '#4a474c'
        disabled_text = '#a9a5ab'
        self.inner.configure(bg=disabled_bg)
        self.entry.configure(
            state='disabled',
            bg=disabled_bg,
            disabledbackground=disabled_bg,
            disabledforeground=disabled_text,
            insertbackground=disabled_text,
        )

    def _clear_placeholder(self, _event: tk.Event | None = None) -> None:
        if not self._placeholder_visible:
            return
        self.entry.delete(0, 'end')
        self.entry.configure(fg=self._text_color, insertbackground=self._text_color)
        self._placeholder_visible = False

    def _restore_placeholder_if_needed(self, _event: tk.Event | None = None) -> None:
        if not self._placeholder_text:
            self.entry.configure(fg=self._text_color, insertbackground=self._text_color)
            self._placeholder_visible = False
            return
        if self.entry.get():
            self.entry.configure(fg=self._text_color, insertbackground=self._text_color)
            self._placeholder_visible = False
            return
        self.entry.delete(0, 'end')
        self.entry.insert(0, self._placeholder_text)
        self.entry.configure(fg=self._placeholder_color, insertbackground=self._placeholder_color)
        self._placeholder_visible = True

    def get(self) -> str:
        if self._placeholder_visible:
            return ''
        return self.entry.get()

    def set(self, value: str) -> None:
        self._placeholder_visible = False
        self.entry.configure(fg=self._text_color, insertbackground=self._text_color)
        self.entry.delete(0, 'end')
        self.entry.insert(0, value)
        if not value:
            self._restore_placeholder_if_needed()


class LabeledTextField(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        label_text: str = '',
        label_width: int = spec.TYPEABLE_LABEL_SIZE[0],
        label_height: int = spec.TYPEABLE_LABEL_SIZE[1],
        field_width: int = spec.TYPEABLE_FIELD_SIZE[0],
        field_height: int = spec.TYPEABLE_FIELD_SIZE[1],
        label_text_color: str = spec.TYPEABLE_LABEL_TEXT_COLOR,
        label_font_size: int = spec.TYPEABLE_LABEL_FONT_SIZE,
        bg_color: str | None = None,
        placeholder_text: str = '',
        textvariable: tk.StringVar | None = None,
    ) -> None:
        resolved_bg = bg_color if bg_color is not None else parent.cget('bg')
        total_width = label_width + field_width
        total_height = max(label_height, field_height)
        super().__init__(parent, bg=resolved_bg, bd=0, highlightthickness=0, width=total_width, height=total_height)
        self.pack_propagate(False)

        self.label_frame = tk.Frame(
            self,
            bg=resolved_bg,
            bd=0,
            highlightthickness=0,
            width=label_width,
            height=label_height,
        )
        self.label_frame.place(x=0, y=(total_height - label_height) // 2)

        self.label = tk.Label(
            self.label_frame,
            text=label_text,
            bg=resolved_bg,
            fg=label_text_color,
            bd=0,
            highlightthickness=0,
            font=('Orbitron Medium', label_font_size),
            anchor='w',
            justify='left',
        )
        self.label.place(x=0, y=0, width=label_width, height=label_height)

        self.field = TextField(
            self,
            width=field_width,
            height=field_height,
            placeholder_text=placeholder_text,
            textvariable=textvariable,
        )
        self.field.place(x=label_width, y=(total_height - field_height) // 2)

    def set_enabled(self, enabled: bool) -> None:
        self.label.configure(fg=spec.TYPEABLE_LABEL_TEXT_COLOR if enabled else '#8f8a92')
        self.field.set_enabled(enabled)
