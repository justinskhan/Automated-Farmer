import pygame
import ast
import signal
import threading
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
 
# allow Ctrl+C in the terminal to quit the game cleanly
signal.signal(signal.SIGINT, lambda s, f: pygame.event.post(pygame.event.Event(pygame.QUIT)))
 
manager = LevelManager()
manager.current.center_on(*screen.get_size())
 
level   = manager.current
farmer  = Farmer(level.start_tile, level.TILE_SIZE)
farmer.snap_to_tile()
 
background = Background(color=(173, 216, 230))
ide        = IDE(20, 20)
overlay    = Overlay()
 
# game states
STATE_START       = "start"
STATE_PLAYING     = "playing"
STATE_PROGRESSION = "progression"
game_state        = STATE_START
 
# start screen animation state
_btn_hovered      = False
_pulse_timer      = 0.0
_current_btn_rect = None
 
# in-game how to play modal state — tracks visibility, scroll offset, and the close button rect
_show_htp_ingame   = False
_htp_ingame_close: pygame.Rect | None = None
_htp_scroll_offset = 0   # pixels scrolled down into the content


def _htp_scroll(delta: int) -> None:
    """Adjust the how-to-play scroll offset by delta pixels (positive = scroll down)."""
    global _htp_scroll_offset
    _htp_scroll_offset = max(0, _htp_scroll_offset + delta)


def _build_htp_content(allowed: list[str]) -> list[tuple]:
    """Return a flat list of (kind, text, indent) rows for the modal.

    kind values:
      'section'  — top-level header (e.g. GOAL, COMMANDS, TIPS, CONTROLS)
      'sub'      — subsection label inside COMMANDS (e.g. Movement)
      'code'     — a command line, indented under its subsection
      'body'     — plain descriptive text
      'locked'   — greyed-out locked command hint
    """
    rows: list[tuple] = []

    # ── GOAL ──────────────────────────────────────────────────────────────────
    rows.append(("section", "GOAL", 0))
    rows.append(("body", "Harvest the required crops before time runs out.", 0))

    # ── COMMANDS ──────────────────────────────────────────────────────────────
    rows.append(("section", "COMMANDS", 0))

    # Movement subsection — always shown, move is always unlocked
    rows.append(("sub", "Movement", 0))
    rows.append(("code", 'move("up")      move("down")', 16))
    rows.append(("code", 'move("left")    move("right")', 16))

    # Planting subsection
    rows.append(("sub", "Planting", 0))
    if "plant" in allowed:
        rows.append(("code", 'plant("wheat")  plant("corn")', 16))
        rows.append(("code", 'plant("tomato") plant("carrot")', 16))
    else:
        rows.append(("locked", "plant()  [locked]", 16))

    # Harvesting subsection
    rows.append(("sub", "Harvesting", 0))
    if "harvest" in allowed:
        rows.append(("code", "harvest()", 16))
    else:
        rows.append(("locked", "harvest()  [locked]", 16))

    # Loops subsection — show unlock hint when not yet available
    rows.append(("sub", "Loops", 0))
    if "while" in allowed:
        rows.append(("code", "while <condition>:", 16))
        rows.append(("body", "Repeat actions automatically.", 20))
    else:
        rows.append(("locked", "while loops  [unlocks at level 5]", 16))

    # ── TIPS ──────────────────────────────────────────────────────────────────
    rows.append(("section", "TIPS", 0))
    rows.append(("body", "Crops must be fully grown before harvesting.", 0))
    rows.append(("body", "You can only plant on empty, walkable tiles.", 0))
    rows.append(("body", "New commands unlock as you progress.", 0))

    # ── CONTROLS ──────────────────────────────────────────────────────────────
    rows.append(("section", "CONTROLS", 0))
    rows.append(("body", "Click the Run button to play.", 0))

    return rows


