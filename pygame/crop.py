import pygame
from enum import Enum, auto


class CropType(Enum):
    WHEAT  = auto()
    CORN   = auto()
    TOMATO = auto()
    CARROT = auto()


#crop colors
_CROP_COLOR: dict[CropType, tuple[int, int, int]] = {
    CropType.WHEAT:  (210, 180,  50),   #wheat gold
    CropType.CORN:   (255, 220,   0),   #bright yellow
    CropType.TOMATO: (220,  50,  50),   #red
    CropType.CARROT: (230, 120,  20),   #orange
}

_OUTLINE = (0, 0, 0)

#class for crops inside a tile
class Crop:

    def __init__(
        self,
        crop_type: CropType,
        growth_rate: float = 0.05,
        start_growth: float = 0.0,
    ):
        self.crop_type = crop_type
        self.growth_rate = growth_rate
        self.growth: float = start_growth
        self.grown: bool = start_growth >= 1.0
        self.harvested: bool = False
        self.color = _CROP_COLOR[crop_type]

    #updating and logic for game
    def update(self, dt: float) -> None:
        """Advance crop growth over time (call once per frame)."""
        if self.harvested or self.grown:
            return
        self.growth = min(1.0, self.growth + self.growth_rate * dt)
        if self.growth >= 1.0:
            self.grown = True

    def harvest(self) -> CropType | None:
        if self.grown and not self.harvested:
            self.harvested = True
            return self.crop_type
        return None

    #drawing crops centered on the tile with a shape per crop type
    def draw(self, surface: pygame.Surface, tile_rect: pygame.Rect) -> None:
        if self.harvested:
            return

        #darken color based on growth (dim when young, full color when grown)
        factor = 0.7 + 0.3 * self.growth
        draw_color = tuple(int(c * factor) for c in self.color)

        size = max(16, tile_rect.width * 2 // 5)
        cx = tile_rect.centerx
        cy = tile_rect.centery

        if self.crop_type == CropType.WHEAT:
            #wheat colored sqaure for wheat
            half = size // 2
            rect = pygame.Rect(cx - half, cy - half, size, size)
            pygame.draw.rect(surface, draw_color, rect, border_radius=3)
            pygame.draw.rect(surface, _OUTLINE, rect, 1, border_radius=3)

        elif self.crop_type == CropType.CORN:
            #yellow circle for corn
            pygame.draw.circle(surface, draw_color, (cx, cy), size // 2)
            pygame.draw.circle(surface, _OUTLINE, (cx, cy), size // 2, 1)

        elif self.crop_type == CropType.TOMATO:
            # red circle
            pygame.draw.circle(surface, draw_color, (cx, cy), size // 2)
            pygame.draw.circle(surface, _OUTLINE, (cx, cy), size // 2, 1)

        elif self.crop_type == CropType.CARROT:
            #orange triangle for carrot
            half = size // 2
            points = [
                (cx,        cy - half),   # top point
                (cx - half, cy + half),   # bottom-left
                (cx + half, cy + half),   # bottom-right
            ]
            pygame.draw.polygon(surface, draw_color, points)
            pygame.draw.polygon(surface, _OUTLINE, points, 1)

    def __repr__(self) -> str:
        return (
            f"Crop({self.crop_type.name}, growth={self.growth:.2f}, "
            f"grown={self.grown}, harvested={self.harvested})"
        )