import pygame
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from tile import Tile
    from level import Level

# Color palette — swap these to restyle the farmer
_SKIN       = (232, 184, 138)
_SHIRT      = (200,  90,  42)   # rust/flannel
_OVERALLS   = ( 59,  95, 138)   # denim blue
_OVERALLS_D = ( 42,  74, 114)   # darker denim (straps, pocket)
_HAT_BODY   = (139,  85,  35)   # warm brown
_HAT_BRIM   = (122,  74,  26)   # slightly darker brim
_HAT_BAND   = ( 90,  48,  16)   # dark band
_BOOT       = ( 59,  42,  26)   # dark leather
_EYE        = ( 59,  42,  26)
_MOUTH      = (160, 115,  90)

# can be adjusted for farmer speed
_MOVE_COOLDOWN = 0.18

# farmer only moves via the in-game IDE, not keyboard input
class Farmer:
    SPEED = 300  # pixels per second for smooth glide

    # initializing the farmer
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

    # updating the farmer position
    def update(self, dt: float, level: "Level") -> None:
        self._move_cooldown = max(0.0, self._move_cooldown - dt)
        # movement animation for the farmer (will be changed)
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

    # drawing the farmer to the screen
    def draw(self, surface: pygame.Surface) -> None:
        cx = int(self.pixel_pos[0])
        cy = int(self.pixel_pos[1])
        ts = self.tile_size

        # Scale factor — everything derived from tile size (designed at 64px)
        s = ts / 64

        def r(v: float) -> int:
            return max(1, int(v * s))

        def rx(offset: float) -> int:
            return cx + int(offset * s)

        def ry(offset: float) -> int:
            return cy + int(offset * s)

        # ── Boots ──────────────────────────────────────────────
        boot_w, boot_h = r(12), r(8)
        pygame.draw.rect(surface, _BOOT,
            (rx(-13), ry(14), boot_w, boot_h), border_radius=r(2))
        pygame.draw.rect(surface, _BOOT,
            (rx(1),   ry(14), boot_w, boot_h), border_radius=r(2))

        # ── Legs (overalls) ────────────────────────────────────
        leg_w, leg_h = r(10), r(18)
        pygame.draw.rect(surface, _OVERALLS,
            (rx(-12), ry(-2), leg_w, leg_h), border_radius=r(2))
        pygame.draw.rect(surface, _OVERALLS,
            (rx(2),   ry(-2), leg_w, leg_h), border_radius=r(2))

        # ── Arms / shirt ───────────────────────────────────────
        arm_w, arm_h = r(8), r(14)
        pygame.draw.rect(surface, _SHIRT,
            (rx(-20), ry(-6), arm_w, arm_h), border_radius=r(3))
        pygame.draw.rect(surface, _SHIRT,
            (rx(12),  ry(-6), arm_w, arm_h), border_radius=r(3))

        # ── Body / overalls bib ────────────────────────────────
        body_w, body_h = r(24), r(20)
        pygame.draw.rect(surface, _OVERALLS,
            (rx(-12), ry(-8), body_w, body_h), border_radius=r(3))

        # Straps
        strap_w = r(5)
        pygame.draw.rect(surface, _OVERALLS_D,
            (rx(-7), ry(-8), strap_w, r(8)), border_radius=r(2))
        pygame.draw.rect(surface, _OVERALLS_D,
            (rx(2),  ry(-8), strap_w, r(8)), border_radius=r(2))

        # Bib pocket
        pygame.draw.rect(surface, _OVERALLS_D,
            (rx(-4), ry(-4), r(8), r(6)), border_radius=r(1))

        # ── Head ───────────────────────────────────────────────
        head_r = r(11)
        head_cy = ry(-20)
        pygame.draw.circle(surface, _SKIN, (cx, head_cy), head_r)

        # Eyes
        eye_r = r(1.5)
        pygame.draw.circle(surface, _EYE, (rx(-4), head_cy - r(2)), eye_r)
        pygame.draw.circle(surface, _EYE, (rx(4),  head_cy - r(2)), eye_r)

        # Smile (arc)
        smile_rect = pygame.Rect(rx(-4), head_cy + r(3), r(8), r(3))
        pygame.draw.arc(surface, _MOUTH, smile_rect, 3.5, 6.0, max(1, r(1.5)))

        # ── Hat brim ───────────────────────────────────────────
        brim_w, brim_h = r(36), r(5)
        pygame.draw.rect(surface, _HAT_BRIM,
            (cx - brim_w // 2, head_cy - head_r - r(2), brim_w, brim_h),
            border_radius=r(2))

        # Hat body
        hat_w, hat_h = r(26), r(16)
        hat_top = head_cy - head_r - r(2) - hat_h
        pygame.draw.rect(surface, _HAT_BODY,
            (cx - hat_w // 2, hat_top, hat_w, hat_h), border_radius=r(3))

        # Hat band
        pygame.draw.rect(surface, _HAT_BAND,
            (cx - hat_w // 2, hat_top + hat_h - r(5), hat_w, r(4)))

    def __repr__(self) -> str:
        return f"Farmer(tile={self.current_tile})"