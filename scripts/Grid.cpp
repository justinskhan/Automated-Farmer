#include "Grid.hpp"
#include <stdexcept>

Grid::Grid(int grid_width, int grid_height)
    : grid_width(grid_width), grid_height(grid_height)
{
    if (grid_width <= 0 || grid_height <= 0)
        throw std::invalid_argument("Grid dimensions must be positive");

    TileVector.resize(this->grid_height);
    for (int y = 0; y < this->grid_height; y++) {
        TileVector[y].resize(this->grid_width);
    }
}

int Grid::getGridWidth() const { return grid_width; }
int Grid::getGridHeight() const { return grid_height; }

Tile& Grid::getTile(int x, int y)
{
    if (x < 0 || x >= grid_width || y < 0 || y >= grid_height)
        throw std::out_of_range("getTile out of range");
    return TileVector[y][x];
}

const Tile& Grid::getTile(int x, int y) const
{
    if (x < 0 || x >= grid_width || y < 0 || y >= grid_height)
        throw std::out_of_range("getTile out of range");
    return TileVector[y][x];
}