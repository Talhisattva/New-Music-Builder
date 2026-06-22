from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

from new_music_builder.ui import spec


@dataclass(slots=True)
class MenuAction:
    label: str
    command: Callable[[], None]
    shortcut_label: str = ""


def measure_menu_action_width(
    action: MenuAction,
    *,
    label_measure: Callable[[str], int],
    accelerator_measure: Callable[[str], int],
) -> int:
    width = label_measure(action.label)
    if action.shortcut_label:
        width += spec.MENU_DROPDOWN_INLINE_GAP_X + accelerator_measure(action.shortcut_label)
    return width


class _DropdownItem(ctk.CTkFrame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        text: str,
        width: int,
        command: Callable[[], None],
        bg_color: str,
        hover_color: str,
        text_color: str,
        font: ctk.CTkFont,
        accelerator_text: str = "",
        accelerator_color: str = spec.MENU_DROPDOWN_ACCELERATOR_COLOR,
        accelerator_font: ctk.CTkFont | None = None,
        enabled_getter: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(
            parent,
            fg_color=bg_color,
            corner_radius=0,
            width=width,
            height=spec.MENU_DROPDOWN_ROW_HEIGHT,
        )
        self.pack_propagate(False)
        self._default_bg = bg_color
        self._hover_bg = hover_color
        self._command = command
        self._enabled_getter = enabled_getter
        self._text_color = text_color
        self._disabled_text_color = '#8f8a92'
        self._accelerator_color = accelerator_color
        self._accelerator_font = accelerator_font or font
        self._content = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
        )
        self._content.pack(fill='both', expand=True, padx=spec.MENU_DROPDOWN_PAD_X, pady=0)
        self.label = ctk.CTkLabel(
            self._content,
            text=text,
            text_color=text_color,
            font=font,
        )
        self.label.pack(side='left', pady=0)
        self.accelerator_label: tk.Label | None = None
        if accelerator_text:
            self.accelerator_label = tk.Label(
                self._content,
                text=accelerator_text,
                bg=bg_color,
                fg=accelerator_color,
                bd=0,
                highlightthickness=0,
                font=(self._accelerator_font.cget('family'), self._accelerator_font.cget('size')),
                anchor='w',
                justify='left',
            )
            self.accelerator_label.pack(side='left', padx=(spec.MENU_DROPDOWN_INLINE_GAP_X, 0), pady=0)
        widgets = [self, self._content, self.label]
        if self.accelerator_label is not None:
            widgets.append(self.accelerator_label)
        for widget in widgets:
            widget.bind('<Enter>', self._on_enter, add='+')
            widget.bind('<Leave>', self._on_leave, add='+')
            widget.bind('<ButtonPress-1>', self._on_press, add='+')
        self._apply_enabled_state()
        self._set_visual_bg(bg_color)

    def _enabled(self) -> bool:
        return self._enabled_getter() if self._enabled_getter is not None else True

    def _apply_enabled_state(self) -> None:
        self.label.configure(text_color=self._text_color if self._enabled() else self._disabled_text_color)
        if self.accelerator_label is not None:
            self.accelerator_label.configure(fg=self._accelerator_color if self._enabled() else self._disabled_text_color)

    def _set_visual_bg(self, color: str) -> None:
        self.configure(fg_color=color)
        self._content.configure(bg=color)
        if self.accelerator_label is not None:
            self.accelerator_label.configure(bg=color)

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        if not self._enabled():
            self._set_visual_bg(self._default_bg)
            return
        self._set_visual_bg(self._hover_bg)

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._set_visual_bg(self._default_bg)

    def _on_press(self, _event: tk.Event | None = None) -> str:
        if not self._enabled():
            return 'break'
        self._command()
        return 'break'


