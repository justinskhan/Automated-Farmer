from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crop import Crop


# tile colors
_COLOR_WALKABLE     = (160, 210, 120)   # light green
_COLOR_UNWALKABLE   = (100,  80,  60)   # brown
_COLOR_HOVER        = (200, 240, 160)   # highlighted green
_COLOR_BORDER       = ( 80, 130,  60)   # dark green border
_COLOR_BORDER_BLOCK = ( 60,  40,  20)

#this class handles the tiles that the farmer walks on
class Tile:

    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        walkable: bool = True,
        color: tuple[int, int, int] | None = None,
    ):
        self.rect = pygame.Rect(x, y, width, height)
        self.walkable = walkable
        self.crop: Crop | None = None  # set externally
        self._font: pygame.font.Font | None = None

        #this will allow caller functions to override attributes of tiles
        if color is not None:
            self.color: tuple[int, int, int] = color
        else:
            self.color = _COLOR_WALKABLE if walkable else _COLOR_UNWALKABLE

        self._hovered = False

    #helper functions
    def plant(self, crop: "Crop") -> bool:
        """Plant a crop on this tile. Returns False if already occupied."""
        if self.crop is not None or not self.walkable:
            return False
        self.crop = crop
        return True

    def remove_crop(self) -> "Crop | None":
        """Remove and return the crop from this tile."""
        c = self.crop
        self.crop = None
        return c

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        """Update hover state and crop growth each frame."""
        self._hovered = self.rect.collidepoint(mouse_pos) and self.walkable
        if self.crop:
            self.crop.update(dt)

    #creates the tile itself
    def draw(self, surface: pygame.Surface) -> None:
        fill = _COLOR_HOVER if self._hovered else self.color
        pygame.draw.rect(surface, fill, self.rect)

        border_color = _COLOR_BORDER if self.walkable else _COLOR_BORDER_BLOCK
        pygame.draw.rect(surface, border_color, self.rect, 2)

        if self.crop:
            self.crop.draw(surface, self.rect)

        if not self.walkable:
            self._draw_x(surface)

    #this will draw an X if the farmer cant walk on this tile
    def _draw_x(self, surface: pygame.Surface) -> None:
        r = self.rect
        margin = r.width // 4
        color = (60, 40, 20)
        pygame.draw.line(surface, color,
                         (r.left + margin, r.top + margin),
                         (r.right - margin, r.bottom - margin), 2)
        pygame.draw.line(surface, color,
                         (r.right - margin, r.top + margin),
                         (r.left + margin, r.bottom - margin), 2)

    #debugger function that can show the values of the tile
    def __repr__(self) -> str:
        return f"Tile(rect={self.rect}, walkable={self.walkable}, crop={self.crop})"
