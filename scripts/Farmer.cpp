#include "Farmer.hpp"

Farmer::Farmer(Grid& grid):grid(grid) {

}

bool Farmer::move(direction GivenDirection) {
    int oldX = positionX;
    int oldY = positionY;

    switch (GivenDirection) {
        case LEFT:  {
            positionX--; 
            break;
        } 
        case RIGHT: {
            positionX++; 
            break;

        } 
        case UP:   {
            positionY--; 
            break;

        }  
        case DOWN:  {
            positionY++; 
            break;

        } 
    }

    int maxX = this->grid.getGridWidth() - 1;
    int maxY = this->grid.getGridHeight() - 1;

    if (positionY > maxY) {
        positionY--;
    } 
    else if (positionY < 0) {
        positionY++;
    }
    if (positionX > maxX) {
        positionX--;
    }
    else if (positionX < 0) {
        positionX++;
    }

    //Return false if movement was blocked
    return (positionX != oldX || positionY != oldY);
}