def _draw_htp_modal_ingame(surface: pygame.Surface) -> pygame.Rect:
    """Draw the in-game How to Play modal with a scrollable content area.
    Returns the X close button rect."""
    global _htp_scroll_offset

    sw, sh = surface.get_size()

    # dark semi-transparent backdrop covering the whole screen
    backdrop = pygame.Surface((sw, sh), pygame.SRCALPHA)
    backdrop.fill((0, 0, 0, 170))
    surface.blit(backdrop, (0, 0))

    # modal dimensions — height is capped so it always fits the window
    mw = 560
    mh = min(520, sh - 40)
    mx = (sw - mw) // 2
    my = (sh - mh) // 2

    # fixed header zone: title + divider
    HEADER_H    = 50
    SCROLLBAR_W = 10
    CONTENT_X   = mx + 16
    CONTENT_W   = mw - 32 - SCROLLBAR_W

    # fonts
    font_section = pygame.font.SysFont("Consolas", 14, bold=True)
    font_sub     = pygame.font.SysFont("Consolas", 13, bold=True)
    font_code    = pygame.font.SysFont("Consolas", 13)
    font_body    = pygame.font.SysFont("Consolas", 13)
    font_locked  = pygame.font.SysFont("Consolas", 13)

    # row heights per kind
    ROW_H = {
        "section": 26,   # section header gets a bit more breathing room above
        "sub":     22,
        "code":    18,
        "body":    18,
        "locked":  18,
    }

    # build content rows from current level's allowed commands
    rows = _build_htp_content(level.objective.allowed_commands)

    # measure total content height
    content_h = 8
    for kind, _, _ in rows:
        content_h += ROW_H[kind]
    content_h += 8

    viewport_h = mh - HEADER_H
    max_scroll = max(0, content_h - viewport_h)
    _htp_scroll_offset = min(_htp_scroll_offset, max_scroll)

    # render content onto an off-screen surface
    content_surf = pygame.Surface((CONTENT_W, content_h), pygame.SRCALPHA)
    content_surf.fill((0, 0, 0, 0))

    cy = 8
    for kind, text, indent in rows:
        if kind == "section":
            # small gap above each section header
            cy += 4
            # tinted pill background behind the section label
            label_surf = font_section.render(text, True, (140, 210, 110))
            pill_w = label_surf.get_width() + 12
            pill_h = label_surf.get_height() + 2
            pygame.draw.rect(content_surf, (30, 55, 25, 180),
                             pygame.Rect(0, cy - 1, pill_w, pill_h), border_radius=3)
            content_surf.blit(label_surf, (6, cy))
            cy += ROW_H["section"] - 4

        elif kind == "sub":
            # subsection label — indented, yellow-ish, with a short rule after it
            label_surf = font_sub.render(text, True, (210, 190, 80))
            content_surf.blit(label_surf, (indent, cy))
            # horizontal rule from end of label to right edge
            rule_x = indent + label_surf.get_width() + 6
            rule_y = cy + label_surf.get_height() // 2
            pygame.draw.line(content_surf, (80, 70, 30),
                             (rule_x, rule_y), (CONTENT_W - 4, rule_y), 1)
            cy += ROW_H["sub"]

        elif kind == "code":
            label_surf = font_code.render(text, True, (170, 215, 255))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["code"]

        elif kind == "body":
            label_surf = font_body.render(text, True, (190, 210, 185))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["body"]

        elif kind == "locked":
            label_surf = font_locked.render(text, True, (110, 110, 100))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["locked"]

    # ── draw the modal panel ───────────────────────────────────────────────────
    panel = pygame.Surface((mw, mh), pygame.SRCALPHA)
    panel.fill((20, 28, 18, 245))
    surface.blit(panel, (mx, my))

    # green border
    pygame.draw.rect(surface, (60, 140, 60), pygame.Rect(mx, my, mw, mh), 2, border_radius=6)

    # title
    font_title = pygame.font.SysFont("Consolas", 20, bold=True)
    title_surf = font_title.render("How to Play", True, (160, 230, 120))
    surface.blit(title_surf, (mx + 16, my + 14))

    # divider below title
    pygame.draw.line(surface, (60, 120, 60),
                     (mx + 8,      my + HEADER_H - 4),
                     (mx + mw - 8, my + HEADER_H - 4), 1)

    # ── blit the visible slice of the content surface ──────────────────────────
    clip_rect  = pygame.Rect(0, _htp_scroll_offset, CONTENT_W, viewport_h)
    dest_x     = CONTENT_X
    dest_y     = my + HEADER_H

    # clip so content never bleeds outside the modal
    old_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(mx, my + HEADER_H, mw, viewport_h))
    surface.blit(content_surf, (dest_x, dest_y), clip_rect)
    surface.set_clip(old_clip)

    # subtle fade at the bottom edge to hint there is more content
    if _htp_scroll_offset < max_scroll:
        fade_h   = 28
        fade_surf = pygame.Surface((mw - 4, fade_h), pygame.SRCALPHA)
        for i in range(fade_h):
            alpha = int(200 * i / fade_h)
            pygame.draw.line(fade_surf, (20, 28, 18, alpha), (0, fade_h - 1 - i), (mw - 4, fade_h - 1 - i))
        surface.blit(fade_surf, (mx + 2, my + mh - fade_h - 2))

    # ── scrollbar ─────────────────────────────────────────────────────────────
    if max_scroll > 0:
        sb_x      = mx + mw - SCROLLBAR_W - 4
        sb_y      = my + HEADER_H + 2
        sb_h      = viewport_h - 4
        # thumb height proportional to how much of the content is visible
        thumb_h   = max(20, int(sb_h * viewport_h / content_h))
        thumb_top = sb_y + int((sb_h - thumb_h) * _htp_scroll_offset / max_scroll)

        # track
        pygame.draw.rect(surface, (40, 50, 40), pygame.Rect(sb_x, sb_y, SCROLLBAR_W, sb_h), border_radius=4)
        # thumb
        pygame.draw.rect(surface, (90, 160, 80), pygame.Rect(sb_x, thumb_top, SCROLLBAR_W, thumb_h), border_radius=4)

    # ── X close button ─────────────────────────────────────────────────────────
    close_size = 28
    cx_btn     = mx + mw - close_size - 6
    cy_btn     = my + 6
    close_rect    = pygame.Rect(cx_btn, cy_btn, close_size, close_size)
    close_hovered = close_rect.collidepoint(pygame.mouse.get_pos())

    close_col = (200, 60, 60) if close_hovered else (140, 40, 40)
    pygame.draw.rect(surface, close_col, close_rect, border_radius=4)
    pygame.draw.rect(surface, (220, 80, 80), close_rect, 1, border_radius=4)

    pad = 8
    lx1, ly1 = cx_btn + pad, cy_btn + pad
    lx2, ly2 = cx_btn + close_size - pad, cy_btn + close_size - pad
    pygame.draw.line(surface, (255, 255, 255), (lx1, ly1), (lx2, ly2), 2)
    pygame.draw.line(surface, (255, 255, 255), (lx2, ly1), (lx1, ly2), 2)

    return close_rect
 
 