class _DropdownMenu(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        items: list[MenuAction],
        width: int,
        text_color: str,
        bg_color: str,
        hover_color: str,
        font: ctk.CTkFont,
        accelerator_font: ctk.CTkFont,
        enabled_getter: Callable[[str], bool] | None = None,
    ) -> None:
        border_width = spec.MENU_DROPDOWN_BORDER_WIDTH
        super().__init__(
            parent,
            bg=spec.MENU_DROPDOWN_BORDER_COLOR,
            bd=0,
            highlightthickness=0,
            width=width,
            height=(len(items) * spec.MENU_DROPDOWN_ROW_HEIGHT) + (border_width * 2),
        )
        self.pack_propagate(False)
        self.content = tk.Frame(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=width - (border_width * 2),
            height=len(items) * spec.MENU_DROPDOWN_ROW_HEIGHT,
        )
        self.content.place(x=border_width, y=border_width)
        for index, item in enumerate(items):
            menu_item = _DropdownItem(
                self.content,
                text=item.label,
                width=width - (border_width * 2),
                command=item.command,
                bg_color=bg_color,
                hover_color=hover_color,
                text_color=text_color,
                font=font,
                accelerator_text=item.shortcut_label,
                accelerator_font=accelerator_font,
                enabled_getter=(lambda label=item.label: enabled_getter(label)) if enabled_getter is not None else None,
            )
            menu_item.place(
                x=0,
                y=index * spec.MENU_DROPDOWN_ROW_HEIGHT,
            )


