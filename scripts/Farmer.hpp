#pragma once
#include "Grid.hpp"


enum direction {LEFT,UP,DOWN,RIGHT};

class Farmer 
{
    public:
        Farmer(Grid& grid);
        Farmer(Grid& grid, int startX, int startY);

        bool move(direction GivenDirection);

        int getX() const {return positionX;}
        int getY() const {return positionY;}

    private: 
        Grid& grid;
        int positionX = 0;
        int positionY = 0;

};

