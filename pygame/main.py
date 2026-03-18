import pygame
from background import Background
from level import LevelManager
from farmer import Farmer
from ide import IDE

pygame.init()
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Automated Farmer")
clock = pygame.time.Clock()

manager = LevelManager()
manager.current.center_on(*screen.get_size())

level = manager.current
farmer = Farmer(level.start_tile, level.TILE_SIZE)
farmer.snap_to_tile()

background = Background(color=(173, 216, 230))
ide = IDE(20, 20)

running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        #updating the window size 
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            #center the level
            level.center_on(event.w, event.h)
            #redraw the tile so it is back on the tile 
            farmer.snap_to_tile()

        #passing an event to the IDE
        code = ide.handle_event(event)
        if code is not None:
            # moving up down right and left 
            def move(direction: str) -> None:
                #find the tile the farmer is on 
                pos = level.find_tile(farmer.current_tile)
                #if the farmer isnt there exit
                if pos is None:
                    return
                r, c = pos
                #map the direction of the movement using rows and columns 
                deltas = {
                    "up":    (-1,  0),
                    "down":  ( 1,  0),
                    "left":  ( 0, -1),
                    "right": ( 0,  1),
                }
                dr, dc = deltas.get(direction.lower(), (0, 0))
                target = level.get_tile(r + dr, c + dc)
                #move only if the target tile exists and the tile is walkable 
                if target and target.walkable:
                    #update the farmers tile 
                    farmer.current_tile = target
                    farmer._target_pos = [
                        float(target.rect.centerx),
                        float(target.rect.centery),
                    ]
                    farmer._arrived = False

            try:
                #only work if move is in front of the text
                exec(code, {"move": move})
            except Exception as e:
                print(f"IDE error: {e}")

    farmer.update(dt, level, accept_input=not ide.focused)
    ide.update(dt)

    background.draw(screen)
    level.draw(screen)
    farmer.draw(screen)
    ide.draw(screen)

    pygame.display.flip()

pygame.quit()