class MenuStrip(ctk.CTkFrame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        items: tuple[str, ...] = spec.MENU_ITEMS,
        menu_actions: dict[str, list[MenuAction]] | None = None,
        bg_color: str = spec.MENU_BG,
        hover_color: str = spec.MENU_HOVER,
        text_color: str = spec.HEADER_TEXT,
    ) -> None:
        super().__init__(parent, fg_color=bg_color, corner_radius=0, height=spec.MENU_HEIGHT)
        self.pack_propagate(False)
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._text_color = text_color
        self._menu_actions = menu_actions or {}
        self._action_enabled: dict[tuple[str, str], bool] = {}
        self._item_widgets: dict[str, tuple[ctk.CTkFrame, ctk.CTkLabel]] = {}
        self._open_menu_name: str | None = None
        self._dropdown: _DropdownMenu | None = None
        self._global_bind_active = False
        self._toplevel_press_bind_id: str | None = None
        self._toplevel_escape_bind_id: str | None = None
        self._top_font = ctk.CTkFont(family='Orbitron', size=spec.MENU_FONT_SIZE, weight='normal')
        self._measure_font = tkfont.Font(family='Orbitron', size=spec.MENU_FONT_SIZE, weight='normal')
        self._accelerator_font = ctk.CTkFont(family='Perfect DOS VGA 437 Win', size=spec.MENU_ACCELERATOR_FONT_SIZE)
        self._accelerator_measure_font = tkfont.Font(family='Perfect DOS VGA 437 Win', size=spec.MENU_ACCELERATOR_FONT_SIZE)

        items_frame = ctk.CTkFrame(self, fg_color='transparent')
        items_frame.pack(side='left')

        for item in items:
            item_frame = ctk.CTkFrame(items_frame, fg_color=bg_color, corner_radius=0)
            item_frame.pack(side='left', padx=0, pady=0)
            label = ctk.CTkLabel(
                item_frame,
                text=item,
                text_color=text_color,
                font=self._top_font,
                fg_color='transparent',
            )
            label.pack(padx=spec.MENU_ITEM_PAD_X, pady=spec.MENU_ITEM_PAD_Y)
            for widget in (item_frame, label):
                widget.bind('<Enter>', lambda _e, name=item: self._handle_top_enter(name), add='+')
                widget.bind('<Leave>', lambda _e, name=item: self._handle_top_leave(name), add='+')
                widget.bind('<ButtonPress-1>', lambda _e, name=item: self._handle_top_press(name), add='+')
            self._item_widgets[item] = (item_frame, label)

    def destroy(self) -> None:
        self.close_menu()
        super().destroy()

    def close_menu(self) -> None:
        if self._dropdown is not None:
            self._dropdown.place_forget()
            self._dropdown.destroy()
            self._dropdown = None
        if self._open_menu_name is not None:
            self._set_top_bg(self._open_menu_name, self._bg_color)
        self._open_menu_name = None
        self._unbind_global_handlers()

    def _handle_top_enter(self, menu_name: str) -> None:
        if self._open_menu_name is not None:
            self._open_dropdown(menu_name)
            return
        self._set_top_bg(menu_name, self._hover_color)

    def _handle_top_leave(self, menu_name: str) -> None:
        if self._open_menu_name == menu_name:
            return
        self._set_top_bg(menu_name, self._bg_color)

    def _handle_top_press(self, menu_name: str) -> str:
        if self._open_menu_name == menu_name:
            self.close_menu()
        else:
            self._open_dropdown(menu_name)
        return 'break'

    def _open_dropdown(self, menu_name: str) -> None:
        actions = self._menu_actions.get(menu_name, [])
        if not actions:
            self.close_menu()
            return
        if self._open_menu_name is not None and self._open_menu_name != menu_name:
            self._set_top_bg(self._open_menu_name, self._bg_color)
        self._open_menu_name = menu_name
        self._set_top_bg(menu_name, self._hover_color)

        dropdown_width = self._dropdown_width_for_actions(actions)
        if self._dropdown is not None:
            self._dropdown.destroy()
        self._dropdown = _DropdownMenu(
            self.winfo_toplevel(),
            items=[
                MenuAction(
                    label=item.label,
                    command=lambda action=item.command, label=item.label, name=menu_name: self._run_action(name, label, action),
                    shortcut_label=item.shortcut_label,
                )
                for item in actions
            ],
            width=dropdown_width,
            text_color=self._text_color,
            bg_color=spec.MENU_DROPDOWN_BG,
            hover_color=spec.MENU_DROPDOWN_HOVER_BG,
            font=self._top_font,
            accelerator_font=self._accelerator_font,
            enabled_getter=lambda label: self.is_action_enabled(menu_name, label),
        )
        x, y = self._dropdown_position(menu_name)
        self._dropdown.place(x=x, y=y)
        self._dropdown.lift()
        self._bind_global_handlers()

    def _run_action(self, menu_name: str, item_label: str, command: Callable[[], None]) -> None:
        if not self.is_action_enabled(menu_name, item_label):
            self.close_menu()
            return
        self.close_menu()
        command()

    def is_action_enabled(self, menu_name: str, item_label: str) -> bool:
        return self._action_enabled.get((menu_name, item_label), True)

    def set_action_enabled(self, menu_name: str, item_label: str, enabled: bool) -> None:
        self._action_enabled[(menu_name, item_label)] = enabled

    def _dropdown_width_for_actions(self, actions: list[MenuAction]) -> int:
        widest_text = 0
        for action in actions:
            width = measure_menu_action_width(
                action,
                label_measure=self._measure_font.measure,
                accelerator_measure=self._accelerator_measure_font.measure,
            )
            widest_text = max(widest_text, width)
        return widest_text + (spec.MENU_DROPDOWN_PAD_X * 2) + (spec.MENU_DROPDOWN_BORDER_WIDTH * 2)

    def _dropdown_position(self, menu_name: str) -> tuple[int, int]:
        item_frame, _label = self._item_widgets[menu_name]
        root_x = self.winfo_toplevel().winfo_rootx()
        root_y = self.winfo_toplevel().winfo_rooty()
        x = item_frame.winfo_rootx() - root_x
        y = self.winfo_rooty() - root_y + self.winfo_height()
        return x, y

    def _set_top_bg(self, menu_name: str, color: str) -> None:
        item_frame, _label = self._item_widgets[menu_name]
        item_frame.configure(fg_color=color)

    def _bind_global_handlers(self) -> None:
        if self._global_bind_active:
            return
        toplevel = self.winfo_toplevel()
        self._toplevel_press_bind_id = toplevel.bind('<ButtonPress-1>', self._handle_global_press, add='+')
        self._toplevel_escape_bind_id = toplevel.bind('<Escape>', self._handle_escape, add='+')
        self._global_bind_active = True

    def _unbind_global_handlers(self) -> None:
        if not self._global_bind_active:
            return
        toplevel = self.winfo_toplevel()
        try:
            if self._toplevel_press_bind_id is not None:
                toplevel.unbind('<ButtonPress-1>', self._toplevel_press_bind_id)
            if self._toplevel_escape_bind_id is not None:
                toplevel.unbind('<Escape>', self._toplevel_escape_bind_id)
        except tk.TclError:
            pass
        self._toplevel_press_bind_id = None
        self._toplevel_escape_bind_id = None
        self._global_bind_active = False

    def _handle_global_press(self, event: tk.Event) -> None:
        if self._belongs_to_menu(event.widget):
            return
        self.close_menu()

    def _handle_escape(self, _event: tk.Event | None = None) -> str:
        self.close_menu()
        return 'break'

    def _belongs_to_menu(self, widget: object) -> bool:
        current = widget
        while isinstance(current, tk.Misc):
            if current is self or current is self._dropdown:
                return True
            if current in {frame for frame, _label in self._item_widgets.values()}:
                return True
            if current in {label for _frame, label in self._item_widgets.values()}:
                return True
            current = current.master
        return False
