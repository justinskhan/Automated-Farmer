#pragma once
enum TileType { EMPTY, SOIL, CROP };
enum crop { EMPTY, PLANTED, GROWN };

struct Tile {
    TileType type = TileType::EMPTY;
    crop CropState = crop::EMPTY;
};