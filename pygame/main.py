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
pygame.key.set_repeat(400, 40)
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
 
# game states
STATE_START   = "start"
STATE_PLAYING = "playing"
game_state    = STATE_START
 
# start screen animation state
_btn_hovered  = False
_pulse_timer  = 0.0
 
 
def _draw_start_screen(surface: pygame.Surface, pulse: float) -> None:
    sw, sh = surface.get_size()
 
    # sky-blue background matching the game background color
    surface.fill((173, 216, 230))
 
    # decorative dark panel behind the title area
    panel_w = 520
    panel_h = 280
    panel_x = (sw - panel_w) // 2
    panel_y = (sh - panel_h) // 2 - 20
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((15, 15, 25, 210))
    surface.blit(panel_surf, (panel_x, panel_y))
 
    # subtitle tag line above the main title
    font_sub = pygame.font.SysFont("Consolas", 15)
    sub_surf = font_sub.render("< Learn to code through farming />", True, (100, 180, 100))
    surface.blit(sub_surf, (sw // 2 - sub_surf.get_width() // 2, panel_y + 28))
 
    # main title — large bold text
    font_title = pygame.font.SysFont("Consolas", 52, bold=True)
    title_surf = font_title.render("Automated", True, (220, 240, 200))
    title2_surf = font_title.render("Farmer", True, (160, 210, 120))
    surface.blit(title_surf,  (sw // 2 - title_surf.get_width()  // 2, panel_y + 60))
    surface.blit(title2_surf, (sw // 2 - title2_surf.get_width() // 2, panel_y + 118))
 
    # small decorative crop icons drawn as simple shapes below the title
    icons = [
        ((sw // 2 - 90, panel_y + 195), (210, 180, 50),  "sq"),   # wheat square
        ((sw // 2 - 40, panel_y + 195), (255, 220,  0),  "ci"),   # corn circle
        ((sw // 2 + 10, panel_y + 195), (220,  50, 50),  "ci"),   # tomato circle
        ((sw // 2 + 60, panel_y + 195), (230, 120, 20),  "tr"),   # carrot triangle
    ]
    for (ix, iy), col, shape in icons:
        if shape == "sq":
            pygame.draw.rect(surface, col, pygame.Rect(ix - 10, iy - 10, 20, 20), border_radius=3)
            pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(ix - 10, iy - 10, 20, 20), 1, border_radius=3)
        elif shape == "ci":
            pygame.draw.circle(surface, col, (ix, iy), 10)
            pygame.draw.circle(surface, (0, 0, 0), (ix, iy), 10, 1)
        elif shape == "tr":
            pts = [(ix, iy - 11), (ix - 10, iy + 9), (ix + 10, iy + 9)]
            pygame.draw.polygon(surface, col, pts)
            pygame.draw.polygon(surface, (0, 0, 0), pts, 1)
 
    # play button — pulses slightly in size using the pulse timer
    btn_w  = int(160 + pulse * 6)
    btn_h  = int(48  + pulse * 3)
    btn_x  = sw // 2 - btn_w // 2
    btn_y  = panel_y + panel_h + 30
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
 
    # brighter green when hovered
    btn_color = (70, 210, 100) if _btn_hovered else (50, 180, 80)
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=6)
    pygame.draw.rect(surface, (30, 100, 50), btn_rect, 2, border_radius=6)
 
    # play text inside the button
    font_btn = pygame.font.SysFont("Consolas", 20, bold=True)
    btn_label = font_btn.render("PLAY", True, (255, 255, 255))
    surface.blit(btn_label, (sw // 2 - btn_label.get_width() // 2,
                              btn_y + btn_h // 2 - btn_label.get_height() // 2))
 
    return btn_rect
 
 
def _reload_level() -> None:
    global level, farmer
    manager.reload(*screen.get_size())
    level  = manager.current
    farmer = Farmer(level.start_tile, level.TILE_SIZE)
    farmer.snap_to_tile()
    command_queue.clear()
    ide.clear_output()
    ide.lines = [""]
    ide.cursor_row = 0
    ide.cursor_col = 0
    ide.update_allowed(level.objective.allowed_commands)
 
 
def _advance_level() -> None:
    global level, farmer
    if not manager.next_level(*screen.get_size()):
        manager.reload(*screen.get_size())
    level  = manager.current
    farmer = Farmer(level.start_tile, level.TILE_SIZE)
    farmer.snap_to_tile()
    command_queue.clear()
    ide.clear_output()
    ide.lines = [""]
    ide.cursor_row = 0
    ide.cursor_col = 0
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
        farmer.current_tile = target
        farmer._target_pos  = [float(target.rect.centerx), float(target.rect.centery)]
        farmer._arrived     = False
 
 
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
    if not tile.plant(Crop(crop_type, start_growth=1.0)):
        ide.log("Tile is recovering, wait before replanting.", error=True)
        return
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
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and not _while_loops_allowed():
            return "while loops are locked — reach level 5 to unlock them."
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return "for loops are not available."
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "import statements are not allowed."
    return None
 
 
def _draw_hud(surface: pygame.Surface, lv) -> None:
    obj        = lv.objective
    font_title = pygame.font.SysFont("Consolas", 16, bold=True)
    font_body  = pygame.font.SysFont("Consolas", 14)
    font_time  = pygame.font.SysFont("Consolas", 22, bold=True)
    font_label = pygame.font.SysFont("Consolas", 11)
 
    padding = 10
    line_h  = 20
    margin  = 12
 
    obj_lines = [f"Level {lv.number}: {lv.name}", f"Harvest {obj.harvests_done}/{obj.harvests_required} crops"]
 
    # measure widest line so the panel always fits regardless of level name length
    panel_w = max(font_title.size(obj_lines[0])[0],
                  font_body.size(obj_lines[1])[0]) + padding * 2
    panel_h = padding * 2 + len(obj_lines) * line_h
 
    sx = surface.get_width() - panel_w - margin
    sy = margin
 
    # semi-transparent dark background
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((15, 15, 25, 190))
    surface.blit(panel_surf, (sx, sy))
 
    # border matching IDE style
    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(sx, sy, panel_w, panel_h), 1, border_radius=4)
 
    # level name in bright white-blue
    surface.blit(font_title.render(obj_lines[0], True, (220, 220, 255)),
                 (sx + padding, sy + padding))
 
    # harvest progress in green
    surface.blit(font_body.render(obj_lines[1], True, (180, 220, 180)),
                 (sx + padding, sy + padding + line_h))
 
    # time box sits directly below the objective panel, same width so they align
    time_box_w = panel_w
    time_box_h = 54
    tx = sx
    ty = sy + panel_h + 6
 
    # pick time string and color based on whether a timer exists
    t = obj.time_remaining
    if t is None:
        time_str = "Infinity"
        time_col = (160, 160, 200)
    else:
        time_str = f"{t:.1f}s"
        if t < 10:
            time_col = (220, 80, 80)
        elif t < 20:
            time_col = (230, 180, 50)
        else:
            time_col = (180, 220, 180)
 
    # semi-transparent background for time box
    time_surf = pygame.Surface((time_box_w, time_box_h), pygame.SRCALPHA)
    time_surf.fill((15, 15, 25, 190))
    surface.blit(time_surf, (tx, ty))
 
    # border matching IDE style
    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(tx, ty, time_box_w, time_box_h), 1, border_radius=4)
 
    # small label at the top of the time box
    label_surf = font_label.render("TIME LEFT", True, (120, 120, 160))
    surface.blit(label_surf, (tx + padding, ty + 6))
 
    # large time number centered in the box
    time_render = font_time.render(time_str, True, time_col)
    time_x = tx + (time_box_w - time_render.get_width()) // 2
    time_y = ty + time_box_h - time_render.get_height() - 6
    surface.blit(time_render, (time_x, time_y))
 
 
ide.update_allowed(level.objective.allowed_commands)
 
frame_count = 0
running     = True
frozen      = False
 
while running:
    dt = clock.tick(60) / 1000.0
 
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
 
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            if game_state == STATE_PLAYING:
                level.center_on(event.w, event.h)
                farmer.snap_to_tile()
 
        # handle start screen clicks
        if game_state == STATE_START:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if _current_btn_rect and _current_btn_rect.collidepoint(event.pos):
                    game_state = STATE_PLAYING
                    level.center_on(*screen.get_size())
            continue
 
        # overlay swallows all input while frozen
        if frozen:
            if overlay.handle_event(event):
                obj = level.objective
                if obj.status == ObjectiveStatus.WIN:
                    _advance_level()
                else:
                    _reload_level()
                frozen = False
            # don't pass events to IDE or farmer while frozen
            continue
 
        # pass events to the IDE, run code if the run button was pressed
        code = ide.handle_event(event)
        if code is not None:
            try:
                tree = ast.parse(code)
                # check forbidden constructs before queuing anything
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
 
    # draw and update the start screen
    if game_state == STATE_START:
        import math
        _pulse_timer += dt
        pulse = (math.sin(_pulse_timer * 3) + 1) / 2
        mouse_pos = pygame.mouse.get_pos()
        _current_btn_rect = _draw_start_screen(screen, pulse)
        _btn_hovered = _current_btn_rect.collidepoint(mouse_pos)
        pygame.display.flip()
        continue
 
    # keep a reference to the button rect for hit testing
    _current_btn_rect = None
 
    if frozen:
        # still draw everything behind the overlay while frozen
        background.draw(screen)
        level.draw(screen)
        farmer.draw(screen)
        ide.draw(screen)
        _draw_hud(screen, level)
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
 
    # freeze the game as soon as the level ends
    if obj.status != ObjectiveStatus.PLAYING and not frozen:
        frozen = True
        command_queue.clear()
 
    # execute one command per frame once the farmer has arrived at its tile
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
    # draw HUD last so it sits on top of everything
    _draw_hud(screen, level)
 
    pygame.display.flip()
 
    frame_count += 1
    if frame_count % 30 == 0:
        print_grid(level)
 
pygame.quit()