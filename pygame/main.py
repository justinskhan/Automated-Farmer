import pygame
import ast
from background import Background
from level import LevelManager
from farmer import Farmer
from ide import IDE
from crop import Crop, CropType
from debug import print_grid
from objective import ObjectiveStatus
from overlay import Overlay

pygame.init()
pygame.key.set_repeat(400, 40) #this makes it so if you hold a key, there is a 400ms wait time before the key is printed to IDE again
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Automated Farmer")
clock = pygame.time.Clock()

manager = LevelManager()
manager.current.center_on(*screen.get_size())

level   = manager.current
farmer  = Farmer(level.start_tile, level.TILE_SIZE)
farmer.snap_to_tile()

background = Background(color=(173, 216, 230))
ide        = IDE(20, 20)
overlay    = Overlay()


def _reload_level() -> None:
    """Restart the current level (fail → retry)."""
    global level, farmer
    manager.reload(*screen.get_size())
    level  = manager.current
    farmer = Farmer(level.start_tile, level.TILE_SIZE)
    farmer.snap_to_tile()
    command_queue.clear()
    ide.clear_output()
    ide.update_allowed(level.objective.allowed_commands)


def _advance_level() -> None:
    """Move to the next level (win → continue)."""
    global level, farmer
    if not manager.next_level(*screen.get_size()):
        #No more levels, just reload the last one for now
        manager.reload(*screen.get_size())
    level  = manager.current
    farmer = Farmer(level.start_tile, level.TILE_SIZE)
    farmer.snap_to_tile()
    command_queue.clear()
    ide.clear_output()
    ide.update_allowed(level.objective.allowed_commands)


def move(direction: str) -> None:
    pos = level.find_tile(farmer.current_tile)
    if pos is None:
        return
    r, c = pos
    deltas = {
        "up":    (-1,  0),
        "down":  ( 1,  0),
        "left":  ( 0, -1),
        "right": ( 0,  1),
    }
    dr, dc = deltas.get(direction.lower(), (0, 0))
    target = level.get_tile(r + dr, c + dc)
    if target and target.walkable:
        farmer.current_tile    = target
        farmer._target_pos     = [float(target.rect.centerx), float(target.rect.centery)]
        farmer._arrived        = False


def plant(crop_name: str) -> None:
    if "plant" not in level.objective.allowed_commands:
        ide.log("plant() is locked on this level.", error=True)
        return
    crop_map = {
        "wheat":  CropType.WHEAT,
        "corn":   CropType.CORN,
        "tomato": CropType.TOMATO,
        "carrot": CropType.CARROT,
    }
    crop_type = crop_map.get(crop_name.lower())
    if crop_type is None:
        ide.log(f"Unknown crop: {crop_name}", error=True)
        return
    tile = farmer.current_tile
    if tile.crop is not None:
        ide.log("Tile already has a crop.", error=True)
        return
    tile.plant(Crop(crop_type, start_growth=1.0))
    ide.log(f"Planted: {crop_name}")


def harvest() -> None:
    tile = farmer.current_tile
    if tile.crop is None:
        ide.log("No crop to harvest here.", error=True)
        return
    if not tile.crop.grown:
        ide.log("Crop not ready to harvest yet.", error=True)
        return
    ide.log(f"Harvested: {tile.crop.crop_type.name}")
    tile.remove_crop()
    level.objective.record_harvest()


command_queue: list = []