def _draw_start_screen(surface: pygame.Surface, pulse: float) -> pygame.Rect:
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
    font_title  = pygame.font.SysFont("Consolas", 52, bold=True)
    title_surf  = font_title.render("Automated", True, (220, 240, 200))
    title2_surf = font_title.render("Farmer",    True, (160, 210, 120))
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
 
 
# three threading events coordinate the user thread and the game loop
# _step_event is set by the game loop to tell the user thread the farmer arrived
# _done_event is set by the user thread to tell the game loop a command was issued
# _stop_event is set by the game loop to ask the user thread to exit cleanly
_step_event = threading.Event()
_done_event = threading.Event()
_stop_event = threading.Event()
_user_thread: threading.Thread | None = None
 
 
def _stop_user_thread() -> None:
    global _user_thread
    if _user_thread and _user_thread.is_alive():
        _stop_event.set()
        # unblock the thread in case it is waiting on _step_event
        _step_event.set()
        _user_thread.join(timeout=1.0)
    _user_thread = None
    _stop_event.clear()
    _step_event.clear()
    _done_event.clear()
 
 
def _wait_for_arrival() -> None:
    # cancellation check before blocking so a stopped thread exits immediately
    if _stop_event.is_set():
        raise SystemExit
    _done_event.set()      # tell game loop: command issued, wait for farmer
    _step_event.wait()     # block until game loop says farmer has arrived
    _step_event.clear()
    # check again after waking up in case stop was requested while waiting
    if _stop_event.is_set():
        raise SystemExit
 
 
