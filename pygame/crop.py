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
            # wavy stem via 3 segments
            pts = [(cx, by)]
            for i in range(1, 4):
                t = i / 3
                pts.append((cx + int(math.sin(t * math.pi * 2) * 3),
                             by - int(stem_h * t)))
            for i in range(len(pts) - 1):
                pygame.draw.line(surface, _dim(_STEM, g), pts[i], pts[i + 1],
                                 max(1, s // 12))
            # small leaves
            if g > 0.2:
                ll = max(3, int(s * 0.35 * g))
                for i, side in enumerate([1, -1, 1]):
                    ly = by - int(stem_h * (0.25 + i * 0.25))
                    pygame.draw.line(surface, _dim(_LEAF, g),
                                     (cx, ly), (cx + side * ll, ly - ll // 3),
                                     max(1, s // 13))
            # fruits — blend green -> red as g rises
            if g > 0.45:
                fp      = (g - 0.45) / 0.55
                fr      = max(2, int(s * 0.28 * fp))
                blend   = max(0.0, (g - 0.6) / 0.4)
                fruit_c = _dim((int(80 + blend * 140), int(150 - blend * 110), 20), g)
                for ox, oy_frac in [(-s // 5, 0.65), (s // 5, 0.72), (0, 0.52)]:
                    fx = cx + ox
                    fy = by - int(stem_h * oy_frac)
                    pygame.draw.circle(surface, fruit_c, (fx, fy), fr)
                    pygame.draw.circle(surface, _OUTLINE, (fx, fy), fr, 1)

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
