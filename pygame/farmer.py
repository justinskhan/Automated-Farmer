import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tile import Tile
    from level import Level

#quick mockup for the farmer
_FARMER_COLOR = (70,  90, 200)
_FARMER_HEAD  = (240, 190, 140)
_HAT_COLOR    = (160,  80,  20)

#can be adjusted for farmer speed
_MOVE_COOLDOWN = 0.18

class Farmer:

    SPEED = 300  # pixels per second for smooth glide

    #initializing the farmer
    def __init__(self, start_tile: "Tile", tile_size: int):
        self.current_tile = start_tile
        self.tile_size = tile_size
        self.pixel_pos: list[float] = [
            float(start_tile.rect.centerx),
            float(start_tile.rect.centery),
        ]
        self._target_pos: list[float] = list(self.pixel_pos)
        self._move_cooldown: float = 0.0
        self._arrived: bool = True 

    #updating the farmer position
    def update(self, dt: float) -> None:
        self._move_cooldown = max(0.0, self._move_cooldown - dt)

        #movement animation for the farmer (will be changed)
        arrived_x = arrived_y = False
        for i, arrived in enumerate([False, False]):
            diff = self._target_pos[i] - self.pixel_pos[i]
            step = self.SPEED * dt
            if abs(diff) <= step:
                self.pixel_pos[i] = self._target_pos[i]
                if i == 0:
                    arrived_x = True
                else:
                    arrived_y = True
            else:
                self.pixel_pos[i] += step if diff > 0 else -step

        self._arrived = arrived_x and arrived_y

    def snap_to_tile(self) -> None:
        self.pixel_pos = [
            float(self.current_tile.rect.centerx),
            float(self.current_tile.rect.centery),
        ]
        self._target_pos = list(self.pixel_pos)
        self._arrived = True

    #drawing the farmer to the screen
    def draw(self, surface: pygame.Surface) -> None:
        cx = int(self.pixel_pos[0])
        cy = int(self.pixel_pos[1])
        ts = self.tile_size

        bw = ts // 3
        bh = ts // 3
        body = pygame.Rect(cx - bw // 2, cy - bh // 4, bw, bh)
        pygame.draw.rect(surface, _FARMER_COLOR, body, border_radius=4)

        hr = ts // 7
        hcy = body.top - hr
        pygame.draw.circle(surface, _FARMER_HEAD, (cx, hcy), hr)

        hw = hr * 2 + 6
        hh = hr
        hat = pygame.Rect(cx - hw // 2, hcy - hr - hh + 4, hw, hh)
        pygame.draw.rect(surface, _HAT_COLOR, hat, border_radius=2)
        brim = pygame.Rect(cx - hw // 2 - 4, hcy - hr + 2, hw + 8, 5)
        pygame.draw.rect(surface, _HAT_COLOR, brim)

    def __repr__(self) -> str:
        return f"Farmer(tile={self.current_tile})"