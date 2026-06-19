from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


class _BorderPane(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        size: tuple[int, int],
        fill_color: str,
        border_color: str,
        border_width: int = 1,
        show_top_edge: bool = True,
        show_right_edge: bool = True,
        show_bottom_edge: bool = True,
        show_left_edge: bool = True,
    ) -> None:
        super().__init__(
            parent,
            bg=fill_color,
            bd=0,
            highlightthickness=0,
            width=size[0],
            height=size[1],
        )
        self.pack_propagate(False)
        self._size = size
        self._fill_color = fill_color

        if show_top_edge:
            self.top_edge = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=size[0], height=border_width)
            self.top_edge.place(x=0, y=0)
        else:
            self.top_edge = None
        if show_right_edge:
            self.right_edge = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=border_width, height=size[1])
            self.right_edge.place(x=size[0] - border_width, y=0)
        else:
            self.right_edge = None
        if show_bottom_edge:
            self.bottom_edge = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=size[0], height=border_width)
            self.bottom_edge.place(x=0, y=size[1] - border_width)
        else:
            self.bottom_edge = None
        if show_left_edge:
            self.left_edge = tk.Frame(self, bg=border_color, bd=0, highlightthickness=0, width=border_width, height=size[1])
            self.left_edge.place(x=0, y=0)
        else:
            self.left_edge = None

        inset_left = border_width if show_left_edge else 0
        inset_top = border_width if show_top_edge else 0
        inset_right = border_width if show_right_edge else 0
        inset_bottom = border_width if show_bottom_edge else 0

        self.content = tk.Frame(
            self,
            bg=fill_color,
            bd=0,
            highlightthickness=0,
            width=size[0] - inset_left - inset_right,
            height=size[1] - inset_top - inset_bottom,
        )
        self.content.place(x=inset_left, y=inset_top)

    @property
    def fill_color(self) -> str:
        return self._fill_color


class AppearancePanelShell(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        bg_color: str,
        show_expanded_footer_overlay: bool = False,
    ) -> None:
        super().__init__(
            parent,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=spec.MODULE_THREE_CONTENT_SIZE[0],
            height=spec.MODULE_THREE_CONTENT_SIZE[1],
        )
        self.pack_propagate(False)

        border_color = spec.MODULE_THREE_PANEL_BORDER_COLOR
        fill_color = spec.MODULE_THREE_PANEL_BG

        self.tabs_pane = _BorderPane(
            self,
            size=spec.MODULE_THREE_TABS_ROW_SIZE,
            fill_color=fill_color,
            border_color=border_color,
        )
        self.tabs_pane.place(x=0, y=0)

        self.grid_viewport = ScrollViewport(
            self,
            size=spec.MODULE_THREE_GRID_VIEWPORT_SIZE,
            viewport_size=spec.MODULE_THREE_GRID_MASK_SIZE,
            scrollbar_size=spec.MODULE_THREE_GRID_SCROLLBAR_SIZE,
            viewport_edge_color=border_color,
            viewport_edge_width=spec.MODULE_THREE_PANEL_BORDER_WIDTH,
            show_top_edge=True,
            content_bottom_padding=0,
            bg_color=fill_color,
        )
        self.grid_viewport.place(x=0, y=spec.MODULE_THREE_GRID_VIEWPORT_Y)
        self.grid_viewport.viewport_left_edge.lower(self.grid_viewport.viewport_canvas)
        self.grid_viewport.viewport_top_edge.lower(self.grid_viewport.viewport_canvas)
        self.grid_viewport.viewport_bottom_edge.lower(self.grid_viewport.viewport_canvas)

        self.footer_pane = _BorderPane(
            self,
            size=spec.MODULE_THREE_FOOTER_SIZE,
            fill_color=spec.MODULE_THREE_CUSTOM_ROW_BG,
            border_color=spec.MODULE_THREE_CUSTOM_ROW_BORDER_COLOR,
        )
        self.footer_pane.place(x=0, y=spec.MODULE_THREE_FOOTER_Y)

        self.dual_sprite_row = _BorderPane(
            self,
            size=spec.MODULE_THREE_DUAL_SPRITE_ROW_SIZE,
            fill_color=fill_color,
            border_color=border_color,
        )
        self.dual_sprite_row.place(x=0, y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y)
        self.expanded_footer_overlay = _BorderPane(
            self,
            size=spec.MODULE_THREE_EXPANDED_FOOTER_OVERLAY_SIZE,
            fill_color=fill_color,
            border_color=border_color,
        )

        self.set_expanded_footer_overlay_visible(show_expanded_footer_overlay)

    def set_expanded_footer_overlay_visible(self, visible: bool) -> None:
        if visible:
            self.expanded_footer_overlay.place(x=0, y=spec.MODULE_THREE_EXPANDED_FOOTER_OVERLAY_Y)
            self.expanded_footer_overlay.lift()
        else:
            self.expanded_footer_overlay.place_forget()