def _launch_user_code(code: str) -> None:
    global _user_thread
    # stop any previously running thread before starting a new one
    _stop_user_thread()
 
    try:
        compiled = compile(code, "<ide>", "exec")
    except SyntaxError as e:
        ide.log(f"Syntax error: {e.msg} (line {e.lineno})", error=True)
        return
    except Exception as e:
        ide.log(f"Error: {e}", error=True)
        return
 
    def _run() -> None:
        try:
            exec(compiled, {"move": move, "plant": plant, "harvest": harvest})
        except SystemExit:
            pass  # clean stop requested by the game, not a real error
        except Exception as e:
            ide.log(f"Error: {e}", error=True)
 
    _step_event.clear()
    _done_event.clear()
    _user_thread = threading.Thread(target=_run, daemon=True)
    _user_thread.start()
 
 
def _reload_level() -> None:
    global level, farmer
    _stop_user_thread()
    manager.reload(*screen.get_size())
    level  = manager.current
    farmer = Farmer(level.start_tile, level.TILE_SIZE)
    farmer.snap_to_tile()
    ide.clear_output()
    ide.lines = [""]
    ide.cursor_row = 0
    ide.cursor_col = 0
    ide.update_allowed(level.objective.allowed_commands)
 
 
def _advance_level() -> None:
    global level, farmer
    _stop_user_thread()
    if not manager.next_level(*screen.get_size()):
        manager.reload(*screen.get_size())
    level  = manager.current
    farmer = Farmer(level.start_tile, level.TILE_SIZE)
    farmer.snap_to_tile()
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
    _wait_for_arrival()
 
 
def plant(crop_name: str) -> None:
    if "plant" not in level.objective.allowed_commands:
        ide.log("plant() is locked on this level.", error=True)
        _wait_for_arrival()
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
        _wait_for_arrival()
        return
    tile = farmer.current_tile
    if tile.crop is not None:
        ide.log("Tile already has a crop.", error=True)
        _wait_for_arrival()
        return
    if not tile.plant(Crop(crop_type, start_growth=0.0)):
        ide.log("Tile is recovering, wait before replanting.", error=True)
        _wait_for_arrival()
        return
    ide.log(f"Planted: {crop_name}")
    _wait_for_arrival()
 
 
