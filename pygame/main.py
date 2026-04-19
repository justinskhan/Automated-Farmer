import asyncio
import sys
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

# ---------------------------------------------------------------------------
# Browser integration — fills the pygame canvas to the whole viewport and
# keeps it in sync with browser resizes. On desktop this is all a no-op.
# ---------------------------------------------------------------------------
_IS_BROWSER = sys.platform == "emscripten"
_DEFAULT_SIZE = (1280, 720)


def _browser_viewport_size() -> tuple[int, int] | None:
    """Return the current browser viewport size, or None when not in pygbag."""
    if not _IS_BROWSER:
        return None
    try:
        import platform as _p  # pygbag injects window/document on this module
        w = int(_p.window.innerWidth)
        h = int(_p.window.innerHeight)
        if w > 0 and h > 0:
            return (w, h)
    except Exception:
        pass
    return None


def _apply_fullscreen_canvas_css() -> None:
    """Strip default pygbag margins and stretch the canvas to fill the viewport.
    Kills the gray bars pygbag normally leaves around the canvas."""
    if not _IS_BROWSER:
        return
    try:
        import platform as _p
        _p.window.eval("""
            (function() {
                var html = document.documentElement;
                var body = document.body;
                html.style.margin = '0';
                html.style.padding = '0';
                html.style.overflow = 'hidden';
                html.style.width = '100%';
                html.style.height = '100%';
                html.style.background = '#000';
                body.style.margin = '0';
                body.style.padding = '0';
                body.style.overflow = 'hidden';
                body.style.width = '100%';
                body.style.height = '100%';
                body.style.background = '#000';
                var c = document.getElementById('canvas') || document.querySelector('canvas');
                if (c) {
                    c.style.margin = '0';
                    c.style.padding = '0';
                    c.style.width = '100vw';
                    c.style.height = '100vh';
                    c.style.display = 'block';
                    c.style.position = 'absolute';
                    c.style.top = '0';
                    c.style.left = '0';
                    c.style.background = '#000';
                }
            })();
        """)
    except Exception:
        pass


_apply_fullscreen_canvas_css()

# Start at the real browser viewport size (or a sensible desktop default).
# RESIZABLE lets pygame honour future set_mode calls cleanly.
_initial_size = _browser_viewport_size() or _DEFAULT_SIZE
screen = pygame.display.set_mode(_initial_size, pygame.RESIZABLE)
pygame.display.set_caption("Automated Farmer")
clock = pygame.time.Clock()
 
# allow Ctrl+C in the terminal to quit the game cleanly
# wrapped in try/except because signal is not available in the browser/WASM environment
try:
    import signal
    signal.signal(signal.SIGINT, lambda s, f: pygame.event.post(pygame.event.Event(pygame.QUIT)))
except Exception:
    pass
 
# ---------------------------------------------------------------------------
# Font cache — pre-load all fonts once so SysFont is never called mid-frame
# calling SysFont every frame in the browser/WASM environment causes freezes
# ---------------------------------------------------------------------------
_FONTS: dict = {}
 
def _font(size: int, bold: bool = False) -> pygame.font.Font:
    """Return a cached font — loads once on first call, reuses every frame after."""
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = pygame.font.SysFont("Consolas", size, bold=bold)
    return _FONTS[key]
 
 
_FONT_SIZES: list[tuple[int, bool]] = [
    (11, False), (13, False), (13, True),
    (14, False), (14, True),  (15, False),
    (16, True),  (18, True),  (20, True),
    (22, True),  (36, True),  (52, True),
]


def _preload_fonts() -> None:
    """Force-load every font size used in the game so they are cached before gameplay."""
    for size, bold in _FONT_SIZES:
        _font(size, bold)
 
 
# ---------------------------------------------------------------------------
# Game object setup
# ---------------------------------------------------------------------------
manager = LevelManager()
manager.current.center_on(*screen.get_size())
 
level   = manager.current
farmer  = Farmer(level.start_tile, level.TILE_SIZE)
farmer.snap_to_tile()
 
background = Background(color=(173, 216, 230))
ide        = IDE(20, 20)
overlay    = Overlay()
 
# ---------------------------------------------------------------------------
# Game states
# ---------------------------------------------------------------------------
STATE_START    = "start"
STATE_LOADING  = "loading"   # loading screen shown after Play is clicked
STATE_PLAYING  = "playing"
STATE_PROGRESSION = "progression"
game_state     = STATE_START
 
