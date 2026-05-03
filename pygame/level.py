from __future__ import annotations
 
import pygame
from tile import Tile
from crop import Crop, CropType
from objective import Objective
from ui_scale import s as _s
 
# key for grid
# '.' = regular walkable tile
# 'X' = cant walk
# 'F' = this is where the farmer starts (required for now)
 
# level 1 - just get started, plant and harvest 1 crop, no timer
LEVEL_1 = {
    "name": "First Steps",
    "number": 1,
    "grid": [
        "F..",
        "...",
        "...",
    ],
    "objective": Objective(
        harvests_required=1,
        time_limit=None,
        allowed_commands=["move", "plant", "harvest"],
    ),
    "hint": "",
}
 
# level 2 - a bit more work, harvest 3 crops, no timer
LEVEL_2 = {
    "name": "Getting Started",
    "number": 2,
    "grid": [
        "F..",
        "...",
        "...",
    ],
    "objective": Objective(
        harvests_required=3,
        time_limit=None,
        allowed_commands=["move", "plant", "harvest"],
    ),
    "hint": "",
}
 
# level 3 - bigger grid, harvest 5 crops, no timer — for loops unlocked here
LEVEL_3 = {
    "name": "Growing Season",
    "number": 3,
    "grid": [
        "F...",
        "....",
        "....",
        "....",
    ],
    "objective": Objective(
        harvests_required=5,
        time_limit=None,
        allowed_commands=["move", "plant", "harvest", "for"],
    ),
    "hint": "",
}
 
# level 4 - same grid but now has a time limit to add pressure
LEVEL_4 = {
    "name": "Race the Clock",
    "number": 4,
    "grid": [
        "F...",
        "....",
        "....",
        "....",
    ],
    "objective": Objective(
        harvests_required=8,
        time_limit=90.0,
        allowed_commands=["move", "plant", "harvest", "for"],
    ),
    "hint": "",
}
 
# level 5 - while loops unlocked here, bigger grid, harder goal
LEVEL_5 = {
    "name": "Automation Station",
    "number": 5,
    "grid": [
        "F....",
        ".....",
        ".....",
        ".....",
        ".....",
    ],
    "objective": Objective(
        harvests_required=15,
        time_limit=120.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
    ),
    "hint": "",
}
 
# level 6 - obstacles introduced, must harvest specific crops
# X tiles force the farmer to navigate around a wall in the middle
LEVEL_6 = {
    "name": "The Obstacle Course",
    "number": 6,
    "grid": [
        "F....",
        ".XXX.",
        ".....",
        ".XXX.",
        ".....",
    ],
    "objective": Objective(
        harvests_required=6,
        time_limit=75.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 3, "corn": 3},
    ),
    "hint": "",
}
 
# level 7 - maze-like grid, specific crop requirements, tighter timer
# farmer must navigate through a corridor layout
LEVEL_7 = {
    "name": "The Maze",
    "number": 7,
    "grid": [
        "F.X..",
        "..X..",
        "..X..",
        ".....",
        "XX.XX",
    ],
    "objective": Objective(
        harvests_required=8,
        time_limit=70.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 2, "corn": 2, "tomato": 2, "carrot": 2},
    ),
    "hint": "",
}
 
# level 8 - bigger grid, lots of obstacles, very specific crop requirements
# farmer must work around a cross-shaped obstacle in the center
LEVEL_8 = {
    "name": "The Crossroads",
    "number": 8,
    "grid": [
        "F.....",
        "..XXX.",
        "......",
        ".XXX..",
        "......",
        "..XXX.",
    ],
    "objective": Objective(
        harvests_required=10,
        time_limit=65.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 3, "corn": 3, "tomato": 2, "carrot": 2},
    ),
    "hint": "",
}
 
# level 9 - large grid with scattered obstacles and tight timer
# requires careful planning and efficient loops to finish in time
LEVEL_9 = {
    "name": "The Gauntlet",
    "number": 9,
    "grid": [
        "F..X...",
        ".X...X.",
        "...X...",
        ".X...X.",
        "...X...",
        ".X...X.",
        ".......",
    ],
    "objective": Objective(
        harvests_required=12,
        time_limit=60.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 3, "corn": 3, "tomato": 3, "carrot": 3},
    ),
    "hint": "",
}
 
