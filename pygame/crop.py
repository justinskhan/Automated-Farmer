import os
import pygame
import math
from enum import Enum, auto


class CropType(Enum):
    WHEAT  = auto()
    CORN   = auto()
    TOMATO = auto()
    CARROT = auto()


_CROP_COLOR = {
    CropType.WHEAT:  (210, 180,  50),
    CropType.CORN:   (255, 220,   0),
    CropType.TOMATO: (220,  50,  50),
    CropType.CARROT: (230, 120,  20),
}

_STEM    = (60, 110, 20)
_LEAF    = (75, 145, 30)
_OUTLINE = (0, 0, 0)

# Tomato sprite sheet — plant-only region (soil excluded, drawn separately).
# (x, y, width, height) within sprites/tomatoGrowth.png
_TOMATO_FRAMES = [
    (358, 579,  69,  64),   # SEED
    (460, 555,  89,  82),   # SPROUT
    (582, 531, 108, 100),   # GROW
    (723, 507, 127, 118),   # FLOWER
    (883, 483, 146, 136),   # HARVEST
]
# Dirt strip drawn under every tomato sprite (matches HARVEST sprite width visually)
_DIRT_H          = 10
_DIRT_BASE       = (123,  79, 46)
_DIRT_HIGHLIGHT  = (160,  99, 41)

_tomato_sprites: list | None = None


def _load_tomato_sprites() -> list:
    """Lazy-load and cache the 5 plant-only tomato surfaces with full alpha masking."""
    global _tomato_sprites
    if _tomato_sprites is not None:
        return _tomato_sprites
    sheet_path = os.path.join(os.path.dirname(__file__), 'sprites', 'tomatoGrowth.png')
    sheet = pygame.image.load(sheet_path).convert()
    sprites = []
    for x, y, w, h in _TOMATO_FRAMES:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.blit(sheet, (0, 0), (x, y, w, h))
        #mask out all of the black background
        #use blue color to filter them out
        surf.lock()
        for py in range(h):
            for px in range(w):
                col = surf.get_at((px, py))
                r, g, b = col.r, col.g, col.b
                if r + g + b < 180 and b >= r and b >= g:
                    surf.set_at((px, py), (0, 0, 0, 0))
        surf.unlock()
        sprites.append(surf)
    _tomato_sprites = sprites
    return sprites


def _dim(color, g):
    f = 0.7 + 0.3 * g
    return tuple(int(c * f) for c in color)


