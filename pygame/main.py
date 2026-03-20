import pygame
import ast
from background import Background
from level import LevelManager
from farmer import Farmer
from ide import IDE
from crop import Crop, CropType
from debug import print_grid

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

#plants a crop on the tile the farmer is currently standing on
def plant(crop_name: str) -> None:
    #map the string name to the crop type enum
    crop_map = {
        "wheat":  CropType.WHEAT,
        "corn":   CropType.CORN,
        "tomato": CropType.TOMATO,
        "carrot": CropType.CARROT,
    }
    #exit if the crop name isnt recognized
    crop_type = crop_map.get(crop_name.lower())
    if crop_type is None:
        print(f"Unknown crop: {crop_name}")
        return
    tile = farmer.current_tile
    #only plant if the tile doesnt already have a crop
    if tile.crop is not None:
        print("Tile already has a crop.")
        return
    tile.plant(Crop(crop_type, start_growth=1.0))

#harvests the crop on the tile the farmer is currently standing on
def harvest() -> None:
    tile = farmer.current_tile
    #exit if there is no crop on the tile
    if tile.crop is None:
        print("No crop to harvest here.")
        return
    #exit if the crop isnt fully grown yet
    if not tile.crop.grown:
        print("Crop not ready to harvest yet.")
        return
    #remove the crop from the screen once harvested
    print(f"Harvested: {tile.crop.crop_type.name}")
    tile.remove_crop()

#holds the list of commands to run one at a time
command_queue: list = []

frame_count = 0
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
            try:
                #parse each line into its own command and add to the queue
                tree = ast.parse(code)
                for node in tree.body:
                    command_queue.append(
                        compile(ast.Module([node], type_ignores=[]), "<ide>", "exec")
                    )
            except Exception as e:
                print(f"IDE error: {e}")

    #run the next command in the queue only when the farmer has arrived
    if command_queue and farmer._arrived:
        cmd = command_queue.pop(0)
        try:
            exec(cmd, {"move": move, "plant": plant, "harvest": harvest})
        except Exception as e:
            print(f"IDE error: {e}")

    farmer.update(dt, level, accept_input=not ide.focused)
    ide.update(dt)

    background.draw(screen)
    level.draw(screen)
    farmer.draw(screen)
    ide.draw(screen)

    pygame.display.flip()

    # Print debug for every 30 frames
    frame_count += 1
    if frame_count % 30 == 0:
        print_grid(level)

pygame.quit()