# level 10 - alternating corridor walls force the farmer to snake through
# each row, requires efficient loop logic to finish in time
LEVEL_10 = {
    "name": "The Final Harvest",
    "number": 10,
    "grid": [
        "F.......",
        "XXXXXXX.",
        "........",
        ".XXXXXXX",
        "........",
        "XXXXXXX.",
        "........",
        "........",
    ],
    "objective": Objective(
        harvests_required=16,
        time_limit=50.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 4, "corn": 4, "tomato": 4, "carrot": 4},
    ),
    "hint": "",
}
 
# level 11 - scattered obstacle clusters across an open grid
# farmer must weave between them to reach all farmable tiles
LEVEL_11 = {
    "name": "The Spiral",
    "number": 11,
    "grid": [
        "F.......",
        "..XXX...",
        "........",
        "...XXX..",
        "........",
        "..XXX...",
        "........",
        "........",
    ],
    "objective": Objective(
        harvests_required=16,
        time_limit=55.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 4, "corn": 4, "tomato": 4, "carrot": 4},
    ),
    "hint": "",
}
 
# level 12 - columns of obstacles with open paths on both edges
# farmer must sweep up and down between the obstacle columns
LEVEL_12 = {
    "name": "Checkerboard",
    "number": 12,
    "grid": [
        "F.......",
        ".X.X.X..",
        ".X.X.X..",
        ".X.X.X..",
        ".X.X.X..",
        ".X.X.X..",
        ".X.X.X..",
        "........",
    ],
    "objective": Objective(
        harvests_required=18,
        time_limit=55.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 5, "corn": 5, "tomato": 4, "carrot": 4},
    ),
    "hint": "",
}
 
# level 13 - alternating corridor walls, farmer must snake through each row
# gaps alternate left and right so the farmer zigzags down the grid
LEVEL_13 = {
    "name": "The Tunnel",
    "number": 13,
    "grid": [
        "F.........",
        "XXXXXXXXX.",
        "..........",
        ".XXXXXXXXX",
        "..........",
        "XXXXXXXXX.",
        "..........",
    ],
    "objective": Objective(
        harvests_required=18,
        time_limit=60.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 5, "corn": 5, "tomato": 4, "carrot": 4},
    ),
    "hint": "",
}
 
# level 14 - L-shaped walls split the grid into connected regions
# farmer starts top-left and must navigate along the open edges
LEVEL_14 = {
    "name": "Four Corners",
    "number": 14,
    "grid": [
        "F.........",
        "....XXXXXX",
        "....XXXXXX",
        "....XXXXXX",
        ".XXXXXXXXX",
        ".XXXXXXXXX",
        ".XXXXXXXXX",
        "....XXXXXX",
        "....XXXXXX",
        "..........",
    ],
    "objective": Objective(
        harvests_required=20,
        time_limit=55.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 5, "corn": 5, "tomato": 5, "carrot": 5},
    ),
    "hint": "",
}
 
# level 15 - walls block large sections but alternate sides each row
# farmer must find the gap on each wall to pass through to the next corridor
LEVEL_15 = {
    "name": "The Archipelago",
    "number": 15,
    "grid": [
        "F..........",
        "..XXXXXXXX.",
        "...........",
        "XXXXXXXX...",
        "...........",
        "...XXXXXXXX",
        "...........",
        ".XXXXXXXX..",
        "...........",
    ],
    "objective": Objective(
        harvests_required=20,
        time_limit=50.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 5, "corn": 5, "tomato": 5, "carrot": 5},
    ),
    "hint": "",
}
 
# level 16 - long hallways separated by walls with alternating gaps
# farmer must efficiently loop back and forth through each corridor
LEVEL_16 = {
    "name": "Hallways",
    "number": 16,
    "grid": [
        "F.........",
        "XXXXXXXXX.",
        "..........",
        ".XXXXXXXXX",
        "..........",
        "XXXXXXXXX.",
        "..........",
        ".XXXXXXXXX",
        "..........",
    ],
    "objective": Objective(
        harvests_required=22,
        time_limit=55.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 6, "corn": 6, "tomato": 5, "carrot": 5},
    ),
    "hint": "",
}
 