class Crop:
    def __init__(self, crop_type, growth_rate=0.05, start_growth=0.0):
        self.crop_type   = crop_type
        self.growth_rate = growth_rate
        self.growth      = start_growth
        self.grown       = start_growth >= 1.0
        self.harvested   = False
        self.color       = _CROP_COLOR[crop_type]

    def update(self, dt):
        if self.harvested or self.grown:
            return
        self.growth = min(1.0, self.growth + self.growth_rate * dt)
        if self.growth >= 1.0:
            self.grown = True

    def harvest(self):
        if self.grown and not self.harvested:
            self.harvested = True
            return self.crop_type
        return None

    def draw(self, surface, tile_rect):
        if self.harvested:
            return

        g  = self.growth
        cx = tile_rect.centerx
        cy = tile_rect.centery
        s  = max(16, tile_rect.width * 2 // 5)
        by = cy + s // 2      # soil line
        stem_h = max(2, int(s * 1.1 * g))
        top    = by - stem_h

        if self.crop_type == CropType.WHEAT:
            # stem
            pygame.draw.line(surface, _dim(_STEM, g), (cx, by), (cx, top), max(1, s // 10))
            # two alternating leaves
            if g > 0.2:
                ll = max(3, int(s * 0.4 * g))
                for i, side in enumerate([1, -1]):
                    ly = by - int(stem_h * (0.4 + i * 0.25))
                    pygame.draw.line(surface, _dim(_LEAF, g),
                                     (cx, ly), (cx + side * ll, ly - ll // 3),
                                     max(1, s // 12))
            # golden ear
            if g > 0.5:
                ew = max(2, int(s * 0.2 * g))
                eh = max(3, int(s * 0.5 * g))
                pygame.draw.ellipse(surface, _dim((210, 180, 50), g),
                                    (cx - ew, top - eh, ew * 2, eh))
                # awns
                if g > 0.75:
                    for dx in [-4, 0, 4]:
                        side = 1 if dx >= 0 else -1
                        pygame.draw.line(surface, _dim((170, 140, 20), g),
                                         (cx + dx, top - eh),
                                         (cx + dx + side, top - eh - 8), 1)

        elif self.crop_type == CropType.CORN:
            stem_h = max(2, int(s * 1.4 * g))
            top    = by - stem_h
            # thick stalk
            pygame.draw.line(surface, _dim(_STEM, g), (cx, by), (cx, top), max(2, s // 7))
            # broad leaves
            if g > 0.15:
                ll = max(4, int(s * 0.55 * g))
                for i, side in enumerate([1, -1, 1, -1]):
                    ly  = by - int(stem_h * (0.2 + i * 0.2))
                    pts = [(cx, ly), (cx + side * 4, ly - 4),
                           (cx + side * ll, ly - ll // 5),
                           (cx + side * 2,  ly + 4)]
                    pygame.draw.polygon(surface, _dim(_LEAF, g), pts)
            # cob
            if g > 0.55:
                cw  = max(2, int(s * 0.2 * g))
                ch  = max(3, int(s * 0.55 * g))
                cx2 = cx + s // 5
                cy2 = by - int(stem_h * 0.55)
                pygame.draw.ellipse(surface, _dim((255, 210, 0), g),
                                    (cx2 - cw, cy2 - ch // 2, cw * 2, ch))
                pygame.draw.ellipse(surface, _OUTLINE,
                                    (cx2 - cw, cy2 - ch // 2, cw * 2, ch), 1)
            # tassel
            if g > 0.85:
                for dx in range(-2, 3):
                    pygame.draw.line(surface, _dim((200, 170, 30), g),
                                     (cx, top), (cx + dx * 4, top - s // 4), 1)

        elif self.crop_type == CropType.TOMATO:
            # Dirt strip — full tile width
            pygame.draw.rect(surface, _DIRT_BASE,
                             (tile_rect.x, tile_rect.bottom - _DIRT_H,
                              tile_rect.width, _DIRT_H))
            pygame.draw.rect(surface, _DIRT_HIGHLIGHT,
                             (tile_rect.x, tile_rect.bottom - _DIRT_H,
                              tile_rect.width, 3))
            # Plant sprite above the dirt
            sprites = _load_tomato_sprites()
            stage = min(4, int(g * 5))
            sprite = sprites[stage]
            sw, sh = sprite.get_size()
            avail_h = tile_rect.height - _DIRT_H
            scale = min(tile_rect.width / sw, avail_h / sh)
            dw = max(1, int(sw * scale))
            dh = max(1, int(sh * scale))
            scaled = pygame.transform.scale(sprite, (dw, dh))
            surface.blit(scaled, (tile_rect.centerx - dw // 2,
                                  tile_rect.bottom - _DIRT_H - dh))

        elif self.crop_type == CropType.CARROT:
            # feathery tops
            n = max(1, int(g * 6))
            for i in range(n):
                angle = -1.0 + (i / max(n - 1, 1)) * 2.0
                ll    = max(3, int(s * 0.8 * g))
                tx    = cx + int(math.sin(angle) * ll)
                ty    = by - int(math.cos(angle) * ll)
                pygame.draw.line(surface, _dim(_LEAF, g), (cx, by), (tx, ty),
                                 max(1, s // 13))
            # tapered root below soil line
            if g > 0.1:
                rw  = max(2, int(s * 0.22 * g))
                rl  = max(3, int(s * 0.7  * g))
                pts = [(cx - rw // 2, by), (cx + rw // 2, by),
                       (cx + 1, by + rl),  (cx - 1, by + rl)]
                pygame.draw.polygon(surface, _dim((230, 120, 20), g), pts)
                pygame.draw.polygon(surface, _OUTLINE, pts, 1)
                # growth rings
                if g > 0.5:
                    for r in range(1, 4):
                        ry  = by + int(rl * r * 0.25)
                        rw2 = max(1, rw // 2 - r)
                        pygame.draw.line(surface, _dim((160, 80, 10), g),
                                         (cx - rw2, ry), (cx + rw2, ry), 1)

    def __repr__(self):
        return (f"Crop({self.crop_type.name}, growth={self.growth:.2f}, "
                f"grown={self.grown}, harvested={self.harvested})")