# loading screen state — tracks progress across frames
_load_step        = 0       # which loading step we are currently on
_load_sub_step    = 0       # sub-step counter used inside step 1 (per-font loading)
_load_done        = False   # True once all steps are complete
_load_bar_pct     = 0.0     # 0.0 to 1.0 progress bar fill
_load_status_msg  = ""      # message shown under the bar
 
# start screen animation state
_btn_hovered      = False
_pulse_timer      = 0.0
_current_btn_rect = None
 
# in-game how to play modal state — tracks visibility, scroll offset, and the close button rect
_show_htp_ingame   = False
_htp_ingame_close  = None
_htp_scroll_offset = 0   # pixels scrolled down into the content
 
# ---------------------------------------------------------------------------
# Command queue — replaces the blocking threading approach
# ---------------------------------------------------------------------------
# Instead of running user code in a separate thread and blocking on events,
# we parse the user's code into a list of command tuples and process them
# one per frame once the farmer has arrived at each tile.
# This is fully compatible with the browser/WASM single-threaded environment.
 
# each entry is a tuple like ("move", "up") or ("plant", "wheat") or ("harvest",)
_command_queue: list[tuple] = []
 
# True while we are waiting for the farmer to finish moving before next command
_waiting_for_arrival: bool = False
 
 
def _clear_queue() -> None:
    global _command_queue, _waiting_for_arrival
    _command_queue = []
    _waiting_for_arrival = False
 
 
def _parse_code_to_queue(code: str) -> str | None:
    """Parse the user's code string into _command_queue.
    Returns an error string if parsing fails, or None on success.
    Supports: move(), plant(), harvest(), and while loops over those calls.
    """
    global _command_queue
    _clear_queue()
 
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"Syntax error: {e.msg} (line {e.lineno})"
 
    # check forbidden constructs first
    err = _check_forbidden_constructs(tree)
    if err:
        return err
 
    commands: list[tuple] = []
 
    def _process_node(node, depth: int = 0) -> str | None:
        """Recursively walk AST nodes and append commands to the list.
        Returns an error string or None."""
 
        # a sequence of statements
        if isinstance(node, list):
            for n in node:
                err = _process_node(n, depth)
                if err:
                    return err
            return None
 
        # expression statement — should be a function call
        if isinstance(node, ast.Expr):
            return _process_node(node.value, depth)
 
        # function call: move(), plant(), harvest()
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fn = node.func.id
            else:
                return "Only move(), plant(), and harvest() calls are supported."
 
            if fn == "move":
                if len(node.args) != 1:
                    return "move() takes exactly one argument e.g. move('up')"
                arg = node.args[0]
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                    return "move() argument must be a string e.g. move('up')"
                commands.append(("move", arg.value))
                return None
 
            elif fn == "plant":
                if len(node.args) != 1:
                    return "plant() takes exactly one argument e.g. plant('wheat')"
                arg = node.args[0]
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                    return "plant() argument must be a string e.g. plant('wheat')"
                commands.append(("plant", arg.value))
                return None
 
            elif fn == "harvest":
                commands.append(("harvest",))
                return None
 
            else:
                return f"Unknown command: {fn}(). Use move(), plant(), or harvest()."
 
        # while loop — unroll up to a safe limit to avoid infinite loops
        if isinstance(node, ast.While):
            cond = node.test
            if isinstance(cond, ast.Constant) and cond.value:
                repeat = 9999
            elif isinstance(cond, ast.Constant) and isinstance(cond.value, int):
                repeat = int(cond.value)
            else:
                try:
                    repeat = int(ast.literal_eval(cond))
                except Exception:
                    repeat = 9999
 
            repeat = min(repeat, 9999)
 
            loop_commands: list[tuple] = []
            saved = commands[:]
            commands.clear()
            err = _process_node(node.body, depth + 1)
            if err:
                commands[:] = saved
                return err
            iteration_commands = commands[:]
            commands[:] = saved
 
            for _ in range(repeat):
                commands.extend(iteration_commands)
            return None
 
        # ignore pass statements
        if isinstance(node, ast.Pass):
            return None
 
        return f"Unsupported statement type: {type(node).__name__}"
 
    err = _process_node(tree.body)
    if err:
        return err
 
    _command_queue = commands
    return None
 
 
