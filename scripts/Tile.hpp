#pragma once
enum class TileType { EMPTY, SOIL, CROP };
enum  class CropState { EMPTY, PLANTED, GROWN }; //switched these to class to avoid empty conflicts 2/14/26

struct Tile 
{
    TileType type = TileType::EMPTY;
    CropState cropstate = CropState::EMPTY;
};