def harvest() -> None:
    tile = farmer.current_tile
    if tile.crop is None:
        ide.log("No crop to harvest here.", error=True)
        _wait_for_arrival()
        return
    if not tile.crop.grown:
        ide.log("Crop not ready to harvest yet.", error=True)
        _wait_for_arrival()
        return
    ide.log(f"Harvested: {tile.crop.crop_type.name}")
    tile.remove_crop()
    level.objective.record_harvest()
    _wait_for_arrival()
 
 
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
 
 
def _draw_progression_screen(surface: pygame.Surface) -> pygame.Rect:
    """Draw the level selection screen. Returns the back button rect."""
    sw, sh = surface.get_size()
    surface.fill((173, 216, 230))

    font_title = pygame.font.SysFont("Consolas", 36, bold=True)
    title_surf = font_title.render("Level Select", True, (30, 80, 30))
    surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, 60))

    # back button
    btn_w, btn_h = 160, 48
    back_rect    = pygame.Rect(sw // 2 - btn_w // 2, sh - btn_h - 40, btn_w, btn_h)
    back_hovered = back_rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(surface, (70, 210, 100) if back_hovered else (50, 180, 80), back_rect, border_radius=6)
    pygame.draw.rect(surface, (30, 100, 50), back_rect, 2, border_radius=6)
    font_btn = pygame.font.SysFont("Consolas", 18, bold=True)
    lbl = font_btn.render("Back", True, (255, 255, 255))
    surface.blit(lbl, (back_rect.centerx - lbl.get_width() // 2,
                        back_rect.centery - lbl.get_height() // 2))

    return back_rect


def _draw_hud(surface: pygame.Surface, lv) -> tuple:
    """Draw the in-game HUD. Returns (center_btn_rect, htp_btn_rect, prog_btn_rect)."""
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

    # Level Select button at the very top of the HUD stack
    prog_h    = 36
    prog_rect = pygame.Rect(sx, margin, panel_w, prog_h)
    sy        = margin + prog_h + 6

    prog_hovered = prog_rect.collidepoint(pygame.mouse.get_pos())
    prog_bg      = pygame.Surface((panel_w, prog_h), pygame.SRCALPHA)
    prog_bg.fill((30, 30, 45, 210) if prog_hovered else (15, 15, 25, 190))
    surface.blit(prog_bg, (prog_rect.x, prog_rect.y))
    pygame.draw.rect(surface, (80, 80, 110), prog_rect, 1, border_radius=4)
    font_prog = pygame.font.SysFont("Consolas", 13, bold=True)
    prog_lbl  = font_prog.render("Level Select", True, (255, 255, 255))
    surface.blit(prog_lbl, (prog_rect.x + (panel_w - prog_lbl.get_width())  // 2,
                             prog_rect.y + (prog_h  - prog_lbl.get_height()) // 2))

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
 
    # Center IDE button sits directly below the time box, same width and style
    btn_w = time_box_w
    btn_h = time_box_h
    bx    = tx
    by    = ty + time_box_h + 6
 
    center_btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
    btn_hovered     = center_btn_rect.collidepoint(pygame.mouse.get_pos())
 
    # background — slightly brighter on hover to signal it is clickable
    btn_bg_col = (30, 30, 45, 210) if btn_hovered else (15, 15, 25, 190)
    btn_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
    btn_bg.fill(btn_bg_col)
    surface.blit(btn_bg, (bx, by))
 
    # border matching the rest of the HUD panels
    pygame.draw.rect(surface, (80, 80, 110), center_btn_rect, 1, border_radius=4)
 
    # white label centered in the box
    font_btn = pygame.font.SysFont("Consolas", 14, bold=True)
    lbl = font_btn.render("Center IDE", True, (255, 255, 255))
    surface.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                        by + (btn_h - lbl.get_height()) // 2))
 
    # How to Play button sits directly below the Center IDE button
    htp_w = btn_w
    htp_h = btn_h
    hx    = bx
    hy    = by + btn_h + 6
 
    htp_btn_rect = pygame.Rect(hx, hy, htp_w, htp_h)
    htp_hovered  = htp_btn_rect.collidepoint(pygame.mouse.get_pos())

    # simple dark background matching the other HUD panels, brighter on hover
    htp_bg_col = (30, 30, 45, 210) if htp_hovered else (15, 15, 25, 190)
    htp_bg = pygame.Surface((htp_w, htp_h), pygame.SRCALPHA)
    htp_bg.fill(htp_bg_col)
    surface.blit(htp_bg, (hx, hy))

    # border matching the rest of the HUD panels
    pygame.draw.rect(surface, (80, 80, 110), htp_btn_rect, 1, border_radius=4)

    # plain text label centered in the button, no icon
    font_htp = pygame.font.SysFont("Consolas", 14, bold=True)
    htp_lbl  = font_htp.render("How to Play", True, (255, 255, 255))
    surface.blit(htp_lbl, (hx + (htp_w - htp_lbl.get_width())  // 2,
                             hy + (htp_h - htp_lbl.get_height()) // 2))
    
    return center_btn_rect, htp_btn_rect, prog_rect
 
 
ide.update_allowed(level.objective.allowed_commands)
 
frame_count = 0
running     = True
frozen      = False
 
# both HUD button rects are tracked so each can be hit-tested independently
_center_btn: pygame.Rect | None = None
_htp_btn:    pygame.Rect | None = None
_prog_btn:   pygame.Rect | None = None
_prog_back_btn: pygame.Rect | None = None
 
while running:
    dt = clock.tick(60) / 1000.0
 
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
 
        elif event.type == pygame.VIDEORESIZE:
            old_w, old_h = screen.get_size()
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            if game_state == STATE_PLAYING:
                # scale the IDE proportionally so it moves with the window like the other UI
                sx = event.w / old_w
                sy = event.h / old_h
                ide.rect.x      = int(ide.rect.x      * sx)
                ide.rect.y      = int(ide.rect.y      * sy)
                ide.rect.width  = max(200, int(ide.rect.width  * sx))
                ide.rect.height = max(120, int(ide.rect.height * sy))
                level.center_on(event.w, event.h)
                farmer.snap_to_tile()
 
        # handle start screen clicks
        if game_state == STATE_START:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if _current_btn_rect and _current_btn_rect.collidepoint(event.pos):
                    game_state = STATE_PLAYING
                    level.center_on(*screen.get_size())
            continue

        # handle progression screen clicks
        if game_state == STATE_PROGRESSION:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if _prog_back_btn and _prog_back_btn.collidepoint(event.pos):
                    game_state = STATE_PLAYING
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
 
        # mouse wheel scrolls the how to play modal when it is open
        if event.type == pygame.MOUSEWHEEL and _show_htp_ingame:
            _htp_scroll(-event.y * 24)
            continue

        # Escape or X key dismisses the in-game how to play modal from the keyboard
        if event.type == pygame.KEYDOWN:
            if _show_htp_ingame and event.key in (pygame.K_ESCAPE, pygame.K_x):
                _show_htp_ingame = False
                continue
 
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # close the modal when its X button is clicked; swallow all other clicks while open
            if _show_htp_ingame:
                if _htp_ingame_close and _htp_ingame_close.collidepoint(event.pos):
                    _show_htp_ingame = False
                continue
 
            # Center IDE button — reset IDE to its original position and size
            if _center_btn and _center_btn.collidepoint(event.pos):
                ide.rect.x      = 20
                ide.rect.y      = 20
                ide.rect.width  = IDE.WIDTH
                ide.rect.height = IDE.HEIGHT
                continue
 
            # How to Play button — open the in-game modal
            if _htp_btn and _htp_btn.collidepoint(event.pos):
                _show_htp_ingame = True
                _htp_scroll_offset = 0
                continue

            # Level Select button — open the progression screen
            if _prog_btn and _prog_btn.collidepoint(event.pos):
                game_state = STATE_PROGRESSION
                continue
 
        # pass events to the IDE, run code if the run button was pressed
        code = ide.handle_event(event)
        if code is not None:
            try:
                tree = ast.parse(code)
                # check forbidden constructs before launching the thread
                err = _check_forbidden_constructs(tree)
                if err:
                    ide.log(f"Error: {err}", error=True)
                else:
                    ide.log("Running code...")
                    _launch_user_code(code)
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

    if game_state == STATE_PROGRESSION:
        _prog_back_btn = _draw_progression_screen(screen)
        pygame.display.flip()
        continue

    if frozen:
        # still draw everything behind the overlay while frozen
        background.draw(screen)
        level.draw(screen)
        farmer.draw(screen)
        ide.draw(screen)
        _center_btn, _htp_btn, _prog_btn = _draw_hud(screen, level)
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
        _stop_user_thread()
 
    # once the farmer has arrived, signal the user thread to issue its next command
    if (
        not frozen
        and _user_thread is not None
        and _user_thread.is_alive()
        and _done_event.is_set()
        and farmer._arrived
    ):
        _done_event.clear()
        _step_event.set()
 
    farmer.update(dt, level)
    ide.update(dt)
    level.update(dt, pygame.mouse.get_pos())
 
    background.draw(screen)
    level.draw(screen)
    farmer.draw(screen)
    ide.draw(screen)
    # draw HUD last so it sits on top of everything; capture both button rects for click handling
    _center_btn, _htp_btn = _draw_hud(screen, level)
 
    # draw the how to play modal on top of everything if it is open; capture close button rect
    if _show_htp_ingame:
        _htp_ingame_close = _draw_htp_modal_ingame(screen)
    else:
        _htp_ingame_close = None
 
    pygame.display.flip()
 
    frame_count += 1
    if frame_count % 30 == 0:
        print_grid(level)
 
_stop_user_thread()
pygame.quit()