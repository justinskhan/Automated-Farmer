import pygame
from tile import Tile
from crop import Crop, CropType

# key for grid
#   '.' = regular walkable tile
#   'X' = cant walk
#   'W' = wheat crop
#   'C' = corn crop
#   'T' = tomato crop
#   'R' = carrot crop
#   'F' = this is where the farmer starts (required)

#with this level, you can see the name of the level is set along with the level number
#the F means the player starts on top left corner with all the rest of the tiles being accessible
LEVEL_1 = {
    "name": "The Starter Farm",
    "number": 1,
    "grid": [
        "F..",
        "...",
        "...",
    ],
}

#placeholder for level 2
LEVEL_2 = {
    "name": "Crop Fields",
    "number": 2,
    "grid": [
        "F.W..",
        ".X..C",
        "T.X..",
        "..R..",
        ".....",
    ],
}

_ALL_LEVELS = [LEVEL_1, LEVEL_2]

#mapping the characters to certain crops
_CROP_MAP: dict[str, CropType] = {
    "W": CropType.WHEAT,
    "C": CropType.CORN,
    "T": CropType.TOMATO,
    "R": CropType.CARROT,
}

#this class will parse thru the dict and build the tiles and crops and locate the farmer
class Level:
    TILE_SIZE = 120 #default tile size before screen is resized

    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.number: int = data["number"]
        self.grid_data: list[str] = data["grid"]

        self.rows: int = len(self.grid_data)
        self.cols: int = len(self.grid_data[0])
        self.tiles: list[list[Tile]] = []
        self.start_tile: Tile | None = None

        self._build()

    #this function converts the character strings into tiles
    def _build(self) -> None:
        #center the grid on an 800x600 base — main.py will
        # pass the actual screen size via center_on().
        self.tiles = []
        for r, row_str in enumerate(self.grid_data):
            row: list[Tile] = []
            for c, ch in enumerate(row_str):
                x = c * self.TILE_SIZE
                y = r * self.TILE_SIZE
                walkable = ch != "X"
                tile = Tile(x, y, self.TILE_SIZE, self.TILE_SIZE, walkable=walkable)

                if ch in _CROP_MAP:
                    tile.crop = Crop(_CROP_MAP[ch])

                if ch == "F":
                    self.start_tile = tile

                row.append(tile)
            self.tiles.append(row)

        #will make the default start tile top left is none is given
        if self.start_tile is None:
            self.start_tile = self.tiles[0][0]

    #function that handles the screen being resized and adjusting tile size
    def center_on(self, screen_width: int, screen_height: int) -> None:
        grid_w = self.cols * self.TILE_SIZE
        grid_h = self.rows * self.TILE_SIZE
        offset_x = (screen_width - grid_w) // 2
        offset_y = (screen_height - grid_h) // 2

        for r, row in enumerate(self.tiles):
            for c, tile in enumerate(row):
                tile.rect.topleft = (
                    offset_x + c * self.TILE_SIZE,
                    offset_y + r * self.TILE_SIZE,
                )

    #tile lookup helper functions
    def get_tile(self, row: int, col: int) -> Tile | None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.tiles[row][col]
        return None

    def find_tile(self, tile: Tile) -> tuple[int, int] | None:
        """Return (row, col) of a tile, or None if not found."""
        for r, row in enumerate(self.tiles):
            for c, t in enumerate(row):
                if t is tile:
                    return r, c
        return None

    #functions for updating and drawing the tiles
    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        for row in self.tiles:
            for tile in row:
                tile.update(dt, mouse_pos)

    def draw(self, surface: pygame.Surface) -> None:
        for row in self.tiles:
            for tile in row:
                tile.draw(surface)


#this class tracks the current level and adjusts for levels
class LevelManager:
    def __init__(self):
        self._index: int = 0
        self.current: Level = self._load(self._index)

    def _load(self, index: int) -> Level:
        return Level(_ALL_LEVELS[index])

    #checks if farmer is ready for next level, true if finished false otherwise
    def next_level(self, screen_w: int, screen_h: int) -> bool:
        if self._index + 1 >= len(_ALL_LEVELS):
            return False
        self._index += 1
        self.current = self._load(self._index)
        self.current.center_on(screen_w, screen_h)
        return True
    
    #function to restart the level if needed (not implemented fully yet)
    def reload(self, screen_w: int, screen_h: int) -> None:
        self.current = self._load(self._index)
        self.current.center_on(screen_w, screen_h)