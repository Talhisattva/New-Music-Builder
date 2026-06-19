from __future__ import annotations

import tkinter as tk


class BorderPane(tk.Frame):
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
        self._border_width = border_width
        self._show_top_edge = show_top_edge
        self._show_right_edge = show_right_edge
        self._show_bottom_edge = show_bottom_edge
        self._show_left_edge = show_left_edge

    def resize(self, size: tuple[int, int]) -> None:
        width, height = size
        self.configure(width=width, height=height)
        if self.top_edge is not None:
            self.top_edge.place_configure(x=0, y=0, width=width, height=self._border_width)
        if self.right_edge is not None:
            self.right_edge.place_configure(x=width - self._border_width, y=0, width=self._border_width, height=height)
        if self.bottom_edge is not None:
            self.bottom_edge.place_configure(x=0, y=height - self._border_width, width=width, height=self._border_width)
        if self.left_edge is not None:
            self.left_edge.place_configure(x=0, y=0, width=self._border_width, height=height)

        inset_left = self._border_width if self._show_left_edge else 0
        inset_top = self._border_width if self._show_top_edge else 0
        inset_right = self._border_width if self._show_right_edge else 0
        inset_bottom = self._border_width if self._show_bottom_edge else 0
        self.content.configure(width=width - inset_left - inset_right, height=height - inset_top - inset_bottom)
        self.content.place_configure(x=inset_left, y=inset_top, width=width - inset_left - inset_right, height=height - inset_top - inset_bottom)

    @property
    def fill_color(self) -> str:
        return self._fill_color
