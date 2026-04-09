from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
 
if TYPE_CHECKING:
    from crop import Crop
 
 
_COLOR_WALKABLE     = (160, 210, 120)
_COLOR_UNWALKABLE   = (100,  80,  60)
_COLOR_HOVER        = (200, 240, 160)
_COLOR_BORDER       = ( 80, 130,  60)
_COLOR_BORDER_BLOCK = ( 60,  40,  20)
_COLOR_COOLDOWN     = (180, 140,  80)
 
_HARVEST_COOLDOWN = 3.0
 
 
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
        self.crop: Crop | None = None
        self._font: pygame.font.Font | None = None
 
        # allow caller functions to override tile color
        if color is not None:
            self.color: tuple[int, int, int] = color
        else:
            self.color = _COLOR_WALKABLE if walkable else _COLOR_UNWALKABLE
 
        self._hovered = False
        # counts down from _HARVEST_COOLDOWN to 0 after a harvest
        self._cooldown: float = 0.0
 
    # returns true if the tile is currently in its post-harvest cooldown
    @property
    def on_cooldown(self) -> bool:
        return self._cooldown > 0.0
 
    # plant a crop on this tile, returns False if occupied or on cooldown
    def plant(self, crop: "Crop") -> bool:
        if self.crop is not None or not self.walkable:
            return False
        if self.on_cooldown:
            return False
        self.crop = crop
        return True
 
    # remove and return the crop, then start the cooldown timer
    def remove_crop(self) -> "Crop | None":
        c = self.crop
        self.crop = None
        self._cooldown = _HARVEST_COOLDOWN
        return c
 
    # update hover state, crop growth, and cooldown timer each frame
    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self._hovered = self.rect.collidepoint(mouse_pos) and self.walkable
        if self.crop:
            self.crop.update(dt)
        if self._cooldown > 0.0:
            self._cooldown = max(0.0, self._cooldown - dt)
 
    # draw the tile, with cooldown color lerp and progress bar if cooling down
    def draw(self, surface: pygame.Surface) -> None:
        if self.on_cooldown:
            # lerp between cooldown color and normal color as the timer runs out
            t = self._cooldown / _HARVEST_COOLDOWN
            fill = (
                int(_COLOR_COOLDOWN[0] * t + self.color[0] * (1 - t)),
                int(_COLOR_COOLDOWN[1] * t + self.color[1] * (1 - t)),
                int(_COLOR_COOLDOWN[2] * t + self.color[2] * (1 - t)),
            )
        elif self._hovered:
            fill = _COLOR_HOVER
        else:
            fill = self.color
 
        pygame.draw.rect(surface, fill, self.rect)
 
        border_color = _COLOR_BORDER if self.walkable else _COLOR_BORDER_BLOCK
        pygame.draw.rect(surface, border_color, self.rect, 2)
 
        if self.crop:
            self.crop.draw(surface, self.rect)
 
        if not self.walkable:
            self._draw_x(surface)
 
        # draw a small progress bar at the bottom of the tile while cooling down
        if self.on_cooldown:
            bar_h    = 5
            bar_w    = self.rect.width - 8
            bar_x    = self.rect.x + 4
            bar_y    = self.rect.bottom - bar_h - 3
            filled_w = int(bar_w * (self._cooldown / _HARVEST_COOLDOWN))
            pygame.draw.rect(surface, (40, 40, 40),
                             pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=2)
            if filled_w > 0:
                pygame.draw.rect(surface, _COLOR_COOLDOWN,
                                 pygame.Rect(bar_x, bar_y, filled_w, bar_h), border_radius=2)
 
    # draw an X on unwalkable tiles
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
 
    def __repr__(self) -> str:
        return f"Tile(rect={self.rect}, walkable={self.walkable}, crop={self.crop})"
 