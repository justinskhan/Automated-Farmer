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
STATE_START   = "start"
STATE_PLAYING = "playing"
game_state    = STATE_START
 
# start screen animation state
_btn_hovered      = False
_pulse_timer      = 0.0
_current_btn_rect = None
 
# in-game how to play modal state — tracks visibility, scroll offset, and the close button rect
_show_htp_ingame   = False
_htp_ingame_close  = None
_htp_scroll_offset = 0   # pixels scrolled down into the content
 
# which example panel is currently open inside the modal — None, "for", or "while"
_htp_example_open: str | None = None
 
# example code shown in the IDE-style preview panels
_EXAMPLE_CODE = {
    "for": [
        "#moves right 3 times, planting on each tile",
        "#loop runs 3 times, i goes 0, 1, 2",
        "for i in range(3):",
        "    #move one tile to the right",
        "    move(\"right\")",
        "    #plant wheat on current tile",
        "    plant(\"wheat\")",
    ],
    "while": [
        "#repeats until 5 crops have been harvested",
        "#track how many crops we have harvested",
        "harvested = 0",
        "#keep looping until we reach 5",
        "while harvested < 5:",
        "    #plant wheat on current tile",
        "    plant(\"wheat\")",
        "    #harvest the grown crop",
        "    harvest()",
        "    #count this harvest",
        "    harvested += 1",
    ],
}
 
 
def _htp_scroll(delta: int) -> None:
    """Adjust the how-to-play scroll offset by delta pixels (positive = scroll down)."""
    global _htp_scroll_offset
    _htp_scroll_offset = max(0, _htp_scroll_offset + delta)
 
 