def _execute_next_command() -> None:
    """Pop and execute the next command from the queue.
    Called each frame once the farmer has arrived and we are not waiting."""
    global _waiting_for_arrival
 
    if not _command_queue:
        return
 
    cmd = _command_queue.pop(0)
    _waiting_for_arrival = True
 
    if cmd[0] == "move":
        _do_move(cmd[1])
    elif cmd[0] == "plant":
        _do_plant(cmd[1])
    elif cmd[0] == "harvest":
        _do_harvest()
    else:
        _waiting_for_arrival = False
 
 
def _do_move(direction: str) -> None:
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
 
 
def _do_plant(crop_name: str) -> None:
    global _waiting_for_arrival
    if "plant" not in level.objective.allowed_commands:
        ide.log("plant() is locked on this level.", error=True)
        _waiting_for_arrival = False
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
        _waiting_for_arrival = False
        return
    tile = farmer.current_tile
    if tile.crop is not None:
        ide.log("Tile already has a crop.", error=True)
        _waiting_for_arrival = False
        return
    if not tile.plant(Crop(crop_type, start_growth=0.0)):
        ide.log("Tile is recovering, wait before replanting.", error=True)
        _waiting_for_arrival = False
        return
    ide.log(f"Planted: {crop_name}")
    _waiting_for_arrival = False   # plant is instant
 
 
def _do_harvest() -> None:
    global _waiting_for_arrival
    tile = farmer.current_tile
    if tile.crop is None:
        ide.log("No crop to harvest here.", error=True)
        _waiting_for_arrival = False
        return
    if not tile.crop.grown:
        ide.log("Crop not ready to harvest yet.", error=True)
        _waiting_for_arrival = False
        return
    ide.log(f"Harvested: {tile.crop.crop_type.name}")
    tile.remove_crop()
    level.objective.record_harvest()
    _waiting_for_arrival = False   # harvest is instant
 
 
