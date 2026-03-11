import pygame
from background import Background 
from level import LevelManager
from farmer import Farmer
from ide import IDE

#initialize pygame 
pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE) #pygame starts at 800x600 and is resizable
pygame.display.set_caption("Automated Farmer") #title for the window 
clock = pygame.time.Clock()

#level and farmer handler
manager = LevelManager() #will load the current level user is on
manager.current.center_on(*screen.get_size()) #this makes the grid in the center despite screen size

level = manager.current
farmer = Farmer(level.start_tile, level.TILE_SIZE) #creates farmer and needs the starting tile and the size of the tile
farmer.snap_to_tile()

#background color
background = Background(color=(173, 216, 230)) #color for background can be image in future 

ide = IDE(*screen.get_size())

running = True
while running:
    dt = clock.tick(60) / 1000.0 #this makes the game work at 60 fps instead of 30

#function for when the game window is resized
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            level.center_on(event.w, event.h)
            farmer.snap_to_tile()
            ide.resize(event.w, event.h)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                ide.toggle()
            elif event.key == pygame.K_F5:
                ide.run_code(farmer, level)
            else:
                ide.handle_event(event)
        else:
            ide.handle_event(event)

    # --- Update ---
    ide.update(dt, farmer, level)
    farmer.update(dt, level, block_input=ide._running) #updates the farmer when WASD is pressed or IDE commands run

    background.draw(screen) #first the background is created
    level.draw(screen) #then the level on top
    farmer.draw(screen) #then the farmer
    ide.draw(screen)

    pygame.display.flip() #updates screen

pygame.quit() #called when x is clicked