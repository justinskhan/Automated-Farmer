#pragma once
#include <vector>
#include "Tile.hpp"
class Grid {
    public:
    Grid(int grid_width, int grid_height);
    int getGridWidth();
    int getGridHeight();
    
    private:
    std::vector<std::vector<Tile>> TileVector;
    int grid_width = 10;
    int grid_height = 10;

};