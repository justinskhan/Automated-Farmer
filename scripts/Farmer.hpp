#pragma once
#include "Grid.hpp"


enum direction {LEFT,UP,DOWN,RIGHT};

class Farmer 
{
    public:
    Farmer(Grid& grid);
    bool move(direction GivenDirection);
    private:
    Grid& grid;
    int positionX = 0;
    int positionY = 0;

    int getX() const {return positionX;}
    int getY() const {return positionY;}

    private: 
    Grid& grid; 
    int positionX = 0;
    int positionY = 0;
};