# level 17 - open center ringed by obstacles with one gap at the bottom
# farmer starts outside and must find the entry point to farm inside
LEVEL_17 = {
    "name": "The Moat",
    "number": 17,
    "grid": [
        "F.........",
        ".XXXXXXXX.",
        ".X......X.",
        ".X......X.",
        ".X......X.",
        ".X......X.",
        ".X......X.",
        ".XXXX.XXX.",
        "..........",
    ],
    "objective": Objective(
        harvests_required=20,
        time_limit=50.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 5, "corn": 5, "tomato": 5, "carrot": 5},
    ),
    "hint": "",
}
 
# level 18 - dense alternating walls, tighter than the tunnel levels
# requires very efficient loop logic to snake through in time
LEVEL_18 = {
    "name": "The Labyrinth",
    "number": 18,
    "grid": [
        "F.........",
        "XXXXXXXX..",
        "..........",
        "XXXXXXXXX.",
        "..........",
        "..XXXXXXXXX",
        "..........",
        "XXXXXXXXX.",
        "..........",
    ],
    "objective": Objective(
        harvests_required=24,
        time_limit=45.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 6, "corn": 6, "tomato": 6, "carrot": 6},
    ),
    "hint": "",
}
 
# level 19 - scattered random-looking obstacle pattern across a large grid
# lots of walkable tiles but the path is non-obvious, very tight timer
LEVEL_19 = {
    "name": "The Scatterplot",
    "number": 19,
    "grid": [
        "F..X..X....",
        "..X....X...",
        "X....X....X",
        "...X....X..",
        "..X..X.....",
        ".X....X..X.",
        "....X....X.",
        "X....X.....",
        "..X....X..X",
        "...X..X....",
        "...........",
    ],
    "objective": Objective(
        harvests_required=24,
        time_limit=40.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 6, "corn": 6, "tomato": 6, "carrot": 6},
    ),
    "hint": "",
}
 
# level 20 - the grand finale: massive grid, heavy alternating walls,
# extremely tight timer, requires mastery of loops and planning
LEVEL_20 = {
    "name": "The Ultimate Harvest",
    "number": 20,
    "grid": [
        "F.........",
        "XXXXXXXXX.",
        "..........",
        ".XXXXXXXX.",
        "..........",
        ".XXXXXXXX.",
        "..........",
        ".XXXXXXXXX",
        "..........",
        "XXXXXXXXX.",
        "..........",
    ],
    "objective": Objective(
        harvests_required=32,
        time_limit=40.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 8, "corn": 8, "tomato": 8, "carrot": 8},
    ),
    "hint": "",
}

LEVEL_21 = {
    "name": "The Serpentine",
    "number": 21,
    "grid": [
        "F...........",
        "XXXXXXXXXX..",
        "............",
        "..XXXXXXXXXX",
        "............",
        "XXXXXXXXXX..",
        "............",
        "..XXXXXXXXXX",
        "............",
        "XXXXXXXXXX..",
        "............",
    ],
    "objective": Objective(
        harvests_required=36,
        time_limit=38.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 9, "corn": 9, "tomato": 9, "carrot": 9},
    ),
    "hint": "",
}

LEVEL_22 = {
    "name": "The Comb",
    "number": 22,
    "grid": [
        "F.........",
        ".X.X.X.X..",
        ".X.X.X.X..",
        ".X.X.X.X..",
        ".X.X.X.X..",
        ".X.X.X.X..",
        ".X.X.X.X..",
        ".X.X.X.X..",
        ".X.X.X.X..",
        "..........",
    ],
    "objective": Objective(
        harvests_required=40,
        time_limit=35.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 10, "corn": 10, "tomato": 10, "carrot": 10},
    ),
    "hint": "",
}
 
LEVEL_23 = {
    "name": "The Double Moat",
    "number": 23,
    "grid": [
        "F...........",
        ".XXXXXXXXXX.",
        ".X........X.",
        ".X.XXXXXX.X.",
        ".X.X....X.X.",
        ".X.X....X.X.",
        ".X.X....X.X.",
        ".X.X....X.X.",
        ".X.XXXX.X.X.",
        ".X........X.",
        ".XXXXX.XXXX.",
        "............",
    ],
    "objective": Objective(
        harvests_required=40,
        time_limit=35.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 10, "corn": 10, "tomato": 10, "carrot": 10},
    ),
    "hint": "",
}
 

