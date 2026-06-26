from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.images import load_tk_photoimage_contained


class _SelectorBox(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        command: Callable[[], None],
        caption: str = '',
    ) -> None:
        super().__init__(
            parent,
            width=spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[0],
            height=spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[1],
            bg=spec.MODULE_THREE_CUSTOM_ROW_BG,
            bd=0,
            highlightthickness=0,
        )
        self._command = command
        self._caption = caption
        self._preview_path = ''
        self._preview_image = None
        self._plus_color = spec.MODULE_THREE_CUSTOM_SELECTOR_PLUS_COLOR
        self._hovered = False
        self._pressed = False
        self._enabled = True
        self._bind_events()
        self._redraw()

    def set_background_color(self, color: str) -> None:
        self.configure(bg=color)

    def set_preview_path(self, path: str) -> None:
        self._preview_path = path
        self._preview_image = load_tk_photoimage_contained(path, spec.MODULE_THREE_CUSTOM_SELECTOR_PREVIEW_SIZE) if path else None
        self._redraw()

    def _bind_events(self) -> None:
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _set_plus_color(self) -> None:
        if self._pressed:
            self._plus_color = spec.MODULE_THREE_CUSTOM_SELECTOR_PLUS_PRESSED_COLOR
        elif self._hovered:
            self._plus_color = spec.MODULE_THREE_CUSTOM_SELECTOR_PLUS_HOVER_COLOR
        else:
            self._plus_color = spec.MODULE_THREE_CUSTOM_SELECTOR_PLUS_COLOR

    def _redraw(self) -> None:
        self.delete('all')
        inset = 1
        width, height = spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE
        border_color = spec.MODULE_THREE_CUSTOM_SELECTOR_BORDER_COLOR if self._enabled else spec.MODULE_THREE_CUSTOM_SELECTOR_DISABLED_BORDER_COLOR
        self.create_rectangle(
            inset,
            inset,
            width - inset,
            height - inset,
            outline=border_color,
            width=1,
            dash=spec.MODULE_THREE_CUSTOM_SELECTOR_DASH_PATTERN,
        )
        if self._preview_image is not None:
            self.create_image(width // 2, height // 2, image=self._preview_image)
        elif self._enabled:
            self._set_plus_color()
            _plus_width, plus_height = spec.MODULE_THREE_CUSTOM_SELECTOR_PLUS_SIZE
            bar_width = spec.MODULE_THREE_CUSTOM_SELECTOR_PLUS_THICKNESS
            center_x = (width - 1) / 2
            center_y = (height - 1) / 2
            half_bar = bar_width / 2
            half_length = plus_height / 2
            self.create_rectangle(
                center_x - half_bar,
                center_y - half_length,
                center_x + half_bar,
                center_y + half_length,
                outline='',
                fill=self._plus_color,
            )
            self.create_rectangle(
                center_x - half_length,
                center_y - half_bar,
                center_x + half_length,
                center_y + half_bar,
                outline='',
                fill=self._plus_color,
            )
        if self._caption:
            self.create_text(
                (width - 1) / 2,
                spec.MODULE_THREE_CUSTOM_SELECTOR_CAPTION_Y,
                text=self._caption,
                fill=spec.MODULE_THREE_CUSTOM_DISABLED_TEXT_COLOR if not self._enabled else spec.MODULE_THREE_CUSTOM_SELECTOR_CAPTION_COLOR,
                font=(spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_FONT_FAMILY, spec.MODULE_THREE_CUSTOM_SELECTOR_CAPTION_FONT_SIZE),
                anchor='center',
            )

    def _on_enter(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._hovered = True
        if not self._preview_path:
            self._redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._hovered = False
        self._pressed = False
        if not self._preview_path:
            self._redraw()

    def _on_press(self, _event: tk.Event) -> str:
        if not self._enabled:
            return 'break'
        self._pressed = True
        if not self._preview_path:
            self._redraw()
        return 'break'

    def _on_release(self, event: tk.Event) -> str:
        if not self._enabled:
            return 'break'
        inside = 0 <= event.x < spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[0] and 0 <= event.y < spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[1]
        was_pressed = self._pressed
        self._pressed = False
        if not self._preview_path:
            self._redraw()
        if inside and was_pressed:
            self._command()
        return 'break'

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._hovered = False
        self._pressed = False
        self._redraw()


class _VerticalStrip(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int],
        text: str,
        default_bg: str,
        hover_bg: str,
        pressed_bg: str,
        text_color: str,
        font: tuple[str, int],
        command: Callable[[], None],
        enabled_getter: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(
            parent,
            width=size[0],
            height=size[1],
            bg=default_bg,
            bd=0,
            highlightthickness=0,
        )
        self._size = size
        self._text = text
        self._default_bg = default_bg
        self._hover_bg = hover_bg
        self._pressed_bg = pressed_bg
        self._text_color = text_color
        self._font = font
        self._command = command
        self._enabled_getter = enabled_getter
        self._forced_enabled = True
        self._hovered = False
        self._pressed = False
        self._bind_events()
        self._redraw()

    def _bind_events(self) -> None:
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')
        self.bind('<ButtonPress-1>', self._on_press, add='+')
        self.bind('<ButtonRelease-1>', self._on_release, add='+')

    def _enabled(self) -> bool:
        getter_enabled = self._enabled_getter() if self._enabled_getter is not None else True
        return self._forced_enabled and getter_enabled

    def _redraw(self) -> None:
        if not self._enabled():
            fill = self._default_bg
            text_color = spec.MODULE_THREE_CUSTOM_DISABLED_TEXT_COLOR
        elif self._pressed:
            fill = self._pressed_bg
            text_color = self._text_color
        elif self._hovered:
            fill = self._hover_bg
            text_color = self._text_color
        else:
            fill = self._default_bg
            text_color = self._text_color
        self.configure(bg=fill)
        self.delete('all')
        try:
            self.create_text(
                self._size[0] // 2,
                self._size[1] // 2,
                text=self._text,
                angle=90,
                fill=text_color,
                font=self._font,
            )
        except tk.TclError:
            self.create_text(
                self._size[0] // 2,
                self._size[1] // 2,
                text='\n'.join(self._text),
                fill=text_color,
                font=self._font,
                justify='center',
            )

    def _on_enter(self, _event: tk.Event) -> None:
        if not self._enabled():
            return
        self._hovered = True
        self._redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _event: tk.Event) -> str:
        if not self._enabled():
            return 'break'
        self._pressed = True
        self._redraw()
        return 'break'

    def _on_release(self, event: tk.Event) -> str:
        inside = 0 <= event.x < self._size[0] and 0 <= event.y < self._size[1]
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if inside and was_pressed and self._enabled():
            self._command()
        return 'break'

    def set_enabled(self, enabled: bool) -> None:
        self._forced_enabled = enabled
        self._hovered = False
        self._pressed = False
        self._redraw()


class _FooterBase(tk.Frame):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(
            parent,
            bg=spec.MODULE_THREE_CUSTOM_ROW_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_THREE_FOOTER_SIZE[0],
            height=spec.MODULE_THREE_FOOTER_SIZE[1],
        )
        self.pack_propagate(False)
        self.top_edge = tk.Frame(self, bg=spec.MODULE_THREE_CUSTOM_ROW_BORDER_COLOR, bd=0, highlightthickness=0, width=spec.MODULE_THREE_FOOTER_SIZE[0], height=1)
        self.top_edge.place(x=0, y=0)
        self.bottom_edge = tk.Frame(self, bg=spec.MODULE_THREE_CUSTOM_ROW_BORDER_COLOR, bd=0, highlightthickness=0, width=spec.MODULE_THREE_FOOTER_SIZE[0], height=1)
        self.bottom_edge.place(x=0, y=spec.MODULE_THREE_FOOTER_SIZE[1] - 1)
        self.left_edge = tk.Frame(self, bg=spec.MODULE_THREE_CUSTOM_ROW_BORDER_COLOR, bd=0, highlightthickness=0, width=1, height=spec.MODULE_THREE_FOOTER_SIZE[1])
        self.left_edge.place(x=0, y=0)
        self.right_edge = tk.Frame(self, bg=spec.MODULE_THREE_CUSTOM_ROW_BORDER_COLOR, bd=0, highlightthickness=0, width=1, height=spec.MODULE_THREE_FOOTER_SIZE[1])
        self.right_edge.place(x=spec.MODULE_THREE_FOOTER_SIZE[0] - 1, y=0)


class AppearanceSingleCustomFooter(_FooterBase):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_pick_inventory: Callable[[], None],
        on_pick_world: Callable[[], None],
        on_commit: Callable[[], None],
        on_reset: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._on_commit = on_commit
        self._main_hovered = False
        self._main_pressed = False
        self._commit_enabled = False
        self._enabled = True

        main_width = spec.MODULE_THREE_FOOTER_SIZE[0] - spec.MODULE_THREE_CUSTOM_RESET_SIZE[0]
        self.main_surface = tk.Frame(
            self,
            bg=spec.MODULE_THREE_CUSTOM_ROW_BG,
            bd=0,
            highlightthickness=0,
            width=main_width - 2,
            height=spec.MODULE_THREE_FOOTER_SIZE[1] - 2,
        )
        self.main_surface.place(x=1, y=1)

        label_font = (spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_FONT_FAMILY, spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_FONT_SIZE)
        self.inventory_label = tk.Label(self.main_surface, text='Inventory', bg=spec.MODULE_THREE_CUSTOM_ROW_BG, fg=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_COLOR, bd=0, highlightthickness=0, font=label_font, anchor='center')
        self.inventory_label.place(x=spec.MODULE_THREE_CUSTOM_SELECTOR_ONE_POS[0], y=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_Y, width=spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[0], height=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_HEIGHT)
        self.world_label = tk.Label(self.main_surface, text='World', bg=spec.MODULE_THREE_CUSTOM_ROW_BG, fg=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_COLOR, bd=0, highlightthickness=0, font=label_font, anchor='center')
        self.world_label.place(x=spec.MODULE_THREE_CUSTOM_SELECTOR_TWO_POS[0], y=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_Y, width=spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[0], height=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_HEIGHT)

        self.inventory_box = _SelectorBox(self.main_surface, command=on_pick_inventory)
        self.inventory_box.place(x=spec.MODULE_THREE_CUSTOM_SELECTOR_ONE_POS[0], y=spec.MODULE_THREE_CUSTOM_SELECTOR_ONE_POS[1])
        self.world_box = _SelectorBox(self.main_surface, command=on_pick_world)
        self.world_box.place(x=spec.MODULE_THREE_CUSTOM_SELECTOR_TWO_POS[0], y=spec.MODULE_THREE_CUSTOM_SELECTOR_TWO_POS[1])

        self.main_label = tk.Label(
            self.main_surface,
            text='Add Custom',
            bg=spec.MODULE_THREE_CUSTOM_ROW_BG,
            fg=spec.MODULE_THREE_CUSTOM_ACTION_LABEL_COLOR,
            bd=0,
            highlightthickness=0,
            font=(spec.MODULE_THREE_CUSTOM_ACTION_LABEL_FONT_FAMILY, spec.MODULE_THREE_CUSTOM_ACTION_LABEL_FONT_SIZE),
            anchor='w',
        )
        self.main_label.place(x=spec.MODULE_THREE_CUSTOM_ACTION_LABEL_X, y=0, width=100, height=spec.MODULE_THREE_FOOTER_SIZE[1])

        self.reset_strip = _VerticalStrip(
            self,
            size=spec.MODULE_THREE_CUSTOM_RESET_SIZE,
            text='RESET',
            default_bg=spec.MODULE_THREE_CUSTOM_RESET_BG,
            hover_bg=spec.MODULE_THREE_CUSTOM_RESET_HOVER_BG,
            pressed_bg=spec.MODULE_THREE_CUSTOM_RESET_PRESSED_BG,
            text_color=spec.MODULE_THREE_CUSTOM_RESET_TEXT_COLOR,
            font=(spec.MODULE_THREE_CUSTOM_RESET_TEXT_FONT_FAMILY, spec.MODULE_THREE_CUSTOM_RESET_TEXT_FONT_SIZE),
            command=on_reset,
        )
        self.reset_strip.place(x=spec.MODULE_THREE_FOOTER_SIZE[0] - spec.MODULE_THREE_CUSTOM_RESET_SIZE[0], y=0)

        for widget in (self.main_surface, self.main_label, self.inventory_label, self.world_label):
            widget.bind('<Enter>', self._on_main_enter, add='+')
            widget.bind('<Leave>', self._on_main_leave, add='+')
            widget.bind('<ButtonPress-1>', self._on_main_press, add='+')
            widget.bind('<ButtonRelease-1>', self._on_main_release, add='+')

    def tooltip_widgets_for_inventory_upload(self) -> tuple[tk.Misc, ...]:
        return (self.inventory_box, self.inventory_label)

    def tooltip_widgets_for_world_upload(self) -> tuple[tk.Misc, ...]:
        return (self.world_box, self.world_label)

    def tooltip_widgets_for_add_custom(self) -> tuple[tk.Misc, ...]:
        return (self.main_label,)

    def tooltip_widgets_for_reset(self) -> tuple[tk.Misc, ...]:
        return (self.reset_strip,)

    def set_staged_images(self, *, inventory_path: str, world_path: str) -> None:
        self.inventory_box.set_preview_path(inventory_path)
        self.world_box.set_preview_path(world_path)

    def set_commit_enabled(self, enabled: bool) -> None:
        self._commit_enabled = enabled

    def _apply_main_fill(self) -> None:
        if self._main_pressed:
            fill = spec.MODULE_THREE_CUSTOM_ROW_PRESSED_BG
        elif self._main_hovered:
            fill = spec.MODULE_THREE_CUSTOM_ROW_HOVER_BG
        else:
            fill = spec.MODULE_THREE_CUSTOM_ROW_BG
        self.main_surface.configure(bg=fill)
        self.inventory_label.configure(bg=fill)
        self.world_label.configure(bg=fill)
        self.main_label.configure(bg=fill)
        self.inventory_box.set_background_color(fill)
        self.world_box.set_background_color(fill)

    def _on_main_enter(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._main_hovered = True
        self._apply_main_fill()

    def _on_main_leave(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._main_hovered = False
        self._main_pressed = False
        self._apply_main_fill()

    def _on_main_press(self, _event: tk.Event) -> str:
        if not self._enabled:
            return 'break'
        self._main_pressed = True
        self._apply_main_fill()
        return 'break'

    def _on_main_release(self, event: tk.Event) -> str:
        if not self._enabled:
            return 'break'
        widget = event.widget
        root_x = widget.winfo_rootx() + event.x
        root_y = widget.winfo_rooty() + event.y
        target = self.winfo_containing(root_x, root_y)
        inside_main = False
        current = target
        while current is not None:
            if current is self.main_surface:
                inside_main = True
                break
            current = current.master
        should_commit = inside_main and self._main_pressed and self._commit_enabled
        self._main_pressed = False
        self._apply_main_fill()
        if should_commit:
            self._on_commit()
        return 'break'

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.inventory_box.set_enabled(enabled)
        self.world_box.set_enabled(enabled)
        self.reset_strip.set_enabled(enabled)
        label_color = spec.MODULE_THREE_CUSTOM_DISABLED_TEXT_COLOR if not enabled else spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_COLOR
        action_color = spec.MODULE_THREE_CUSTOM_DISABLED_TEXT_COLOR if not enabled else spec.MODULE_THREE_CUSTOM_ACTION_LABEL_COLOR
        self.inventory_label.configure(fg=label_color)
        self.world_label.configure(fg=label_color)
        self.main_label.configure(fg=action_color)
        self._apply_main_fill()


class AppearanceDualCustomFooter(_FooterBase):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_pick_inventory_full: Callable[[], None],
        on_pick_world_full: Callable[[], None],
        on_pick_inventory_empty: Callable[[], None],
        on_pick_world_empty: Callable[[], None],
        on_commit: Callable[[], None],
        on_reset: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._commit_enabled = False
        self._main_hovered = False
        self._main_pressed = False
        self._enabled = True
        label_font = (spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_FONT_FAMILY, spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_FONT_SIZE)

        self.main_surface = tk.Frame(
            self,
            bg=spec.MODULE_THREE_CUSTOM_ROW_BG,
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_THREE_DUAL_CUSTOM_ADD_X - 1,
            height=spec.MODULE_THREE_FOOTER_SIZE[1] - 2,
        )
        self.main_surface.place(x=1, y=1)

        label_texts = ('Inventory', 'World', 'Inventory', 'World')
        box_commands = (
            on_pick_inventory_full,
            on_pick_world_full,
            on_pick_inventory_empty,
            on_pick_world_empty,
        )
        box_captions = ('FULL', 'FULL', 'EMPTY', 'EMPTY')
        self.boxes: list[_SelectorBox] = []
        self.box_labels: list[tk.Label] = []
        for index in range(4):
            x = spec.MODULE_THREE_DUAL_CUSTOM_FIRST_BOX_X + (index * (spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[0] + spec.MODULE_THREE_DUAL_CUSTOM_BOX_GAP))
            label = tk.Label(
                self.main_surface,
                text=label_texts[index],
                bg=spec.MODULE_THREE_CUSTOM_ROW_BG,
                fg=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_COLOR,
                bd=0,
                highlightthickness=0,
                font=label_font,
                anchor='center',
            )
            label.place(
                x=x,
                y=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_Y,
                width=spec.MODULE_THREE_CUSTOM_SELECTOR_SIZE[0],
                height=spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_HEIGHT,
            )
            self.box_labels.append(label)
            box = _SelectorBox(self.main_surface, command=box_commands[index], caption=box_captions[index])
            box.place(x=x, y=spec.MODULE_THREE_CUSTOM_SELECTOR_ONE_POS[1])
            self.boxes.append(box)

        self.add_custom_strip = _VerticalStrip(
            self,
            size=spec.MODULE_THREE_DUAL_CUSTOM_ADD_SIZE,
            text='ADD CUSTOM',
            default_bg=spec.MODULE_THREE_DUAL_CUSTOM_ADD_BG,
            hover_bg=spec.MODULE_THREE_DUAL_CUSTOM_ADD_HOVER_BG,
            pressed_bg=spec.MODULE_THREE_DUAL_CUSTOM_ADD_PRESSED_BG,
            text_color=spec.MODULE_THREE_DUAL_CUSTOM_ADD_TEXT_COLOR,
            font=(spec.MODULE_THREE_DUAL_CUSTOM_ADD_TEXT_FONT_FAMILY, spec.MODULE_THREE_DUAL_CUSTOM_ADD_TEXT_FONT_SIZE),
            command=on_commit,
            enabled_getter=lambda: self._commit_enabled,
        )
        self.add_custom_strip.place(x=spec.MODULE_THREE_DUAL_CUSTOM_ADD_X, y=0)
        self.reset_strip = _VerticalStrip(
            self,
            size=spec.MODULE_THREE_CUSTOM_RESET_SIZE,
            text='RESET',
            default_bg=spec.MODULE_THREE_CUSTOM_RESET_BG,
            hover_bg=spec.MODULE_THREE_CUSTOM_RESET_HOVER_BG,
            pressed_bg=spec.MODULE_THREE_CUSTOM_RESET_PRESSED_BG,
            text_color=spec.MODULE_THREE_CUSTOM_RESET_TEXT_COLOR,
            font=(spec.MODULE_THREE_CUSTOM_RESET_TEXT_FONT_FAMILY, spec.MODULE_THREE_CUSTOM_RESET_TEXT_FONT_SIZE),
            command=on_reset,
        )
        self.reset_strip.place(x=spec.MODULE_THREE_FOOTER_SIZE[0] - spec.MODULE_THREE_CUSTOM_RESET_SIZE[0], y=0)

        for widget in (self.main_surface, *self.box_labels):
            widget.bind('<Enter>', self._on_main_enter, add='+')
            widget.bind('<Leave>', self._on_main_leave, add='+')
            widget.bind('<ButtonPress-1>', self._on_main_press, add='+')
            widget.bind('<ButtonRelease-1>', self._on_main_release, add='+')

    def tooltip_widgets_for_box(self, index: int) -> tuple[tk.Misc, ...]:
        return (self.boxes[index], self.box_labels[index])

    def tooltip_widgets_for_add_custom(self) -> tuple[tk.Misc, ...]:
        return (self.add_custom_strip,)

    def tooltip_widgets_for_reset(self) -> tuple[tk.Misc, ...]:
        return (self.reset_strip,)

    def set_staged_images(
        self,
        *,
        inventory_full: str,
        world_full: str,
        inventory_empty: str,
        world_empty: str,
    ) -> None:
        values = (inventory_full, world_full, inventory_empty, world_empty)
        for box, value in zip(self.boxes, values, strict=False):
            box.set_preview_path(value)

    def set_commit_enabled(self, enabled: bool) -> None:
        self._commit_enabled = enabled

    def _apply_main_fill(self) -> None:
        if self._main_pressed:
            fill = spec.MODULE_THREE_CUSTOM_ROW_PRESSED_BG
        elif self._main_hovered:
            fill = spec.MODULE_THREE_CUSTOM_ROW_HOVER_BG
        else:
            fill = spec.MODULE_THREE_CUSTOM_ROW_BG
        self.main_surface.configure(bg=fill)
        for label in self.box_labels:
            label.configure(bg=fill)
        for box in self.boxes:
            box.set_background_color(fill)

    def _on_main_enter(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._main_hovered = True
        self._apply_main_fill()

    def _on_main_leave(self, _event: tk.Event) -> None:
        if not self._enabled:
            return
        self._main_hovered = False
        self._main_pressed = False
        self._apply_main_fill()

    def _on_main_press(self, _event: tk.Event) -> str:
        if not self._enabled:
            return 'break'
        self._main_pressed = True
        self._apply_main_fill()
        return 'break'

    def _on_main_release(self, event: tk.Event) -> str:
        if not self._enabled:
            return 'break'
        widget = event.widget
        root_x = widget.winfo_rootx() + event.x
        root_y = widget.winfo_rooty() + event.y
        target = self.winfo_containing(root_x, root_y)
        inside_main = False
        current = target
        while current is not None:
            if current is self.main_surface:
                inside_main = True
                break
            current = current.master
        should_commit = inside_main and self._main_pressed and self._commit_enabled
        self._main_pressed = False
        self._apply_main_fill()
        if should_commit:
            self.add_custom_strip._command()
        return 'break'

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        for box in self.boxes:
            box.set_enabled(enabled)
        self.add_custom_strip.set_enabled(enabled)
        self.reset_strip.set_enabled(enabled)
        label_color = spec.MODULE_THREE_CUSTOM_DISABLED_TEXT_COLOR if not enabled else spec.MODULE_THREE_CUSTOM_SELECTOR_LABEL_COLOR
        for label in self.box_labels:
            label.configure(fg=label_color)
        self._apply_main_fill()