def _check_forbidden_constructs(tree: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and not _while_loops_allowed():
            return "while loops are locked — reach level 5 to unlock them."
        if isinstance(node, (ast.For, ast.AsyncFor)):
            return "for loops are not available."
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "import statements are not allowed."
    return None
 
 
def _while_loops_allowed() -> bool:
    return "while" in level.objective.allowed_commands
 
 
def _reload_level() -> None:
    global level, farmer
    _clear_queue()
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
    _clear_queue()
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
 
 
def _htp_scroll(delta: int) -> None:
    """Adjust the how-to-play scroll offset by delta pixels (positive = scroll down)."""
    global _htp_scroll_offset
    _htp_scroll_offset = max(0, _htp_scroll_offset + delta)
 
 
def _build_htp_content(allowed: list[str]) -> list[tuple]:
    """Return a flat list of (kind, text, indent) rows for the modal."""
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
        rows.append(("code", "while True:", 16))
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
    rows.append(("body", "Click the Run button to execute your code.", 0))
 
    return rows
 
 
# ---------------------------------------------------------------------------
# Loading screen
# ---------------------------------------------------------------------------
 
def _draw_loading_screen(surface: pygame.Surface, pct: float, msg: str) -> None:
    """Draw the loading screen with a progress bar and status message."""
    sw, sh = surface.get_size()
    surface.fill((15, 20, 15))
 
    # title
    title_font = _font(36, bold=True)
    title_surf = title_font.render("Automated Farmer", True, (160, 210, 120))
    surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, sh // 2 - 100))
 
    # progress bar background
    bar_w = 400
    bar_h = 18
    bar_x = sw // 2 - bar_w // 2
    bar_y = sh // 2 - 10
    pygame.draw.rect(surface, (40, 50, 40), pygame.Rect(bar_x, bar_y, bar_w, bar_h), border_radius=6)
 
    # progress bar fill
    fill_w = int(bar_w * pct)
    if fill_w > 0:
        pygame.draw.rect(surface, (80, 180, 80), pygame.Rect(bar_x, bar_y, fill_w, bar_h), border_radius=6)
 
    # border around bar
    pygame.draw.rect(surface, (60, 120, 60), pygame.Rect(bar_x, bar_y, bar_w, bar_h), 2, border_radius=6)
 
    # percentage text
    pct_font = _font(14, bold=True)
    pct_surf = pct_font.render(f"{int(pct * 100)}%", True, (160, 220, 160))
    surface.blit(pct_surf, (sw // 2 - pct_surf.get_width() // 2, bar_y + bar_h + 10))
 
    # status message below the bar
    msg_font = _font(13)
    msg_surf = msg_font.render(msg, True, (120, 160, 120))
    surface.blit(msg_surf, (sw // 2 - msg_surf.get_width() // 2, bar_y + bar_h + 34))
 
    pygame.display.flip()
 
 
# ---------------------------------------------------------------------------
# HTP modal
# ---------------------------------------------------------------------------
 
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
 
    # row heights per kind
    ROW_H = {
        "section": 26,
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
            cy += 4
            label_surf = _font(14, bold=True).render(text, True, (140, 210, 110))
            pill_w = label_surf.get_width() + 12
            pill_h = label_surf.get_height() + 2
            pygame.draw.rect(content_surf, (30, 55, 25, 180),
                             pygame.Rect(0, cy - 1, pill_w, pill_h), border_radius=3)
            content_surf.blit(label_surf, (6, cy))
            cy += ROW_H["section"] - 4
 
        elif kind == "sub":
            label_surf = _font(13, bold=True).render(text, True, (210, 190, 80))
            content_surf.blit(label_surf, (indent, cy))
            rule_x = indent + label_surf.get_width() + 6
            rule_y = cy + label_surf.get_height() // 2
            pygame.draw.line(content_surf, (80, 70, 30),
                             (rule_x, rule_y), (CONTENT_W - 4, rule_y), 1)
            cy += ROW_H["sub"]
 
        elif kind == "code":
            label_surf = _font(13).render(text, True, (170, 215, 255))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["code"]
 
        elif kind == "body":
            label_surf = _font(13).render(text, True, (190, 210, 185))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["body"]
 
        elif kind == "locked":
            label_surf = _font(13).render(text, True, (110, 110, 100))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["locked"]
 
    # draw the modal panel
    panel = pygame.Surface((mw, mh), pygame.SRCALPHA)
    panel.fill((20, 28, 18, 245))
    surface.blit(panel, (mx, my))
 
    # green border
    pygame.draw.rect(surface, (60, 140, 60), pygame.Rect(mx, my, mw, mh), 2, border_radius=6)
 
    # title
    title_surf = _font(20, bold=True).render("How to Play", True, (160, 230, 120))
    surface.blit(title_surf, (mx + 16, my + 14))
 
    # divider below title
    pygame.draw.line(surface, (60, 120, 60),
                     (mx + 8,      my + HEADER_H - 4),
                     (mx + mw - 8, my + HEADER_H - 4), 1)
 
    # blit the visible slice of the content surface
    old_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(mx, my + HEADER_H, mw, viewport_h))
    surface.blit(content_surf, (CONTENT_X, my + HEADER_H),
                 pygame.Rect(0, _htp_scroll_offset, CONTENT_W, viewport_h))
    surface.set_clip(old_clip)
 
    # subtle fade at the bottom edge
    if _htp_scroll_offset < max_scroll:
        fade_h    = 28
        fade_surf = pygame.Surface((mw - 4, fade_h), pygame.SRCALPHA)
        for i in range(fade_h):
            alpha = int(200 * i / fade_h)
            pygame.draw.line(fade_surf, (20, 28, 18, alpha),
                             (0, fade_h - 1 - i), (mw - 4, fade_h - 1 - i))
        surface.blit(fade_surf, (mx + 2, my + mh - fade_h - 2))
 
    # scrollbar
    if max_scroll > 0:
        sb_x      = mx + mw - SCROLLBAR_W - 4
        sb_y      = my + HEADER_H + 2
        sb_h      = viewport_h - 4
        thumb_h   = max(20, int(sb_h * viewport_h / content_h))
        thumb_top = sb_y + int((sb_h - thumb_h) * _htp_scroll_offset / max_scroll)
        pygame.draw.rect(surface, (40, 50, 40),
                         pygame.Rect(sb_x, sb_y, SCROLLBAR_W, sb_h), border_radius=4)
        pygame.draw.rect(surface, (90, 160, 80),
                         pygame.Rect(sb_x, thumb_top, SCROLLBAR_W, thumb_h), border_radius=4)
 
    # X close button
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
 
 
# ---------------------------------------------------------------------------
# Start screen
# ---------------------------------------------------------------------------
 
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
    sub_surf = _font(15).render("< Learn to code through farming />", True, (100, 180, 100))
    surface.blit(sub_surf, (sw // 2 - sub_surf.get_width() // 2, panel_y + 28))
 
    # main title — large bold text
    title_surf  = _font(52, bold=True).render("Automated", True, (220, 240, 200))
    title2_surf = _font(52, bold=True).render("Farmer",    True, (160, 210, 120))
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
    btn_label = _font(20, bold=True).render("PLAY", True, (255, 255, 255))
    surface.blit(btn_label, (sw // 2 - btn_label.get_width() // 2,
                              btn_y + btn_h // 2 - btn_label.get_height() // 2))
 
    return btn_rect
 
 
# ---------------------------------------------------------------------------
# Progression screen
# ---------------------------------------------------------------------------
 
def _draw_progression_screen(surface: pygame.Surface) -> pygame.Rect:
    """Draw the level selection screen. Returns the back button rect."""
    sw, sh = surface.get_size()
    surface.fill((173, 216, 230))
 
    title_surf = _font(36, bold=True).render("Level Select", True, (30, 80, 30))
    surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, 60))
 
    # back button
    btn_w, btn_h = 160, 48
    back_rect    = pygame.Rect(sw // 2 - btn_w // 2, sh - btn_h - 40, btn_w, btn_h)
    back_hovered = back_rect.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(surface, (70, 210, 100) if back_hovered else (50, 180, 80), back_rect, border_radius=6)
    pygame.draw.rect(surface, (30, 100, 50), back_rect, 2, border_radius=6)
    lbl = _font(18, bold=True).render("Back", True, (255, 255, 255))
    surface.blit(lbl, (back_rect.centerx - lbl.get_width() // 2,
                        back_rect.centery - lbl.get_height() // 2))
 
    return back_rect
 
 
# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
 
def _draw_hud(surface: pygame.Surface, lv) -> tuple:
    """Draw the in-game HUD. Returns (center_btn_rect, htp_btn_rect, prog_btn_rect)."""
    obj        = lv.objective
    font_title = _font(16, bold=True)
    font_body  = _font(14)
    font_time  = _font(22, bold=True)
    font_label = _font(11)
 
    padding = 10
    line_h  = 20
    margin  = 12
 
    obj_lines = [f"Level {lv.number}: {lv.name}",
                 f"Harvest {obj.harvests_done}/{obj.harvests_required} crops"]
 
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
    prog_lbl = _font(13, bold=True).render("Level Select", True, (255, 255, 255))
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
 
    btn_bg_col = (30, 30, 45, 210) if btn_hovered else (15, 15, 25, 190)
    btn_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
    btn_bg.fill(btn_bg_col)
    surface.blit(btn_bg, (bx, by))
    pygame.draw.rect(surface, (80, 80, 110), center_btn_rect, 1, border_radius=4)
 
    lbl = _font(14, bold=True).render("Center IDE", True, (255, 255, 255))
    surface.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                        by + (btn_h - lbl.get_height()) // 2))
 
    # How to Play button sits directly below the Center IDE button
    htp_w = btn_w
    htp_h = btn_h
    hx    = bx
    hy    = by + btn_h + 6
 
    htp_btn_rect = pygame.Rect(hx, hy, htp_w, htp_h)
    htp_hovered  = htp_btn_rect.collidepoint(pygame.mouse.get_pos())
 
    htp_bg_col = (30, 30, 45, 210) if htp_hovered else (15, 15, 25, 190)
    htp_bg = pygame.Surface((htp_w, htp_h), pygame.SRCALPHA)
    htp_bg.fill(htp_bg_col)
    surface.blit(htp_bg, (hx, hy))
    pygame.draw.rect(surface, (80, 80, 110), htp_btn_rect, 1, border_radius=4)
 
    htp_lbl = _font(14, bold=True).render("How to Play", True, (255, 255, 255))
    surface.blit(htp_lbl, (hx + (htp_w - htp_lbl.get_width())  // 2,
                             hy + (htp_h - htp_lbl.get_height()) // 2))
 
    return center_btn_rect, htp_btn_rect, prog_rect
 
 
# ---------------------------------------------------------------------------
# IDE setup
# ---------------------------------------------------------------------------
ide.update_allowed(level.objective.allowed_commands)
 
# both HUD button rects are tracked so each can be hit-tested independently
_center_btn:    pygame.Rect | None = None
_htp_btn:       pygame.Rect | None = None
_prog_btn:      pygame.Rect | None = None
_prog_back_btn: pygame.Rect | None = None
 
 
# ---------------------------------------------------------------------------
# Main async loop
# ---------------------------------------------------------------------------
async def main():
    global screen, level, farmer, game_state
    global _btn_hovered, _pulse_timer, _current_btn_rect
    global _show_htp_ingame, _htp_ingame_close, _htp_scroll_offset
    global _center_btn, _htp_btn, _prog_btn, _prog_back_btn
    global _waiting_for_arrival, _load_step, _load_sub_step, _load_done
    global _load_bar_pct, _load_status_msg
 
    frame_count = 0
    running     = True
    frozen      = False
 
    while running:
        dt = clock.tick(60) / 1000.0

        # Browser-only: the HTML canvas is CSS-sized to the viewport, but pygame
        # still needs set_mode() to match so drawing happens at the right
        # resolution. Poll the window each frame and synthesise VIDEORESIZE
        # events on change — pygbag rarely dispatches real ones.
        if _IS_BROWSER:
            _vp = _browser_viewport_size()
            if _vp and _vp != screen.get_size():
                pygame.event.post(pygame.event.Event(
                    pygame.VIDEORESIZE, {"w": _vp[0], "h": _vp[1], "size": _vp}
                ))


        # ── Loading screen ────────────────────────────────────────────────────
        # Spread all pre-load work across multiple frames so the browser never
        # sees a long synchronous block. Each step yields before continuing.
        if game_state == STATE_LOADING:
 
            # consume any queued events so the browser stays responsive
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
 
            if _load_step == 0:
                _load_status_msg = "Loading fonts..."
                _load_bar_pct    = 0.1
                _draw_loading_screen(screen, _load_bar_pct, _load_status_msg)
                await asyncio.sleep(0)
                _load_step += 1
 
            elif _load_step == 1:
                # Load fonts one-per-frame so the browser never sees a long
                # synchronous SysFont loop (which can freeze on first-run
                # font-cache misses in pygbag/WASM).
                font_index = _load_sub_step
                if font_index < len(_FONT_SIZES):
                    size, bold = _FONT_SIZES[font_index]
                    _font(size, bold)
                    # ramp 10% -> 40% across the 12 fonts
                    _load_bar_pct    = 0.10 + 0.30 * (font_index + 1) / len(_FONT_SIZES)
                    _load_status_msg = f"Loading fonts... ({font_index + 1}/{len(_FONT_SIZES)})"
                    _draw_loading_screen(screen, _load_bar_pct, _load_status_msg)
                    await asyncio.sleep(0)
                    _load_sub_step += 1
                else:
                    _load_sub_step = 0
                    _load_status_msg = "Preparing level..."
                    _load_bar_pct    = 0.4
                    _draw_loading_screen(screen, _load_bar_pct, _load_status_msg)
                    await asyncio.sleep(0)
                    _load_step += 1
 
            elif _load_step == 2:
                # center the level and snap the farmer — done here not on the click
                sw, sh = screen.get_size()
                if sw == 0 or sh == 0:
                    sw, sh = 1280, 720
                level.center_on(sw, sh)
                farmer.snap_to_tile()
                _load_status_msg = "Setting up background..."
                _load_bar_pct    = 0.65
                _draw_loading_screen(screen, _load_bar_pct, _load_status_msg)
                await asyncio.sleep(0)
                _load_step += 1
 
            elif _load_step == 3:
                # force the background to initialise its clouds and sky cache
                background.draw(screen)
                _load_status_msg = "Almost ready..."
                _load_bar_pct    = 0.85
                _draw_loading_screen(screen, _load_bar_pct, _load_status_msg)
                await asyncio.sleep(0)
                _load_step += 1
 
            elif _load_step == 4:
                _load_status_msg = "Done!"
                _load_bar_pct    = 1.0
                _draw_loading_screen(screen, _load_bar_pct, _load_status_msg)
                await asyncio.sleep(0)
                _load_step += 1
 
            else:
                # all steps complete — switch to playing
                _load_step = 0
                game_state = STATE_PLAYING
 
            continue
 
        # ── Event handling ────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
 
            # handle window resize — fires on real desktop resizes and on the
            # synthetic events we post when the browser viewport changes
            elif event.type == pygame.VIDEORESIZE:
                try:
                    old_w, old_h = screen.get_size()
                    new_w = max(320, event.w)
                    new_h = max(240, event.h)
                    if (new_w, new_h) != (old_w, old_h):
                        screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
                        # IDE size and position are user-controlled (drag title bar
                        # + resize grip), so we deliberately do NOT scale them on
                        # window resize — scaling caused a stretching glitch where
                        # shrinking clamped the IDE at its minimum size and then
                        # growing again made it much bigger than the user had set.
                        # We only nudge the IDE back on-screen if the viewport
                        # got smaller than its current position, so it stays reachable.
                        ide.rect.x = max(0, min(ide.rect.x, max(0, new_w - 40)))
                        ide.rect.y = max(0, min(ide.rect.y, max(0, new_h - 40)))
                        # re-centre the level grid for every state, not just playing,
                        # so the loading/start/progression screens look right too
                        level.center_on(new_w, new_h)
                        farmer.snap_to_tile()
                except Exception:
                    pass
 
            # handle start screen clicks
            if game_state == STATE_START:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if _current_btn_rect and _current_btn_rect.collidepoint(event.pos):
                        # go to loading state instead of playing directly
                        game_state = STATE_LOADING
                        _load_step = 0
                        _load_sub_step = 0
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
 
            # pass events to the IDE; run button returns the code string to execute
            code = ide.handle_event(event)
            if code is not None:
                # parse the code into the command queue — no threading needed
                err = _parse_code_to_queue(code)
                if err:
                    ide.log(f"Error: {err}", error=True)
                else:
                    ide.log("Running code...")
 
        # ── Draw start screen ─────────────────────────────────────────────────
        if game_state == STATE_START:
            import math
            _pulse_timer += dt
            pulse = (math.sin(_pulse_timer * 3) + 1) / 2
            mouse_pos = pygame.mouse.get_pos()
            _current_btn_rect = _draw_start_screen(screen, pulse)
            _btn_hovered = _current_btn_rect.collidepoint(mouse_pos)
            pygame.display.flip()
            await asyncio.sleep(0)  # yield to browser each frame
            continue
 
        _current_btn_rect = None
 
        # ── Draw progression screen ───────────────────────────────────────────
        if game_state == STATE_PROGRESSION:
            _prog_back_btn = _draw_progression_screen(screen)
            pygame.display.flip()
            await asyncio.sleep(0)  # yield to browser each frame
            continue
 
        # ── Draw frozen overlay ───────────────────────────────────────────────
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
            await asyncio.sleep(0)  # yield to browser each frame
            continue
 
        # ── Game logic ────────────────────────────────────────────────────────
        obj = level.objective
        if obj.status == ObjectiveStatus.PLAYING:
            obj.update(dt)
 
        # freeze the game as soon as the level ends
        if obj.status != ObjectiveStatus.PLAYING and not frozen:
            frozen = True
            _clear_queue()
 
        # process the command queue each frame once the farmer has arrived
        if not frozen and _command_queue:
            if _waiting_for_arrival and farmer._arrived:
                # farmer has reached the target — ready for the next command
                _waiting_for_arrival = False
            if not _waiting_for_arrival:
                _execute_next_command()
 
        farmer.update(dt, level)
        ide.update(dt)
        level.update(dt, pygame.mouse.get_pos())
 
        # ── Draw playing state ────────────────────────────────────────────────
        background.draw(screen)
        level.draw(screen)
        farmer.draw(screen)
        ide.draw(screen)
        # draw HUD last so it sits on top of everything; capture both button rects for click handling
        _center_btn, _htp_btn, _prog_btn = _draw_hud(screen, level)
 
        # draw the how to play modal on top of everything if it is open; capture close button rect
        if _show_htp_ingame:
            _htp_ingame_close = _draw_htp_modal_ingame(screen)
        else:
            _htp_ingame_close = None
 
        pygame.display.flip()
        await asyncio.sleep(0)  # yield to browser each frame
 
        frame_count += 1
        if frame_count % 30 == 0:
            print_grid(level)
 
    _clear_queue()
    pygame.quit()
 
 
asyncio.run(main())