LEVEL_24 = {
    "name": "The Pillars",
    "number": 24,
    "grid": [
        "F.............",
        "..XX...XX...XX",
        "..XX...XX...XX",
        "..............",
        "....XX...XX...",
        "....XX...XX...",
        "..............",
        "..XX...XX...XX",
        "..XX...XX...XX",
        "..............",
        "....XX...XX...",
        "....XX...XX...",
        "..............",
    ],
    "objective": Objective(
        harvests_required=44,
        time_limit=32.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 11, "corn": 11, "tomato": 11, "carrot": 11},
    ),
    "hint": "",
}
 

LEVEL_25 = {
    "name": "The Grand Finale",
    "number": 25,
    "grid": [
        "F.............",
        "XXXXXXXXXXXXX.",
        "..............",
        ".XXXXXXXXXXXXX",
        "..............",
        "XXXXXXXXXXXXX.",
        "..............",
        ".XXXXXXXXXXXXX",
        "..............",
        "XXXXXXXXXXXXX.",
        "..............",
        ".XXXXXXXXXXXXX",
        "..............",
    ],
    "objective": Objective(
        harvests_required=48,
        time_limit=30.0,
        allowed_commands=["move", "plant", "harvest", "for", "while"],
        crop_requirements={"wheat": 12, "corn": 12, "tomato": 12, "carrot": 12},
    ),
    "hint": "",
}
 
_ALL_LEVELS = [
    LEVEL_1,  LEVEL_2,  LEVEL_3,  LEVEL_4,  LEVEL_5,
    LEVEL_6,  LEVEL_7,  LEVEL_8,  LEVEL_9,  LEVEL_10,
    LEVEL_11, LEVEL_12, LEVEL_13, LEVEL_14, LEVEL_15,
    LEVEL_16, LEVEL_17, LEVEL_18, LEVEL_19, LEVEL_20,
    LEVEL_21, LEVEL_22, LEVEL_23, LEVEL_24, LEVEL_25,
]
 
#mapping the characters to certain crops
_CROP_MAP: dict[str, CropType] = {
    "W": CropType.WHEAT,
    "C": CropType.CORN,
    "T": CropType.TOMATO,
    "R": CropType.CARROT,
}
 
 
#this class will parse thru the dict and build the tiles and crops and locate the farmer
class Level:
    TILE_SIZE = _s(120) #default tile size before screen is resized (DPR-scaled for browser)
 
    def __init__(self, data: dict):
        #initialization function pulls data from the dict
        self.name: str            = data["name"]
        self.number: int          = data["number"]
        self.grid_data: list[str] = data["grid"]
        #each level now carries its own objective with goals and allowed commands
        self.objective: Objective = data["objective"]
        self.hint: str            = data.get("hint", "")
 
        self.rows: int = len(self.grid_data)
        self.cols: int = len(self.grid_data[0])
        self.tiles: list[list[Tile]] = [] #holds the data until build runs
        self.start_tile: Tile | None = None
 
        self._build()
 
    #this function converts the character strings into tiles
    def _build(self) -> None:
        self.tiles = []
        for r, row_str in enumerate(self.grid_data):
            row: list[Tile] = []
            for c, ch in enumerate(row_str):
                x = c * self.TILE_SIZE
                y = r * self.TILE_SIZE
                walkable = ch != "X"
                tile = Tile(x, y, self.TILE_SIZE, self.TILE_SIZE, walkable=walkable)
 
                #pre-placed crops still supported if ever needed
                if ch in _CROP_MAP:
                    tile.crop = Crop(_CROP_MAP[ch], start_growth=1.0)
 
                if ch == "F":
                    self.start_tile = tile
 
                row.append(tile)
            self.tiles.append(row)
 
        #will make the default start tile top left if none is given
        if self.start_tile is None:
            self.start_tile = self.tiles[0][0]
 
    #function that handles the screen being resized and adjusting tile positions
    def center_on(self, screen_width: int, screen_height: int) -> None:
        grid_w = self.cols * self.TILE_SIZE
        grid_h = self.rows * self.TILE_SIZE
        offset_x = (screen_width  - grid_w) // 2
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
        self._index: int  = 0
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
 
    #function to restart the level if needed, rebuilds from scratch so objective resets
    def reload(self, screen_w: int, screen_h: int) -> None:
        self.current = self._load(self._index)
        self.current.objective.reset()  
        self.current.center_on(screen_w, screen_h)
 
    #returns true if there are no more levels after the current one
    @property
    def on_last_level(self) -> bool:
        return self._index + 1 >= len(_ALL_LEVELS)