from __future__ import annotations

import tkinter as tk

from new_music_builder.ui import spec
from new_music_builder.ui.widgets.border_pane import BorderPane
from new_music_builder.ui.widgets.scroll_area import ScrollViewport


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

        self.tabs_pane = BorderPane(
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

        self.footer_pane = BorderPane(
            self,
            size=spec.MODULE_THREE_FOOTER_SIZE,
            fill_color=spec.MODULE_THREE_CUSTOM_ROW_BG,
            border_color=spec.MODULE_THREE_CUSTOM_ROW_BORDER_COLOR,
        )
        self.footer_pane.place(x=0, y=spec.MODULE_THREE_FOOTER_Y)

        self.dual_sprite_left_pane = BorderPane(
            self,
            size=spec.MODULE_THREE_DUAL_SPRITE_LEFT_SIZE,
            fill_color=fill_color,
            border_color=border_color,
        )
        self.dual_sprite_left_pane.place(x=0, y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y)
        self.preview_mode_pane = BorderPane(
            self,
            size=spec.MODULE_THREE_PREVIEW_MODE_ROW_SIZE,
            fill_color=fill_color,
            border_color=border_color,
        )
        self.preview_mode_pane.place(x=spec.MODULE_THREE_DUAL_SPRITE_LEFT_SIZE[0], y=spec.MODULE_THREE_DUAL_SPRITE_ROW_Y)
        self.expanded_footer_overlay = BorderPane(
            self,
            size=spec.MODULE_THREE_EXPANDED_FOOTER_OVERLAY_SIZE,
            fill_color=fill_color,
            border_color=border_color,
        )
        self.dual_sprite_row = self.dual_sprite_left_pane

        self.set_expanded_footer_overlay_visible(show_expanded_footer_overlay)

    def set_expanded_footer_overlay_visible(self, visible: bool) -> None:
        if visible:
            self.expanded_footer_overlay.place(x=0, y=spec.MODULE_THREE_EXPANDED_FOOTER_OVERLAY_Y)
            self.expanded_footer_overlay.lift()
        else:
            self.expanded_footer_overlay.place_forget()
