#pragma once
#include <vector>
#include "Tile.hpp"
class Grid 
{
    public:
    Grid(int grid_width, int grid_height);
    int getGridWidth() const;
    int getGridHeight() const;

    // added for rendering tiles 2/14/26
    Tile& getTile(int x, int y);
    const Tile& getTile(int x, int y) const;
    
    private:
    std::vector<std::vector<Tile>> TileVector;
    int grid_width = 10;
    int grid_height = 10;

};