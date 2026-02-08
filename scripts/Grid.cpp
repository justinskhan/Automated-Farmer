#include "Grid.hpp"

Grid::Grid(int grid_width, int grid_height) {
    TileVector.resize(grid_height, std::vector<Tile>(grid_width));
    this->grid_height = grid_height;
    this->grid_width = grid_width;
}

int Grid::getGridHeight() {
    return this->grid_height;
}

int Grid::getGridWidth() {
    return this->grid_width;
    
}