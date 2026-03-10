import pygame
from enum import Enum, auto


class CropType(Enum):
    WHEAT  = auto()
    CORN   = auto()
    TOMATO = auto()
    CARROT = auto()


#properties for sample crops
_CROP_STYLE: dict[CropType, tuple[tuple[int, int, int], str]] = {
    CropType.WHEAT:  ((210, 180,  50), "W"),
    CropType.CORN:   ((255, 220,   0), "C"),
    CropType.TOMATO: ((220,  50,  50), "T"),
    CropType.CARROT: ((230, 120,  20), "R"),
}

#class for crops inside a tile for now represented by a letter
class Crop:

    FONT_SIZE = 18
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

        color, symbol = _CROP_STYLE[crop_type]
        self.color = color
        self.symbol = symbol

        self._font: pygame.font.Font | None = None  

    #updating and logic for game
    def update(self, dt: float) -> None:
        """Advance crop growth over time (call once per frame)."""
        if self.harvested or self.grown:
            return
        self.growth = min(1.0, self.growth + self.growth_rate * dt)
        if self.growth >= 1.0:
            self.grown = True

    def harvest(self) -> CropType | None:
        """
        Attempt to harvest the crop.
        Returns the CropType if successful, None otherwise.
        """
        if self.grown and not self.harvested:
            self.harvested = True
            return self.crop_type
        return None

    #drawing crops, still heavily wip
    def draw(self, surface: pygame.Surface, tile_rect: pygame.Rect) -> None:
        """Draw the crop indicator inside *tile_rect*."""
        if self.harvested:
            return

        if self._font is None:
            self._font = pygame.font.SysFont("Arial", self.FONT_SIZE, bold=True)

        #draw heavy color square in top right
        size = max(12, tile_rect.width // 4)
        indicator = pygame.Rect(
            tile_rect.right - size - 4,
            tile_rect.top + 4,
            size,
            size,
        )

        #supposed to darken color of the square when not grown
        factor = 0.4 + 0.6 * self.growth
        draw_color = tuple(int(c * factor) for c in self.color)
        pygame.draw.rect(surface, draw_color, indicator, border_radius=3)
        pygame.draw.rect(surface, (0, 0, 0), indicator, 1, border_radius=3)

        # Symbol
        label = self._font.render(self.symbol, True, (255, 255, 255))
        lx = indicator.centerx - label.get_width() // 2
        ly = indicator.centery - label.get_height() // 2
        surface.blit(label, (lx, ly))

    #function to get info while debugging
    def __repr__(self) -> str:
        return (
            f"Crop({self.crop_type.name}, growth={self.growth:.2f}, "
            f"grown={self.grown}, harvested={self.harvested})"
        )