def _draw_ide_preview(surface: pygame.Surface, x: int, y: int, w: int, lines: list[str]) -> None:
    """Draw an IDE-style code preview panel at (x, y) with the given width.
    The height is calculated from the number of lines."""
 
    # IDE color constants — match the real IDE as closely as possible
    BG          = ( 30,  30,  40)
    TITLE_BG    = ( 20,  20,  30)
    LINE_NUM_BG = ( 25,  25,  35)
    TEXT        = (220, 220, 220)
    LINE_NUM    = (100, 100, 130)
    BORDER      = ( 80,  80, 110)
    COMMENT     = (106, 153,  85)   # green for # comments like VS Code
    KEYWORD     = (197, 134, 192)   # purple for for/while/in/range
    STRING      = (206, 145, 120)   # orange for string literals
 
    TITLE_H  = 22
    LINE_H   = 17
    PADDING  = 5
    NUM_W    = 26
    font     = pygame.font.SysFont("Consolas", 13)
    font_sm  = pygame.font.SysFont("Consolas", 11)
 
    h = TITLE_H + PADDING + len(lines) * LINE_H + PADDING
 
    # outer panel
    pygame.draw.rect(surface, BG, pygame.Rect(x, y, w, h), border_radius=5)
    pygame.draw.rect(surface, BORDER, pygame.Rect(x, y, w, h), 1, border_radius=5)
 
    # title bar
    pygame.draw.rect(surface, TITLE_BG, pygame.Rect(x, y, w, TITLE_H),
                     border_top_left_radius=5, border_top_right_radius=5)
    lbl = font_sm.render("  </> Example", True, (160, 160, 200))
    surface.blit(lbl, (x + PADDING, y + (TITLE_H - lbl.get_height()) // 2))
 
    # line number sidebar
    code_top = y + TITLE_H
    pygame.draw.rect(surface, LINE_NUM_BG,
                     pygame.Rect(x, code_top, NUM_W, h - TITLE_H))
 
    code_x = x + NUM_W + PADDING
    cy     = code_top + PADDING
 
    for i, line in enumerate(lines):
        ly = cy + i * LINE_H
 
        # line number
        num_surf = font.render(str(i + 1), True, LINE_NUM)
        surface.blit(num_surf, (x + PADDING, ly))
 
        # simple syntax colouring — comment lines, then keyword scan
        if line.lstrip().startswith("#"):
            surface.blit(font.render(line, True, COMMENT), (code_x, ly))
        else:
            # tokenise by spaces to colour keywords without a full parser
            _draw_coloured_line(surface, font, line, code_x, ly,
                                TEXT, KEYWORD, STRING)
 
 
def _draw_coloured_line(surface, font, line: str, x: int, y: int,
                        col_text, col_kw, col_str) -> None:
    """Render a single code line with basic keyword and string colouring."""
    KEYWORDS = {"for", "while", "in", "range", "if", "else", "and", "or",
                "not", "True", "False", "None", "def", "return"}
 
    # simple state-machine: scan char by char for strings, then word-by-word for keywords
    # build a list of (text, color) spans
    spans: list[tuple[str, tuple]] = []
    i = 0
    word = ""
 
    def flush_word():
        nonlocal word
        if word:
            color = col_kw if word in KEYWORDS else col_text
            spans.append((word, color))
            word = ""
 
    while i < len(line):
        ch = line[i]
        if ch in ('"', "'"):
            flush_word()
            # collect the full string literal
            q   = ch
            s   = ch
            i  += 1
            while i < len(line):
                s += line[i]
                if line[i] == q:
                    i += 1
                    break
                i += 1
            spans.append((s, col_str))
        elif ch.isalnum() or ch == "_":
            word += ch
            i    += 1
        else:
            flush_word()
            spans.append((ch, col_text))
            i += 1
    flush_word()
 
    cx = x
    for text, color in spans:
        surf = font.render(text, True, color)
        surface.blit(surf, (cx, y))
        cx += surf.get_width()
 
 
def _build_htp_content(allowed: list[str]) -> list[tuple]:
    """Return a flat list of (kind, text, indent) rows for the modal."""
    rows: list[tuple] = []
 
    #Goal
    rows.append(("section", "GOAL", 0))
    rows.append(("body", "Harvest the required crops before time runs out.", 16))
 
    #Commands
    rows.append(("section", "COMMANDS", 0))
 
    #Movement subsection 
    rows.append(("sub", "Movement", 0))
    rows.append(("desc", "Moves the farmer one tile in that direction.", 16))
    rows.append(("desc", "Can't walk off the grid or onto blocked tiles.", 16))
    rows.append(("code", 'move("up")      move("down")', 16))
    rows.append(("code", 'move("left")    move("right")', 16))
 
    #Planting subsection
    rows.append(("sub", "Planting", 0))
    if "plant" in allowed:
        rows.append(("desc", "Plants that crop on the current tile. Tile must be empty.", 16))
        rows.append(("code", 'plant("wheat")  plant("corn")', 16))
        rows.append(("code", 'plant("tomato")  plant("carrot")', 16))
    else:
        rows.append(("locked", "plant()  [locked]", 16))
        rows.append(("desc", "Plants a crop on the current tile. Unlocks soon.", 16))
 
    #Harvesting subsection
    rows.append(("sub", "Harvesting", 0))
    if "harvest" in allowed:
        rows.append(("desc", "Picks the fully grown crop on the current tile. Crops must be fully grown first.", 16))
        rows.append(("code", "harvest()", 16))
    else:
        rows.append(("locked", "harvest()  [locked]", 16))
        rows.append(("desc", "Harvests the grown crop on the current tile. Unlocks soon.", 16))
 
    #Loops
    rows.append(("sub", "Loops", 0))
    if "for" in allowed:
        rows.append(("locked_example", "for i in range(n):", 16, "for"))
        rows.append(("desc", "Repeats the indented block exactly n times.", 16))
    else:
        rows.append(("locked_example", "for loops  [unlocks at level 3]", 16, "for"))
        rows.append(("desc", "Repeat a block of code a fixed number of times.", 16))
    if "while" in allowed:
        rows.append(("locked_example", "while <condition>:", 16, "while"))
        rows.append(("desc", "Keeps repeating the block as long as the condition is true.", 16))
    else:
        rows.append(("locked_example", "while loops  [unlocks at level 5]", 16, "while"))
        rows.append(("desc", "Repeat a block of code until a condition becomes false.", 16))

    # ── TIPS ──────────────────────────────────────────────────────────────────
    rows.append(("section", "TIPS", 0))
    rows.append(("body", "Crops must be fully grown before harvesting.", 16))
    rows.append(("body", "You can only plant on empty, walkable tiles.", 16))
    rows.append(("body", "New commands unlock as you progress.", 16))
 
    # ── CONTROLS ──────────────────────────────────────────────────────────────
    rows.append(("section", "CONTROLS", 0))
    rows.append(("body", "Click the Run button to play.", 16))
 
    return rows
 
 
def _draw_htp_modal_ingame(surface: pygame.Surface) -> tuple[pygame.Rect, list[tuple]]:
    """Draw the in-game How to Play modal with a scrollable content area."""
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
    font_desc    = pygame.font.SysFont("Consolas", 11)
    font_locked  = pygame.font.SysFont("Consolas", 13)
    font_btn     = pygame.font.SysFont("Consolas", 11, bold=True)
 
    # row heights per kind
    ROW_H = {
        "section":        26,
        "sub":            22,
        "code":           18,
        "desc":           16,
        "body":           18,
        "locked":         18,
        "locked_example": 18,
    }
 
    # extra height inserted when an example panel is open
    PREVIEW_TITLE_H = 22
    PREVIEW_PADDING = 5
    PREVIEW_LINE_H  = 17
 
    def _preview_h(key: str) -> int:
        lines = _EXAMPLE_CODE.get(key, [])
        return PREVIEW_TITLE_H + PREVIEW_PADDING + len(lines) * PREVIEW_LINE_H + PREVIEW_PADDING + 6
 
    # build content rows from current level's allowed commands
    rows = _build_htp_content(level.objective.allowed_commands)
 
 
    # measure total content height
    content_h = 8
    for row in rows:
        kind = row[0]
        content_h += ROW_H.get(kind, 18)
        if kind == "locked_example" and row[3] == _htp_example_open:
            content_h += _preview_h(_htp_example_open)
    content_h += 40
 
    viewport_h = mh - HEADER_H
    max_scroll = max(0, content_h - viewport_h)
    _htp_scroll_offset = min(_htp_scroll_offset, max_scroll)
 
 
    # render content onto an off-screen surface
    content_surf = pygame.Surface((CONTENT_W, content_h), pygame.SRCALPHA)
    content_surf.fill((0, 0, 0, 0))
 
    # track Example button rects in content-surface coords
    example_btns_content: list[tuple[str, pygame.Rect]] = []
 
    cy = 8
    for row in rows:
        kind = row[0]
        text = row[1]
        indent = row[2]
 
        if kind == "section":
            cy += 4
            label_surf = font_section.render(text, True, (140, 210, 110))
            pill_w = label_surf.get_width() + 12
            pill_h = label_surf.get_height() + 2
            pygame.draw.rect(content_surf, (30, 55, 25, 180),
                             pygame.Rect(0, cy - 1, pill_w, pill_h), border_radius=3)
            content_surf.blit(label_surf, (6, cy))
            cy += ROW_H["section"] - 4
 
 
        elif kind == "sub":
            label_surf = font_sub.render(text, True, (210, 190, 80))
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
 
        elif kind == "desc":
            label_surf = font_desc.render(text, True, (130, 150, 130))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["desc"]
 
        elif kind == "body":
            label_surf = _font(13).render(text, True, (190, 210, 185))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["body"]
 
 
        elif kind == "locked":
            label_surf = _font(13).render(text, True, (110, 110, 100))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["locked"]
 
        elif kind == "locked_example":
            example_key = row[3]
            label_surf  = font_locked.render(text, True, (110, 110, 100))
            content_surf.blit(label_surf, (indent, cy))
 
            btn_label   = font_btn.render("Example", True, (255, 255, 255))
            btn_w       = btn_label.get_width() + 10
            btn_h       = ROW_H["locked_example"] - 2
            btn_x       = indent + label_surf.get_width() + 10
            btn_y       = cy + (ROW_H["locked_example"] - btn_h) // 2
            btn_rect_cs = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
 
            is_open   = (_htp_example_open == example_key)
            btn_color = (60, 120, 180) if is_open else (45, 85, 130)
            pygame.draw.rect(content_surf, btn_color, btn_rect_cs, border_radius=3)
            pygame.draw.rect(content_surf, (80, 140, 200), btn_rect_cs, 1, border_radius=3)
            content_surf.blit(btn_label,
                              (btn_x + 5, btn_y + (btn_h - btn_label.get_height()) // 2))
 
            example_btns_content.append((example_key, btn_rect_cs))
            cy += ROW_H["locked_example"]
 
            if is_open:
                ph = _preview_h(example_key)
                _draw_ide_preview(content_surf, indent, cy,
                                  CONTENT_W - indent - 4,
                                  _EXAMPLE_CODE[example_key])
                cy += ph
 
    # ── draw the modal panel ───────────────────────────────────────────────────
    panel = pygame.Surface((mw, mh), pygame.SRCALPHA)
    panel.fill((20, 28, 18, 245))
    surface.blit(panel, (mx, my))
 
    pygame.draw.rect(surface, (60, 140, 60), pygame.Rect(mx, my, mw, mh), 2, border_radius=6)
 
    font_title = pygame.font.SysFont("Consolas", 20, bold=True)
    title_surf = font_title.render("How to Play", True, (160, 230, 120))
    surface.blit(title_surf, (mx + 16, my + 14))
 
    pygame.draw.line(surface, (60, 120, 60),
                     (mx + 8,      my + HEADER_H - 4),
                     (mx + mw - 8, my + HEADER_H - 4), 1)
 
    # ── blit the visible slice of the content surface ──────────────────────────
    clip_rect  = pygame.Rect(0, _htp_scroll_offset, CONTENT_W, viewport_h)
    dest_x     = CONTENT_X
    dest_y     = my + HEADER_H
 
    old_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(mx, my + HEADER_H, mw, viewport_h-18))
    surface.blit(content_surf, (dest_x, dest_y), clip_rect)
    surface.set_clip(old_clip)
 
    # subtle fade at the bottom edge
 
    # subtle fade at the bottom edge
    if _htp_scroll_offset < max_scroll:
        fade_h    = 28
        fade_h    = 28
        fade_surf = pygame.Surface((mw - 4, fade_h), pygame.SRCALPHA)
        for i in range(fade_h):
            alpha = int(200 * i / fade_h)
            pygame.draw.line(fade_surf, (20, 28, 18, alpha),
                             (0, fade_h - 1 - i), (mw - 4, fade_h - 1 - i))
        surface.blit(fade_surf, (mx + 2, my + mh - fade_h - 2))
 
    #scrollbar
    if max_scroll > 0:
        sb_x      = mx + mw - SCROLLBAR_W - 4
        sb_y      = my + HEADER_H + 2
        sb_h      = viewport_h - 4
        thumb_h   = max(20, int(sb_h * viewport_h / content_h))
        thumb_top = sb_y + int((sb_h - thumb_h) * _htp_scroll_offset / max_scroll)
 
        pygame.draw.rect(surface, (40, 50, 40), pygame.Rect(sb_x, sb_y, SCROLLBAR_W, sb_h), border_radius=4)
        pygame.draw.rect(surface, (90, 160, 80), pygame.Rect(sb_x, thumb_top, SCROLLBAR_W, thumb_h), border_radius=4)
 
    #x close 
    close_size = 28
    cx_btn     = mx + mw - close_size - 6
    cy_btn     = my + 6
    close_rect    = pygame.Rect(cx_btn, cy_btn, close_size, close_size)
    close_hovered = close_rect.collidepoint(pygame.mouse.get_pos())
 
 
    close_col = (200, 60, 60) if close_hovered else (140, 40, 40)
    pygame.draw.rect(surface, close_col, close_rect, border_radius=4)
    pygame.draw.rect(surface, (220, 80, 80), close_rect, 1, border_radius=4)
 
    cx_center = cx_btn + close_size // 2
    cy_center = cy_btn + close_size // 2
    pad = 7
    pygame.draw.line(surface, (255, 255, 255), (cx_center - pad, cy_center - pad), (cx_center + pad, cy_center + pad), 2)
    pygame.draw.line(surface, (255, 255, 255), (cx_center + pad, cy_center - pad), (cx_center - pad, cy_center + pad), 2)
 
    # convert content-surface button rects to screen-space rects
    example_btns_screen: list[tuple[str, pygame.Rect]] = []
    for key, cs_rect in example_btns_content:
        screen_rect = pygame.Rect(
            CONTENT_X + cs_rect.x,
            my + HEADER_H + cs_rect.y - _htp_scroll_offset,
            cs_rect.width,
            cs_rect.height,
        )
        example_btns_screen.append((key, screen_rect))
 
    return close_rect, example_btns_screen
 
 
def _draw_start_screen(surface: pygame.Surface, pulse: float) -> pygame.Rect:
    sw, sh = surface.get_size()
 
    surface.fill((173, 216, 230))
 
    panel_w = 520
    panel_h = 280
    panel_x = (sw - panel_w) // 2
    panel_y = (sh - panel_h) // 2 - 20
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((15, 15, 25, 210))
    surface.blit(panel_surf, (panel_x, panel_y))
 
    font_sub = pygame.font.SysFont("Consolas", 15)
    sub_surf = font_sub.render("< Learn to code through farming />", True, (100, 180, 100))
    surface.blit(sub_surf, (sw // 2 - sub_surf.get_width() // 2, panel_y + 28))
 
    font_title  = pygame.font.SysFont("Consolas", 52, bold=True)
    title_surf  = font_title.render("Automated", True, (220, 240, 200))
    title2_surf = font_title.render("Farmer",    True, (160, 210, 120))
    surface.blit(title_surf,  (sw // 2 - title_surf.get_width()  // 2, panel_y + 60))
    surface.blit(title2_surf, (sw // 2 - title2_surf.get_width() // 2, panel_y + 118))
 
    icons = [
        ((sw // 2 - 90, panel_y + 195), (210, 180, 50),  "sq"),
        ((sw // 2 - 40, panel_y + 195), (255, 220,  0),  "ci"),
        ((sw // 2 + 10, panel_y + 195), (220,  50, 50),  "ci"),
        ((sw // 2 + 60, panel_y + 195), (230, 120, 20),  "tr"),
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
 
    btn_w  = int(160 + pulse * 6)
    btn_h  = int(48  + pulse * 3)
    btn_x  = sw // 2 - btn_w // 2
    btn_y  = panel_y + panel_h + 30
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
 
    btn_color = (70, 210, 100) if _btn_hovered else (50, 180, 80)
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=6)
    pygame.draw.rect(surface, (30, 100, 50), btn_rect, 2, border_radius=6)
 
    font_btn = pygame.font.SysFont("Consolas", 20, bold=True)
    btn_label = font_btn.render("PLAY", True, (255, 255, 255))
    surface.blit(btn_label, (sw // 2 - btn_label.get_width() // 2,
                              btn_y + btn_h // 2 - btn_label.get_height() // 2))
 
    return btn_rect
 
 
_step_event = threading.Event()
_done_event = threading.Event()
_stop_event = threading.Event()
_user_thread: threading.Thread | None = None
 
 
def _stop_user_thread() -> None:
    global _user_thread
    if _user_thread and _user_thread.is_alive():
        _stop_event.set()
        _step_event.set()
        _user_thread.join(timeout=1.0)
    _user_thread = None
    _stop_event.clear()
    _step_event.clear()
    _done_event.clear()
 
 
def _wait_for_arrival() -> None:
    if _stop_event.is_set():
        raise SystemExit
    _done_event.set()
    _step_event.wait()
    _step_event.clear()
    if _stop_event.is_set():
        raise SystemExit
 
 
def _launch_user_code(code: str) -> None:
    global _user_thread
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
            pass
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
 
 
def _check_forbidden_constructs(tree: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            if "for" not in level.objective.allowed_commands:
                return "for loops are locked — reach level 3 to unlock them."
        if isinstance(node, ast.While):
            if "while" not in level.objective.allowed_commands:
                return "while loops are locked — reach level 5 to unlock them."
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "import statements are not allowed."
    return None
 
 
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
 
    panel_w = max(font_title.size(obj_lines[0])[0],
                  font_body.size(obj_lines[1])[0]) + padding * 2
    panel_h = padding * 2 + len(obj_lines) * line_h
 
    sx = surface.get_width() - panel_w - margin
    sy = margin
 
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((15, 15, 25, 190))
    surface.blit(panel_surf, (sx, sy))
 
    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(sx, sy, panel_w, panel_h), 1, border_radius=4)
 
    surface.blit(font_title.render(obj_lines[0], True, (220, 220, 255)),
                 (sx + padding, sy + padding))
 
    surface.blit(font_body.render(obj_lines[1], True, (180, 220, 180)),
                 (sx + padding, sy + padding + line_h))
 
    time_box_w = panel_w
    time_box_h = 54
    tx = sx
    ty = sy + panel_h + 6
 
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
 
    time_surf = pygame.Surface((time_box_w, time_box_h), pygame.SRCALPHA)
    time_surf.fill((15, 15, 25, 190))
    surface.blit(time_surf, (tx, ty))
 
    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(tx, ty, time_box_w, time_box_h), 1, border_radius=4)
 
    label_surf = font_label.render("TIME LEFT", True, (120, 120, 160))
    surface.blit(label_surf, (tx + padding, ty + 6))
 
    time_render = font_time.render(time_str, True, time_col)
    time_x = tx + (time_box_w - time_render.get_width()) // 2
    time_y = ty + time_box_h - time_render.get_height() - 6
    surface.blit(time_render, (time_x, time_y))
 
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
 
    font_btn = pygame.font.SysFont("Consolas", 14, bold=True)
    lbl = font_btn.render("Center IDE", True, (255, 255, 255))
    surface.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                        by + (btn_h - lbl.get_height()) // 2))
 
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
 
    font_htp = pygame.font.SysFont("Consolas", 14, bold=True)
    htp_lbl  = font_htp.render("How to Play", True, (255, 255, 255))
    surface.blit(htp_lbl, (hx + (htp_w - htp_lbl.get_width())  // 2,
                             hy + (htp_h - htp_lbl.get_height()) // 2))
 
    return center_btn_rect, htp_btn_rect, prog_rect
 
 
ide.update_allowed(level.objective.allowed_commands)
 
frame_count = 0
running     = True
frozen      = False
 
_center_btn: pygame.Rect | None = None
_htp_btn:    pygame.Rect | None = None
_htp_example_btns: list[tuple[str, pygame.Rect]] = []
 
while running:
    dt = clock.tick(60) / 1000.0
 
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
 
        elif event.type == pygame.VIDEORESIZE:
            old_w, old_h = screen.get_size()
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            if game_state == STATE_PLAYING:
                sx = event.w / old_w
                sy = event.h / old_h
                ide.rect.x      = int(ide.rect.x      * sx)
                ide.rect.y      = int(ide.rect.y      * sy)
                ide.rect.width  = max(200, int(ide.rect.width  * sx))
                ide.rect.height = max(120, int(ide.rect.height * sy))
                level.center_on(event.w, event.h)
                farmer.snap_to_tile()
 
        if game_state == STATE_START:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if _current_btn_rect and _current_btn_rect.collidepoint(event.pos):
                    game_state = STATE_PLAYING
                    level.center_on(*screen.get_size())
            continue
 
        if frozen:
            if overlay.handle_event(event):
                obj = level.objective
                if obj.status == ObjectiveStatus.WIN:
                    _advance_level()
                else:
                    _reload_level()
                frozen = False
            continue
 
        if event.type == pygame.MOUSEWHEEL and _show_htp_ingame:
            _htp_scroll(-event.y * 24)
            continue
 
        if event.type == pygame.KEYDOWN:
            if _show_htp_ingame and event.key == pygame.K_ESCAPE:
                _show_htp_ingame  = False
                _htp_example_open = None
                continue
 
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if _show_htp_ingame:
                if _htp_ingame_close and _htp_ingame_close.collidepoint(event.pos):
                    _show_htp_ingame  = False
                    _htp_example_open = None
                    continue
 
                for key, btn_rect in _htp_example_btns:
                    if btn_rect.collidepoint(event.pos):
                        if _htp_example_open == key:
                            _htp_example_open = None
                        else:
                            _htp_example_open = key
                        break
 
                continue
 
            if _center_btn and _center_btn.collidepoint(event.pos):
                ide.rect.x      = 20
                ide.rect.y      = 20
                ide.rect.width  = IDE.WIDTH
                ide.rect.height = IDE.HEIGHT
                continue
 
            if _htp_btn and _htp_btn.collidepoint(event.pos):
                _show_htp_ingame  = True
                _htp_scroll_offset = 0
                _htp_example_open  = None
                continue
 
        code = ide.handle_event(event)
        if code is not None:
            try:
                tree = ast.parse(code)
                err = _check_forbidden_constructs(tree)
                if err:
                    ide.log(f"Error: {err}", error=True)
                else:
                    ide.log("Running code...")
 
    if game_state == STATE_START:
        import math
        _pulse_timer += dt
        pulse = (math.sin(_pulse_timer * 3) + 1) / 2
        mouse_pos = pygame.mouse.get_pos()
        _current_btn_rect = _draw_start_screen(screen, pulse)
        _btn_hovered = _current_btn_rect.collidepoint(mouse_pos)
        pygame.display.flip()
        continue
 
    _current_btn_rect = None
 
    if frozen:
        background.draw(screen)
        level.draw(screen)
        farmer.draw(screen)
        ide.draw(screen)
        _center_btn, _htp_btn = _draw_hud(screen, level)
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
        _stop_user_thread()
 
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
    _center_btn, _htp_btn = _draw_hud(screen, level)
 
    if _show_htp_ingame:
        _htp_ingame_close, _htp_example_btns = _draw_htp_modal_ingame(screen)
    else:
        _htp_ingame_close  = None
        _htp_example_btns  = []
 
    pygame.display.flip()
 
    frame_count += 1
    if frame_count % 30 == 0:
        print_grid(level)
 
_stop_user_thread()
pygame.quit()