def has_infinite_loop(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            if isinstance(node.test, ast.Constant) and node.test.value:
                return True
    return False


def _while_loops_allowed() -> bool:
    return "while" in level.objective.allowed_commands


def _check_forbidden_constructs(tree: ast.AST) -> str | None:
    """Return an error string if the code uses a forbidden construct, else None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and not _while_loops_allowed():
            return "while loops are locked — reach level 5 to unlock them."
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return "for loops are not available."
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "import statements are not allowed."
    return None


def _draw_hud(surface: pygame.Surface, lv: "Level") -> None:
    """Draw a level/objective panel and a separate time box in the top-right corner."""
    obj        = lv.objective
    font_title = pygame.font.SysFont("Consolas", 16, bold=True)
    font_body  = pygame.font.SysFont("Consolas", 14)
    font_time  = pygame.font.SysFont("Consolas", 22, bold=True)
    font_label = pygame.font.SysFont("Consolas", 11)

    padding = 10
    line_h  = 20
    margin  = 12   #gap from screen edge and between boxes

    # --- objective panel (level name + harvest progress) ---
    obj_lines = [f"Level {lv.number}: {lv.name}", f"Harvest {obj.harvests_done}/{obj.harvests_required} crops"]

    #measure widest line so the panel always fits
    panel_w = max(font_title.size(obj_lines[0])[0],
                  font_body.size(obj_lines[1])[0]) + padding * 2
    panel_h = padding * 2 + len(obj_lines) * line_h

    sx = surface.get_width() - panel_w - margin
    sy = margin

    #semi-transparent dark background
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((15, 15, 25, 190))
    surface.blit(panel_surf, (sx, sy))

    #border matching IDE style
    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(sx, sy, panel_w, panel_h), 1, border_radius=4)

    #level name in bright white-blue
    surface.blit(font_title.render(obj_lines[0], True, (220, 220, 255)),
                 (sx + padding, sy + padding))

    #harvest progress in green
    surface.blit(font_body.render(obj_lines[1], True, (180, 220, 180)),
                 (sx + padding, sy + padding + line_h))

    # --- time box drawn below the objective panel ---
    time_box_w = panel_w          #same width so they line up nicely
    time_box_h = 54
    tx = sx
    ty = sy + panel_h + 6         #small gap between the two boxes

    #pick time string and color based on whether a timer exists
    t = obj.time_remaining
    if t is None:
        time_str  = "Infinity"
        time_col  = (160, 160, 200)   #muted purple-grey for no timer
    else:
        time_str  = f"{t:.1f}s"
        if t < 10:
            time_col = (220, 80, 80)     #red when critical
        elif t < 20:
            time_col = (230, 180, 50)    #yellow when warning
        else:
            time_col = (180, 220, 180)   #green when plenty of time

    #semi-transparent background for time box
    time_surf = pygame.Surface((time_box_w, time_box_h), pygame.SRCALPHA)
    time_surf.fill((15, 15, 25, 190))
    surface.blit(time_surf, (tx, ty))

    #border matching IDE style
    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(tx, ty, time_box_w, time_box_h), 1, border_radius=4)

    #small "TIME LEFT" label at the top of the box
    label_surf = font_label.render("TIME LEFT", True, (120, 120, 160))
    surface.blit(label_surf, (tx + padding, ty + 6))

    #big time number centered in the box
    time_render = font_time.render(time_str, True, time_col)
    time_x = tx + (time_box_w - time_render.get_width()) // 2
    time_y = ty + time_box_h - time_render.get_height() - 6
    surface.blit(time_render, (time_x, time_y))


ide.update_allowed(level.objective.allowed_commands)


frame_count = 0
running     = True
frozen      = False   # True when overlay is showing

while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            level.center_on(event.w, event.h)
            farmer.snap_to_tile()

        # overlay swallows all input while frozen
        if frozen:
            if overlay.handle_event(event):
                obj = level.objective
                if obj.status == ObjectiveStatus.WIN:
                    _advance_level()
                else:
                    _reload_level()
                frozen = False
            continue   # don't pass events to IDE / farmer while frozen

        # IDE input
        code = ide.handle_event(event)
        if code is not None:
            try:
                tree = ast.parse(code)

                # check forbidden constructs first
                err = _check_forbidden_constructs(tree)
                if err:
                    ide.log(f"Error: {err}", error=True)
                elif has_infinite_loop(tree):
                    ide.log("Error: infinite loop detected.", error=True)
                else:
                    ide.log("Running code...")
                    for node in tree.body:
                        command_queue.append(
                            compile(ast.Module([node], type_ignores=[]), "<ide>", "exec")
                        )

            except SyntaxError as e:
                ide.log(f"Syntax error: {e.msg} (line {e.lineno})", error=True)
            except Exception as e:
                ide.log(f"Error: {e}", error=True)

    if frozen:
        # still need to draw
        background.draw(screen)
        level.draw(screen)
        farmer.draw(screen)
        ide.draw(screen)
        _draw_hud(screen, level)   #hud still visible while frozen
        obj = level.objective
        overlay.draw(
            screen,
            obj.status,
            level.name,
            obj.harvests_done,
            obj.harvests_required,
            obj.elapsed,
            obj.time_limit,
        )
        pygame.display.flip()
        continue

    obj = level.objective
    if obj.status == ObjectiveStatus.PLAYING:
        obj.update(dt)

    if obj.status != ObjectiveStatus.PLAYING and not frozen:
        frozen = True
        command_queue.clear()

    if command_queue and farmer._arrived and not frozen:
        cmd = command_queue.pop(0)
        try:
            exec(cmd, {"move": move, "plant": plant, "harvest": harvest})
        except Exception as e:
            ide.log(f"Error: {e}", error=True)

    farmer.update(dt)
    ide.update(dt)
    level.update(dt, pygame.mouse.get_pos())

    background.draw(screen)
    level.draw(screen)
    farmer.draw(screen)
    ide.draw(screen)
    _draw_hud(screen, level)   #draw the hud last so it sits on top of everything

    pygame.display.flip()

    frame_count += 1
    if frame_count % 30 == 0:
        print_grid(level)

pygame.quit()