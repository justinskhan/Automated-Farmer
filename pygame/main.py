import asyncio
import pygame
import ast
import math
import sys
from background import Background
from level import LevelManager
from farmer import Farmer
from ide import IDE
from crop import Crop, CropType
from debug import print_grid
from objective import ObjectiveStatus
from overlay import Overlay
import asyncio as _asyncio
import api_client
from auth_ui import AuthUI
from ui_scale import s as _s
from unlock_tree import UnlockTree
import unlock_screen as _unlock_screen

#true if running in a browser, false if running on desktop
_IS_BROWSER = sys.platform in ("emscripten", "wasi")

pygame.init() #initializes game
pygame.key.set_repeat(400, 40) #lets player hold a key and have it repeat, 400ms delay then 40ms after


def _pin_canvas_css(_plat, css_w: int, css_h: int) -> None:
    #sets the canvas display size so each pygame pixel lines up with one screen pixel
    try:
        canvas = _plat.document.querySelector("canvas")
        if canvas is not None:
            canvas.style.width  = f"{css_w}px"
            canvas.style.height = f"{css_h}px"
    except Exception:
        pass


if _IS_BROWSER:
    try:
        #platform lets us read browser window properties
        import platform as _plat
        #devicePixelRatio is how many real pixels fit in one CSS pixel (2 on retina screens)
        _dpr = float(_plat.window.devicePixelRatio) or 1.0
        #get the browser window size in CSS pixels
        _vw = int(_plat.window.innerWidth)
        _vh = int(_plat.window.innerHeight)
        #fall back to 720p if the window is too small to use
        if _vw < 320 or _vh < 240:
            _vw, _vh = 1280, 720
        #multiply by dpr so pygame renders at the real pixel count for sharp text
        _w = int(_vw * _dpr)
        _h = int(_vh * _dpr)
    except Exception:
        #if anything goes wrong just use 720p defaults
        _w, _h = 1280, 720
        _vw, _vh = 1280, 720
        _dpr = 1.0
    screen = pygame.display.set_mode((_w, _h), pygame.RESIZABLE)
    _pin_canvas_css(_plat, _vw, _vh)
else:
    #desktop just opens a plain 1280x720 window
    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)

pygame.display.set_caption("Automated Farmer")
clock = pygame.time.Clock()

#create the level manager and center the first level on screen
manager = LevelManager()
manager.current.center_on(*screen.get_size())

#grab the current level and put the farmer on the start tile
level   = manager.current
farmer  = Farmer(level.start_tile, level.TILE_SIZE)
farmer.snap_to_tile()

#create all the main game objects
background   = Background(color=(173, 216, 230))
ide          = IDE(20, 20)
overlay      = Overlay()
auth_ui      = AuthUI()
current_user = None  #stores the logged in user once auth is done
_auth_task   = None  #holds the async login/signup task while it runs
_auth_creds  = None  #browser only: stores (username, password, mode) until we can await it

#all the possible game states
STATE_START   = "start"
STATE_PLAYING = "playing"
STATE_AUTH    = "auth"
STATE_LOGIN   = "login"
STATE_SIGNUP     = "signup"
STATE_TECH_TREE  = "tech_tree"
#start on the auth screen so the player logs in first
game_state       = STATE_AUTH

#tracks if the mouse is over the play button and the pulse animation timer
_btn_hovered      = False
_pulse_timer      = 0.0
_current_btn_rect = None

#tracks whether the how to play modal is open and its scroll position
_show_htp_ingame   = False
_htp_ingame_close  = None
_htp_scroll_offset = 0

#which example code panel is open inside the how to play modal
_htp_example_open = None

#example code snippets shown when the player clicks the example button in how to play
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
    "if": [
        "#moves right if harvested is 0",
        "#moves left if harvested is 1",
        "#otherwise moves down",
        "harvested = 0",
        "if harvested == 0:",
        "    move(\"right\")",
        "elif harvested == 1:",
        "    move(\"left\")",
        "else:",
        "    move(\"down\")",
    ],
    "break": [
        "#stop looping early when a condition is met",
        "for i in range(10):",
        "    if i == 3:",
        "        break   #exit the loop immediately",
        "    move(\"right\")",
    ],
    "continue": [
        "#skip the rest of this iteration and go to next",
        "for i in range(5):",
        "    if i == 2:",
        "        continue   #skip iteration 2",
        "    move(\"right\")",
        "    plant(\"wheat\")",
    ],
}


def _htp_scroll(delta: int) -> None:
    #move the scroll position up or down, clamped so it cant go above 0
    global _htp_scroll_offset
    _htp_scroll_offset = max(0, _htp_scroll_offset + delta)


def _draw_ide_preview(surface: pygame.Surface, x: int, y: int, w: int, lines: list) -> None:
    #colors for the mini code preview panel inside how to play
    BG          = ( 30,  30,  40)
    TITLE_BG    = ( 20,  20,  30)
    LINE_NUM_BG = ( 25,  25,  35)
    TEXT        = (220, 220, 220)
    LINE_NUM    = (100, 100, 130)
    BORDER      = ( 80,  80, 110)
    COMMENT     = (106, 153,  85)
    KEYWORD     = (197, 134, 192)
    STRING      = (206, 145, 120)

    #sizes for the preview panel
    TITLE_H  = _s(22)
    LINE_H   = _s(17)
    PADDING  = _s(5)
    NUM_W    = _s(26)
    font     = pygame.font.SysFont("Consolas", _s(13))
    font_sm  = pygame.font.SysFont("Consolas", _s(11))

    #total height depends on how many lines of code there are
    h = TITLE_H + PADDING + len(lines) * LINE_H + PADDING

    #draw the background and border of the preview box
    pygame.draw.rect(surface, BG, pygame.Rect(x, y, w, h), border_radius=_s(5))
    pygame.draw.rect(surface, BORDER, pygame.Rect(x, y, w, h), _s(1), border_radius=_s(5))

    #draw the title bar at the top of the preview
    pygame.draw.rect(surface, TITLE_BG, pygame.Rect(x, y, w, TITLE_H),
                     border_top_left_radius=_s(5), border_top_right_radius=_s(5))
    lbl = font_sm.render("  </> Example", True, (160, 160, 200))
    surface.blit(lbl, (x + PADDING, y + (TITLE_H - lbl.get_height()) // 2))

    #draw the line number gutter on the left
    code_top = y + TITLE_H
    pygame.draw.rect(surface, LINE_NUM_BG,
                     pygame.Rect(x, code_top, NUM_W, h - TITLE_H))

    code_x = x + NUM_W + PADDING
    cy     = code_top + PADDING

    #draw each line of the example code
    for i, line in enumerate(lines):
        ly = cy + i * LINE_H
        #draw the line number
        num_surf = font.render(str(i + 1), True, LINE_NUM)
        surface.blit(num_surf, (x + PADDING, ly))

        #comments get a different color, other lines get keyword coloring
        if line.lstrip().startswith("#"):
            surface.blit(font.render(line, True, COMMENT), (code_x, ly))
        else:
            _draw_coloured_line(surface, font, line, code_x, ly, TEXT, KEYWORD, STRING)


def _draw_coloured_line(surface, font, line: str, x: int, y: int,
                        col_text, col_kw, col_str) -> None:
    #all python keywords that should be highlighted in a different color
    KEYWORDS = {"for", "while", "in", "range", "if", "else", "and", "or",
                "not", "True", "False", "None", "def", "return",
                "break", "continue", "elif"}

    spans = []
    i = 0
    word = ""

    def flush_word():
        #finish the current word and decide if it is a keyword or plain text
        nonlocal word
        if word:
            color = col_kw if word in KEYWORDS else col_text
            spans.append((word, color))
            word = ""

    #walk through each character and group them into colored spans
    while i < len(line):
        ch = line[i]
        if ch in ('"', "'"):
            #found a string, collect everything until the closing quote
            flush_word()
            q  = ch
            s  = ch
            i += 1
            while i < len(line):
                s += line[i]
                if line[i] == q:
                    i += 1
                    break
                i += 1
            spans.append((s, col_str))
        elif ch.isalnum() or ch == "_":
            #build up a word character by character
            word += ch
            i    += 1
        else:
            #non-word character, flush the word and add the character as plain text
            flush_word()
            spans.append((ch, col_text))
            i += 1
    flush_word()

    #draw each span one after another so they line up correctly
    cx = x
    for text, color in spans:
        surf = font.render(text, True, color)
        surface.blit(surf, (cx, y))
        cx += surf.get_width()


def _build_htp_content(allowed: list) -> list:
    #builds the list of rows that make up the how to play modal content
    #each row is a tuple of (kind, text, indent) or (kind, text, indent, example_key)
    rows = []

    rows.append(("section", "GOAL", 0))
    rows.append(("body", "Harvest the required crops before time runs out.", 16))

    rows.append(("section", "COMMANDS", 0))

    #movement is always available
    rows.append(("sub", "Movement", 0))
    rows.append(("desc", "Moves the farmer one tile in that direction.", 16))
    rows.append(("desc", "Can't walk off the grid or onto blocked tiles.", 16))
    rows.append(("code", 'move("up")      move("down")', 16))
    rows.append(("code", 'move("left")    move("right")', 16))

    #show plant as available or locked depending on the level
    rows.append(("sub", "Planting", 0))
    if "plant" in allowed:
        rows.append(("desc", "Plants that crop on the current tile. Tile must be empty.", 16))
        rows.append(("code", 'plant("wheat")  plant("corn")', 16))
        rows.append(("code", 'plant("tomato")  plant("carrot")', 16))
    else:
        rows.append(("locked", "plant()  [locked]", 16))
        rows.append(("desc", "Plants a crop on the current tile. Unlocks soon.", 16))

    #show harvest as available or locked depending on the level
    rows.append(("sub", "Harvesting", 0))
    if "harvest" in allowed:
        rows.append(("desc", "Picks the fully grown crop on the current tile. Crops must be fully grown first.", 16))
        rows.append(("code", "harvest()", 16))
    else:
        rows.append(("locked", "harvest()  [locked]", 16))
        rows.append(("desc", "Harvests the grown crop on the current tile. Unlocks soon.", 16))

    #show remove as available or locked depending on the level
    rows.append(("sub", "Removing", 0))
    if "remove" in allowed:
        rows.append(("desc", "Removes the crop on the current tile without harvesting it.", 16))
        rows.append(("code", "remove()", 16))
    else:
        rows.append(("locked", "remove()  [locked]", 16))
        rows.append(("desc", "Removes a crop from the current tile without harvesting. Unlocks soon.", 16))

    #conditionals are always available, just show the syntax
    rows.append(("sub", "Conditionals", 0))
    rows.append(("desc", "Run a block of code only when a condition is true.", 16))
    rows.append(("locked_example", "if <condition>:", 16, "if"))
    rows.append(("desc", "Use elif for extra conditions, else as a fallback.", 16))

    #show for loops as available or locked depending on the level
    rows.append(("sub", "Loops", 0))
    if "for" in allowed:
        rows.append(("locked_example", "for i in range(n):", 16, "for"))
        rows.append(("desc", "Repeats the indented block exactly n times.", 16))
    else:
        rows.append(("locked_example", "for loops  [unlocks at level 3]", 16, "for"))
        rows.append(("desc", "Repeat a block of code a fixed number of times.", 16))

    #show while loops as available or locked depending on the level
    if "while" in allowed:
        rows.append(("locked_example", "while <condition>:", 16, "while"))
        rows.append(("desc", "Keeps repeating the block as long as the condition is true.", 16))
    else:
        rows.append(("locked_example", "while loops  [unlocks at level 5]", 16, "while"))
        rows.append(("desc", "Repeat a block of code until a condition becomes false.", 16))

    #break and continue work inside any loop so always show them
    rows.append(("sub", "Loop Control", 0))
    rows.append(("locked_example", "break", 16, "break"))
    rows.append(("desc", "Exits the current loop immediately.", 16))
    rows.append(("locked_example", "continue", 16, "continue"))
    rows.append(("desc", "Skips the rest of this iteration and moves to the next.", 16))

    rows.append(("section", "TIPS", 0))
    rows.append(("body", "Crops must be fully grown before harvesting.", 16))
    rows.append(("body", "You can only plant on empty, walkable tiles.", 16))
    rows.append(("body", "Use remove() to clear a crop you don't want to harvest.", 16))
    rows.append(("body", "New commands unlock as you progress.", 16))

    rows.append(("section", "CONTROLS", 0))
    rows.append(("body", "Click the Run button to play.", 16))

    return rows


def _draw_htp_modal_ingame(surface: pygame.Surface):
    #draws the how to play popup over the game
    global _htp_scroll_offset

    sw, sh = surface.get_size()

    #dim the game behind the modal with a semi transparent black overlay
    backdrop = pygame.Surface((sw, sh), pygame.SRCALPHA)
    backdrop.fill((0, 0, 0, 170))
    surface.blit(backdrop, (0, 0))

    #size and position the modal panel in the center of the screen
    mw = _s(560)
    mh = min(_s(520), sh - _s(40))
    mx = (sw - mw) // 2
    my = (sh - mh) // 2

    HEADER_H    = _s(50)   #height of the title bar at the top
    SCROLLBAR_W = _s(10)   #width of the scrollbar on the right
    CONTENT_X   = mx + _s(16)
    CONTENT_W   = mw - _s(32) - SCROLLBAR_W

    #fonts for each type of row in the modal
    font_section = pygame.font.SysFont("Consolas", _s(14), bold=True)
    font_sub     = pygame.font.SysFont("Consolas", _s(13), bold=True)
    font_code    = pygame.font.SysFont("Consolas", _s(13))
    font_body    = pygame.font.SysFont("Consolas", _s(13))
    font_desc    = pygame.font.SysFont("Consolas", _s(11))
    font_locked  = pygame.font.SysFont("Consolas", _s(13))
    font_btn     = pygame.font.SysFont("Consolas", _s(11), bold=True)

    #height of each row type so we know how far to move down after drawing it
    ROW_H = {
        "section":        _s(26),
        "sub":            _s(22),
        "code":           _s(18),
        "desc":           _s(16),
        "body":           _s(18),
        "locked":         _s(18),
        "locked_example": _s(18),
    }

    #sizes used when an example code panel is expanded
    PREVIEW_TITLE_H = _s(22)
    PREVIEW_PADDING = _s(5)
    PREVIEW_LINE_H  = _s(17)

    def _preview_h(key: str) -> int:
        #calculate how tall the expanded example panel will be
        lines = _EXAMPLE_CODE.get(key, [])
        return PREVIEW_TITLE_H + PREVIEW_PADDING + len(lines) * PREVIEW_LINE_H + PREVIEW_PADDING + 6

    rows = _build_htp_content(level.objective.allowed_commands)

    #add up the total height of all rows so we know how much scrolling is needed
    content_h = 8
    for row in rows:
        kind = row[0]
        content_h += ROW_H.get(kind, 18)
        #if an example is open add its extra height
        if kind == "locked_example" and row[3] == _htp_example_open:
            content_h += _preview_h(_htp_example_open)
    content_h += 40

    viewport_h = mh - HEADER_H
    max_scroll = max(0, content_h - viewport_h)
    #clamp scroll so it doesnt go past the bottom
    _htp_scroll_offset = min(_htp_scroll_offset, max_scroll)

    #draw everything onto an offscreen surface so we can clip it to the viewport
    content_surf = pygame.Surface((CONTENT_W, content_h), pygame.SRCALPHA)
    content_surf.fill((0, 0, 0, 0))

    #collect example button rects so we can check clicks after drawing
    example_btns_content = []

    cy = 8
    for row in rows:
        kind   = row[0]
        text   = row[1]
        indent = row[2]

        if kind == "section":
            #section headers get a small green pill background
            cy += 4
            label_surf = font_section.render(text, True, (140, 210, 110))
            pill_w = label_surf.get_width() + 12
            pill_h = label_surf.get_height() + 2
            pygame.draw.rect(content_surf, (30, 55, 25, 180),
                             pygame.Rect(0, cy - 1, pill_w, pill_h), border_radius=3)
            content_surf.blit(label_surf, (6, cy))
            cy += ROW_H["section"] - 4

        elif kind == "sub":
            #sub headers have a horizontal rule drawn to the right of the text
            label_surf = font_sub.render(text, True, (210, 190, 80))
            content_surf.blit(label_surf, (indent, cy))
            rule_x = indent + label_surf.get_width() + 6
            rule_y = cy + label_surf.get_height() // 2
            pygame.draw.line(content_surf, (80, 70, 30),
                             (rule_x, rule_y), (CONTENT_W - 4, rule_y), 1)
            cy += ROW_H["sub"]

        elif kind == "code":
            #code rows are shown in blue so they stand out from descriptions
            label_surf = font_code.render(text, True, (170, 215, 255))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["code"]

        elif kind == "desc":
            #description rows are smaller and dimmer, just supporting info
            label_surf = font_desc.render(text, True, (130, 150, 130))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["desc"]

        elif kind == "body":
            #body rows are normal sized tip text
            label_surf = font_body.render(text, True, (190, 210, 185))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["body"]

        elif kind == "locked":
            #locked rows are grayed out to show the command isnt available yet
            label_surf = font_locked.render(text, True, (110, 110, 100))
            content_surf.blit(label_surf, (indent, cy))
            cy += ROW_H["locked"]

        elif kind == "locked_example":
            #locked example rows show the syntax plus a clickable example button
            example_key = row[3]
            label_surf  = font_locked.render(text, True, (110, 110, 100))
            content_surf.blit(label_surf, (indent, cy))

            #draw the example button next to the text
            btn_label   = font_btn.render("Example", True, (255, 255, 255))
            btn_w       = btn_label.get_width() + 10
            btn_h       = ROW_H["locked_example"] - 2
            btn_x       = indent + label_surf.get_width() + 10
            btn_y       = cy + (ROW_H["locked_example"] - btn_h) // 2
            btn_rect_cs = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

            #highlight the button if its example is currently open
            is_open   = (_htp_example_open == example_key)
            btn_color = (60, 120, 180) if is_open else (45, 85, 130)
            pygame.draw.rect(content_surf, btn_color, btn_rect_cs, border_radius=3)
            pygame.draw.rect(content_surf, (80, 140, 200), btn_rect_cs, 1, border_radius=3)
            content_surf.blit(btn_label,
                              (btn_x + 5, btn_y + (btn_h - btn_label.get_height()) // 2))

            example_btns_content.append((example_key, btn_rect_cs))
            cy += ROW_H["locked_example"]

            #if this example is open draw the code preview right below it
            if is_open:
                ph = _preview_h(example_key)
                _draw_ide_preview(content_surf, indent, cy,
                                  CONTENT_W - indent - 4,
                                  _EXAMPLE_CODE[example_key])
                cy += ph

    #draw the modal background panel
    panel = pygame.Surface((mw, mh), pygame.SRCALPHA)
    panel.fill((20, 28, 18, 245))
    surface.blit(panel, (mx, my))

    #draw the green border around the modal
    pygame.draw.rect(surface, (60, 140, 60), pygame.Rect(mx, my, mw, mh), _s(2), border_radius=_s(6))

    #draw the how to play title at the top
    font_title = pygame.font.SysFont("Consolas", _s(20), bold=True)
    title_surf = font_title.render("How to Play", True, (160, 230, 120))
    surface.blit(title_surf, (mx + _s(16), my + _s(14)))

    #divider line below the header
    pygame.draw.line(surface, (60, 120, 60),
                     (mx + 8,      my + HEADER_H - 4),
                     (mx + mw - 8, my + HEADER_H - 4), 1)

    #blit only the visible slice of the content surface using the scroll offset
    clip_rect = pygame.Rect(0, _htp_scroll_offset, CONTENT_W, viewport_h)
    dest_x    = CONTENT_X
    dest_y    = my + HEADER_H

    old_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(mx, my + HEADER_H, mw, viewport_h - 18))
    surface.blit(content_surf, (dest_x, dest_y), clip_rect)
    surface.set_clip(old_clip)

    #draw a fade gradient at the bottom when there is more content to scroll to
    if _htp_scroll_offset < max_scroll:
        fade_h    = 28
        fade_surf = pygame.Surface((mw - 4, fade_h), pygame.SRCALPHA)
        for i in range(fade_h):
            alpha = int(200 * i / fade_h)
            pygame.draw.line(fade_surf, (20, 28, 18, alpha),
                             (0, fade_h - 1 - i), (mw - 4, fade_h - 1 - i))
        surface.blit(fade_surf, (mx + 2, my + mh - fade_h - 2))

    #draw the scrollbar if the content is taller than the viewport
    if max_scroll > 0:
        sb_x      = mx + mw - SCROLLBAR_W - 4
        sb_y      = my + HEADER_H + 2
        sb_h      = viewport_h - 4
        #thumb size is proportional to how much of the content is visible
        thumb_h   = max(20, int(sb_h * viewport_h / content_h))
        thumb_top = sb_y + int((sb_h - thumb_h) * _htp_scroll_offset / max_scroll)

        pygame.draw.rect(surface, (40, 50, 40), pygame.Rect(sb_x, sb_y, SCROLLBAR_W, sb_h), border_radius=4)
        pygame.draw.rect(surface, (90, 160, 80), pygame.Rect(sb_x, thumb_top, SCROLLBAR_W, thumb_h), border_radius=4)

    #draw the close button in the top right corner of the modal
    close_size    = _s(28)
    cx_btn        = mx + mw - close_size - _s(6)
    cy_btn        = my + _s(6)
    close_rect    = pygame.Rect(cx_btn, cy_btn, close_size, close_size)
    close_hovered = close_rect.collidepoint(pygame.mouse.get_pos())

    #brighten the button when hovered
    close_col = (200, 60, 60) if close_hovered else (140, 40, 40)
    pygame.draw.rect(surface, close_col, close_rect, border_radius=_s(4))
    pygame.draw.rect(surface, (220, 80, 80), close_rect, _s(1), border_radius=_s(4))

    #draw the X lines on the close button
    cx_center = cx_btn + close_size // 2
    cy_center = cy_btn + close_size // 2
    pad = _s(7)
    pygame.draw.line(surface, (255, 255, 255),
                     (cx_center - pad, cy_center - pad), (cx_center + pad, cy_center + pad), _s(2))
    pygame.draw.line(surface, (255, 255, 255),
                     (cx_center + pad, cy_center - pad), (cx_center - pad, cy_center + pad), _s(2))

    #convert example button rects from content surface coords to real screen coords
    example_btns_screen = []
    for key, cs_rect in example_btns_content:
        screen_rect = pygame.Rect(
            CONTENT_X + cs_rect.x,
            my + HEADER_H + cs_rect.y - _htp_scroll_offset,
            cs_rect.width,
            cs_rect.height,
        )
        example_btns_screen.append((key, screen_rect))

    #return the close button rect and example button rects so main can check clicks
    return close_rect, example_btns_screen


def _draw_start_screen(surface: pygame.Surface, pulse: float) -> pygame.Rect:
    #draws the title screen with the game name and a pulsing play button
    sw, sh = surface.get_size()

    surface.fill((173, 216, 230))

    #center the dark panel behind the title
    panel_w = _s(520)
    panel_h = _s(280)
    panel_x = (sw - panel_w) // 2
    panel_y = (sh - panel_h) // 2 - _s(20)
    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((15, 15, 25, 210))
    surface.blit(panel_surf, (panel_x, panel_y))

    #draw the tagline above the title
    font_sub = pygame.font.SysFont("Consolas", _s(15))
    sub_surf = font_sub.render("< Learn to code through farming />", True, (100, 180, 100))
    surface.blit(sub_surf, (sw // 2 - sub_surf.get_width() // 2, panel_y + _s(28)))

    #draw the two lines of the title
    font_title  = pygame.font.SysFont("Consolas", _s(52), bold=True)
    title_surf  = font_title.render("Automated", True, (220, 240, 200))
    title2_surf = font_title.render("Farmer",    True, (160, 210, 120))
    surface.blit(title_surf,  (sw // 2 - title_surf.get_width()  // 2, panel_y + _s(60)))
    surface.blit(title2_surf, (sw // 2 - title2_surf.get_width() // 2, panel_y + _s(118)))

    #draw small crop icons below the title as decoration
    icons = [
        ((sw // 2 - _s(90), panel_y + _s(195)), (210, 180, 50),  "sq"),
        ((sw // 2 - _s(40), panel_y + _s(195)), (255, 220,  0),  "ci"),
        ((sw // 2 + _s(10), panel_y + _s(195)), (220,  50, 50),  "ci"),
        ((sw // 2 + _s(60), panel_y + _s(195)), (230, 120, 20),  "tr"),
    ]
    for (ix, iy), col, shape in icons:
        if shape == "sq":
            pygame.draw.rect(surface, col, pygame.Rect(ix - _s(10), iy - _s(10), _s(20), _s(20)), border_radius=_s(3))
            pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(ix - _s(10), iy - _s(10), _s(20), _s(20)), _s(1), border_radius=_s(3))
        elif shape == "ci":
            pygame.draw.circle(surface, col, (ix, iy), _s(10))
            pygame.draw.circle(surface, (0, 0, 0), (ix, iy), _s(10), _s(1))
        elif shape == "tr":
            pts = [(ix, iy - _s(11)), (ix - _s(10), iy + _s(9)), (ix + _s(10), iy + _s(9))]
            pygame.draw.polygon(surface, col, pts)
            pygame.draw.polygon(surface, (0, 0, 0), pts, _s(1))

    #play button pulses in size using the pulse value passed in from the main loop
    btn_w    = int(_s(160) + pulse * _s(6))
    btn_h    = int(_s(48)  + pulse * _s(3))
    btn_x    = sw // 2 - btn_w // 2
    btn_y    = panel_y + panel_h + _s(30)
    btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

    btn_color = (70, 210, 100) if _btn_hovered else (50, 180, 80)
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=_s(6))
    pygame.draw.rect(surface, (30, 100, 50), btn_rect, _s(2), border_radius=_s(6))

    font_btn  = pygame.font.SysFont("Consolas", _s(20), bold=True)
    btn_label = font_btn.render("PLAY", True, (255, 255, 255))
    surface.blit(btn_label, (sw // 2 - btn_label.get_width() // 2,
                              btn_y + btn_h // 2 - btn_label.get_height() // 2))

    return btn_rect


# ---------------------------------------------------------------------------
# user code runs in a thread on desktop so the farmer animates between steps
# in the browser threading isnt available so we record actions first then
# replay them one per frame in the main loop
# ---------------------------------------------------------------------------

#only import threading on desktop, browser doesnt support it
if not _IS_BROWSER:
    import threading as _threading

#events used on desktop to pause the thread between each farmer step
_step_event  = None  #main loop sets this to let the thread run the next command
_done_event  = None  #thread sets this when a command is done and it wants to pause
_stop_event  = None  #main loop sets this to kill the thread early
_user_thread = None  #holds the running thread so we can stop it later

#browser stores all actions in a list and replays them one at a time
_pending_actions: list = []
_action_index: int = 0


def _init_events():
    #create the threading events, only runs on desktop
    global _step_event, _done_event, _stop_event
    if not _IS_BROWSER:
        import threading
        _step_event = threading.Event()
        _done_event = threading.Event()
        _stop_event = threading.Event()


_init_events()


def _stop_user_thread() -> None:
    #kill the running user thread and reset all state
    global _user_thread, _pending_actions, _action_index
    if _IS_BROWSER:
        #browser just clears the action list
        _pending_actions = []
        _action_index = 0
        return
    #tell the thread to stop then wait for it to finish
    if _user_thread and _user_thread.is_alive():
        _stop_event.set()
        _step_event.set()  #unblock it so it can check the stop flag
        _user_thread.join(timeout=1.0)
    _user_thread = None
    _stop_event.clear()
    _step_event.clear()
    _done_event.clear()


def _wait_for_arrival() -> None:
    #called by each command on desktop to pause until the farmer finishes moving
    if _IS_BROWSER:
        return  #browser handles this differently in the main loop
    if _stop_event.is_set():
        raise SystemExit  #exit the thread cleanly if stop was requested
    _done_event.set()      #tell the main loop this command is done
    _step_event.wait()     #wait for the main loop to say go again
    _step_event.clear()
    if _stop_event.is_set():
        raise SystemExit   #check again in case stop was set while waiting


def _launch_user_code(code: str) -> None:
    #compile and run the players code, either in a thread or by recording actions
    global _user_thread, _pending_actions, _action_index

    if _IS_BROWSER:
        #browser path: run the code but swap the real commands for recorders
        #this collects all actions into a list without actually moving the farmer
        _pending_actions = []
        _action_index = 0
        try:
            compiled = compile(code, "<ide>", "exec")
            exec(compiled, {
                "move":    _record_move,
                "plant":   _record_plant,
                "harvest": _record_harvest,
                "remove":  _record_remove,
            })
        except SyntaxError as e:
            ide.log(f"Syntax error: {e.msg} (line {e.lineno})", error=True)
        except Exception as e:
            ide.log(f"Error: {e}", error=True)
        return

    #desktop path: stop any old thread then start a new one
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
        #this runs in the background thread, giving the player access to all commands
        try:
            exec(compiled, {
                "move":    move,
                "plant":   plant,
                "harvest": harvest,
                "remove":  remove,
            })
        except SystemExit:
            pass  #thread was stopped cleanly
        except Exception as e:
            ide.log(f"Error: {e}", error=True)

    _step_event.clear()
    _done_event.clear()
    _user_thread = _threading.Thread(target=_run, daemon=True)
    _user_thread.start()


# ---------------------------------------------------------------------------
# browser recorder functions replace the real commands during exec in the
# browser so we can collect all actions and replay them one per frame
# ---------------------------------------------------------------------------

def _record_move(direction: str) -> None:
    #store a move action to replay later
    _pending_actions.append(("move", direction))

def _record_plant(crop_name: str) -> None:
    #store a plant action to replay later
    _pending_actions.append(("plant", crop_name))

def _record_harvest() -> None:
    #store a harvest action to replay later
    _pending_actions.append(("harvest", None))

def _record_remove() -> None:
    #store a remove action to replay later
    _pending_actions.append(("remove", None))


def _tick_browser_actions() -> bool:
    #called once per frame in the browser to play the next action if the farmer is ready
    #returns true if there are still actions left to run
    global _action_index
    if _action_index >= len(_pending_actions):
        return False  #all done
    if not farmer._arrived:
        return True  #farmer is still moving, wait for them to finish
    action, arg = _pending_actions[_action_index]
    _action_index += 1
    #run the real command now that the farmer is in position
    if action == "move":
        move(arg)
    elif action == "plant":
        plant(arg)
    elif action == "harvest":
        harvest()
    elif action == "remove":
        remove()
    return _action_index < len(_pending_actions)


def _reload_level() -> None:
    #restart the current level from scratch and clear the ide
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
    ide.update_allowed(unlock_tree.effective_commands(level.objective.allowed_commands))


def _advance_level() -> None:
    #move to the next level, or reload the last level if there are no more
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
    ide.update_allowed(unlock_tree.effective_commands(level.objective.allowed_commands))


def move(direction: str) -> None:
    #move the farmer one tile in the given direction if the tile is walkable
    pos = level.find_tile(farmer.current_tile)
    if pos is None:
        return
    r, c = pos
    #map direction strings to row and col changes
    deltas = {
        "up":    (-1,  0),
        "down":  ( 1,  0),
        "left":  ( 0, -1),
        "right": ( 0,  1),
    }
    dr, dc = deltas.get(direction.lower(), (0, 0))
    target = level.get_tile(r + dr, c + dc)
    if target and target.walkable:
        #set the farmers destination and mark them as not yet arrived
        farmer.current_tile = target
        farmer._target_pos  = [float(target.rect.centerx), float(target.rect.centery)]
        farmer._arrived     = False
    if not _IS_BROWSER:
        _wait_for_arrival()  #pause until the farmer finishes the move animation


def plant(crop_name: str) -> None:
    #plant a crop on the farmers current tile
    if "plant" not in level.objective.allowed_commands:
        ide.log("plant() is locked on this level.", error=True)
        if not _IS_BROWSER:
            _wait_for_arrival()
        return
    #map crop name strings to crop types
    crop_map = {
        "wheat":  CropType.WHEAT,
        "corn":   CropType.CORN,
        "tomato": CropType.TOMATO,
        "carrot": CropType.CARROT,
    }
    crop_type = crop_map.get(crop_name.lower())
    if crop_type is None:
        ide.log(f"Unknown crop: {crop_name}", error=True)
        if not _IS_BROWSER:
            _wait_for_arrival()
        return
    tile = farmer.current_tile
    #cant plant if tile already has a crop
    if tile.crop is not None:
        ide.log("Tile already has a crop.", error=True)
        if not _IS_BROWSER:
            _wait_for_arrival()
        return
    #cant plant if tile is still recovering from the last crop
    if not tile.plant(Crop(crop_type, start_growth=0.0)):
        ide.log("Tile is recovering, wait before replanting.", error=True)
        if not _IS_BROWSER:
            _wait_for_arrival()
        return
    ide.log(f"Planted: {crop_name}")
    if not _IS_BROWSER:
        _wait_for_arrival()


def harvest() -> None:
    #pick the grown crop on the farmers current tile and count it toward the goal
    tile = farmer.current_tile
    if tile.crop is None:
        ide.log("No crop to harvest here.", error=True)
        if not _IS_BROWSER:
            _wait_for_arrival()
        return
    #crop must be fully grown before it can be harvested
    if not tile.crop.grown:
        ide.log("Crop not ready to harvest yet.", error=True)
        if not _IS_BROWSER:
            _wait_for_arrival()
        return
    crop_name = tile.crop.crop_type.name.lower()
    ide.log(f"Harvested: {tile.crop.crop_type.name}")
    tile.remove_crop()
    #tell the objective a harvest happened so it can track progress
    level.objective.record_harvest(crop_name)
    if not _IS_BROWSER:
        _wait_for_arrival()


def remove() -> None:
    #remove the crop on the farmers current tile without counting it as a harvest
    tile = farmer.current_tile
    if tile.crop is None:
        ide.log("No crop to remove here.", error=True)
        if not _IS_BROWSER:
            _wait_for_arrival()
        return
    crop_name = tile.crop.crop_type.name.lower()
    ide.log(f"Removed: {crop_name}")
    #remove the crop from the tile but dont tell the objective
    tile.remove_crop()
    if not _IS_BROWSER:
        _wait_for_arrival()


def _check_forbidden_constructs(tree: ast.AST):
    #walk the ast and block any constructs that arent allowed on this level
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if not unlock_tree.is_unlocked("if"):
                return "if/else is not unlocked yet — open the Unlocks screen."
        if isinstance(node, (ast.For, ast.AsyncFor)):
            if not unlock_tree.is_unlocked("for"):
                return "for loops are not unlocked yet — open the Unlocks screen."
        if isinstance(node, ast.While):
            if not unlock_tree.is_unlocked("while"):
                return "while loops are not unlocked yet — open the Unlocks screen."
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return "import statements are not allowed."
        #break and continue are always fine, they only work inside for/while anyway
    return None


def _draw_hud(surface: pygame.Surface, lv) -> tuple:
    #draws the objective panel, timer, and hud buttons on the right side of the screen
    obj        = lv.objective
    font_title = pygame.font.SysFont("Consolas", _s(16), bold=True)
    font_body  = pygame.font.SysFont("Consolas", _s(14))
    font_time  = pygame.font.SysFont("Consolas", _s(22), bold=True)
    font_label = pygame.font.SysFont("Consolas", _s(11))

    padding = _s(10)
    line_h  = _s(20)
    margin  = _s(12)

    #build the list of text lines for the objective panel
    if obj.has_crop_requirements:
        #show each specific crop requirement separately
        obj_lines = [f"Level {lv.number}: {lv.name}"]
        for crop, required in obj.crop_requirements.items():
            done = obj.crop_harvests_done.get(crop, 0)
            obj_lines.append(f"{crop.capitalize()}: {done}/{required}")
    else:
        #just show a total harvest count
        obj_lines = [f"Level {lv.number}: {lv.name}",
                     f"Harvest {obj.harvests_done}/{obj.harvests_required} crops"]

    #size the panel to fit all the text
    panel_w = max(font_title.size(obj_lines[0])[0],
                  max(font_body.size(l)[0] for l in obj_lines[1:])) + padding * 2
    panel_h = padding * 2 + len(obj_lines) * line_h

    #position the panel in the top right corner
    sx = surface.get_width() - panel_w - margin
    sy = margin

    panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel_surf.fill((15, 15, 25, 190))
    surface.blit(panel_surf, (sx, sy))

    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(sx, sy, panel_w, panel_h), _s(1), border_radius=_s(4))

    #draw level name at the top of the panel
    surface.blit(font_title.render(obj_lines[0], True, (220, 220, 255)),
                 (sx + padding, sy + padding))

    #draw each harvest requirement line below the title
    for i, line in enumerate(obj_lines[1:]):
        surface.blit(font_body.render(line, True, (180, 220, 180)),
                     (sx + padding, sy + padding + line_h * (i + 1)))

    #timer box sits directly below the objective panel
    time_box_w = panel_w
    time_box_h = _s(54)
    tx = sx
    ty = sy + panel_h + _s(6)

    #pick the time string and color based on how much time is left
    t = obj.time_remaining
    if t is None:
        time_str = "Infinity"
        time_col = (160, 160, 200)
    else:
        time_str = f"{t:.1f}s"
        if t < 10:
            time_col = (220, 80, 80)   #red when almost out of time
        elif t < 20:
            time_col = (230, 180, 50)  #yellow as a warning
        else:
            time_col = (180, 220, 180) #green when plenty of time left

    time_surf = pygame.Surface((time_box_w, time_box_h), pygame.SRCALPHA)
    time_surf.fill((15, 15, 25, 190))
    surface.blit(time_surf, (tx, ty))

    pygame.draw.rect(surface, (80, 80, 110),
                     pygame.Rect(tx, ty, time_box_w, time_box_h), _s(1), border_radius=_s(4))

    label_surf = font_label.render("TIME LEFT", True, (120, 120, 160))
    surface.blit(label_surf, (tx + padding, ty + _s(6)))

    #center the time number horizontally inside the timer box
    time_render = font_time.render(time_str, True, time_col)
    time_x = tx + (time_box_w - time_render.get_width()) // 2
    time_y = ty + time_box_h - time_render.get_height() - _s(6)
    surface.blit(time_render, (time_x, time_y))

    #center ide button moves the ide window back to its default position
    btn_w = time_box_w
    btn_h = time_box_h
    bx    = tx
    by    = ty + time_box_h + _s(6)

    center_btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
    btn_hovered     = center_btn_rect.collidepoint(pygame.mouse.get_pos())

    btn_bg_col = (30, 30, 45, 210) if btn_hovered else (15, 15, 25, 190)
    btn_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
    btn_bg.fill(btn_bg_col)
    surface.blit(btn_bg, (bx, by))

    pygame.draw.rect(surface, (80, 80, 110), center_btn_rect, _s(1), border_radius=_s(4))

    font_btn = pygame.font.SysFont("Consolas", _s(14), bold=True)
    lbl = font_btn.render("Center IDE", True, (255, 255, 255))
    surface.blit(lbl, (bx + (btn_w - lbl.get_width()) // 2,
                        by + (btn_h - lbl.get_height()) // 2))

    #how to play button opens the help modal
    htp_w = btn_w
    htp_h = btn_h
    hx    = bx
    hy    = by + btn_h + _s(6)

    htp_btn_rect = pygame.Rect(hx, hy, htp_w, htp_h)
    htp_hovered  = htp_btn_rect.collidepoint(pygame.mouse.get_pos())

    htp_bg_col = (30, 30, 45, 210) if htp_hovered else (15, 15, 25, 190)
    htp_bg = pygame.Surface((htp_w, htp_h), pygame.SRCALPHA)
    htp_bg.fill(htp_bg_col)
    surface.blit(htp_bg, (hx, hy))

    pygame.draw.rect(surface, (80, 80, 110), htp_btn_rect, _s(1), border_radius=_s(4))

    font_htp = pygame.font.SysFont("Consolas", _s(14), bold=True)
    htp_lbl  = font_htp.render("How to Play", True, (255, 255, 255))
    surface.blit(htp_lbl, (hx + (htp_w - htp_lbl.get_width())  // 2,
                             hy + (htp_h - htp_lbl.get_height()) // 2))

    #reset level button restarts the current level from scratch
    reset_btn_rect = pygame.Rect(hx, hy + htp_h + _s(6), htp_w, htp_h)
    reset_hovered  = reset_btn_rect.collidepoint(pygame.mouse.get_pos())

    reset_bg_col = (60, 20, 20, 210) if reset_hovered else (35, 15, 15, 190)
    reset_bg = pygame.Surface((htp_w, htp_h), pygame.SRCALPHA)
    reset_bg.fill(reset_bg_col)
    surface.blit(reset_bg, (hx, hy + htp_h + _s(6)))

    pygame.draw.rect(surface, (120, 50, 50), reset_btn_rect, _s(1), border_radius=_s(4))

    font_reset = pygame.font.SysFont("Consolas", _s(14), bold=True)
    reset_lbl  = font_reset.render("Reset Level", True, (255, 120, 120))
    surface.blit(reset_lbl, (reset_btn_rect.x + (htp_w - reset_lbl.get_width())  // 2,
                              reset_btn_rect.y + (htp_h - reset_lbl.get_height()) // 2))

    unlocks_w = htp_w
    unlocks_h = htp_h
    ux = hx
    uy = reset_btn_rect.bottom + _s(6)

    unlocks_btn_rect = pygame.Rect(ux, uy, unlocks_w, unlocks_h)
    unlocks_hovered  = unlocks_btn_rect.collidepoint(pygame.mouse.get_pos())

    unlocks_bg_col = (20, 45, 20, 210) if unlocks_hovered else (10, 30, 10, 190)
    unlocks_bg = pygame.Surface((unlocks_w, unlocks_h), pygame.SRCALPHA)
    unlocks_bg.fill(unlocks_bg_col)
    surface.blit(unlocks_bg, (ux, uy))

    pygame.draw.rect(surface, (60, 110, 60), unlocks_btn_rect, _s(1), border_radius=_s(4))

    font_unlocks = pygame.font.SysFont("Consolas", _s(14), bold=True)
    unlocks_lbl  = font_unlocks.render("Unlocks", True, (140, 225, 140))
    surface.blit(unlocks_lbl, (ux + (unlocks_w - unlocks_lbl.get_width())  // 2,
                                uy + (unlocks_h - unlocks_lbl.get_height()) // 2))

    #return all four button rects so the main loop can check for clicks
    return center_btn_rect, htp_btn_rect, reset_btn_rect, unlocks_btn_rect


unlock_tree = UnlockTree()
#tell the ide which commands are allowed, filtered by what is unlocked in the tree
ide.update_allowed(unlock_tree.effective_commands(level.objective.allowed_commands))

frame_count = 0
running     = True
frozen      = False  #true when the game is paused on the win/lose overlay

#hud button rects stored here so click handlers in the event loop can use them
_center_btn       = None
_htp_btn          = None
_reset_btn        = None
_unlocks_btn      = None
_htp_example_btns = []

_tech_tree_node_rects: dict = {}
_tech_tree_back_rect        = None


async def main():
    global running, frozen, game_state, level, farmer
    global _btn_hovered, _pulse_timer, _current_btn_rect
    global _show_htp_ingame, _htp_ingame_close, _htp_scroll_offset
    global _htp_example_open, _htp_example_btns
    global _center_btn, _htp_btn, _reset_btn, _unlocks_btn
    global _tech_tree_node_rects, _tech_tree_back_rect
    global frame_count
    global screen
    global current_user, _auth_task, _auth_creds

    while running:
        dt = clock.tick(60) / 1000.0  #time since last frame in seconds

        #browser: check if the window was resized and update the pygame surface
        if _IS_BROWSER:
            try:
                import platform as _plat
                dpr = float(_plat.window.devicePixelRatio) or 1.0
                vw = int(_plat.window.innerWidth)
                vh = int(_plat.window.innerHeight)
                target_w = int(vw * dpr)
                target_h = int(vh * dpr)
                cw, ch = screen.get_size()
                if vw > 0 and vh > 0 and (target_w != cw or target_h != ch):
                    screen = pygame.display.set_mode((target_w, target_h), pygame.RESIZABLE)
                    _pin_canvas_css(_plat, vw, vh)
                    level.center_on(target_w, target_h)
                    farmer.snap_to_tile()
            except Exception:
                pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                #desktop window was resized, update screen and recenter level
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                level.center_on(event.w, event.h)
                farmer.snap_to_tile()

            #auth screen handles login and signup button clicks
            if game_state == STATE_AUTH:
                action = auth_ui.handle_event_auth(event)
                if action == "login":
                    auth_ui.reset_form()
                    game_state = STATE_LOGIN
                elif action == "signup":
                    auth_ui.reset_form()
                    game_state = STATE_SIGNUP
                continue

            #login and signup forms handle typing and submission
            if game_state in (STATE_LOGIN, STATE_SIGNUP):
                if _auth_task is None:
                    action = auth_ui.handle_event_form(event)
                    if action == "back":
                        auth_ui.reset_form()
                        game_state = STATE_AUTH
                    elif action == "submit":
                        u, p = auth_ui.username, auth_ui.password
                        if not u or not p:
                            auth_ui.set_error("Username and password required")
                        else:
                            auth_ui.set_pending(True)
                            if _IS_BROWSER:
                                #browser cant await here so store creds and await later
                                _auth_creds = (u, p, "login" if game_state == STATE_LOGIN else "signup")
                            elif game_state == STATE_LOGIN:
                                _auth_task = _asyncio.create_task(api_client.login(u, p))
                            else:
                                _auth_task = _asyncio.create_task(api_client.signup(u, p))
                continue

            if game_state == STATE_TECH_TREE:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if _tech_tree_back_rect and _tech_tree_back_rect.collidepoint(event.pos):
                        game_state = STATE_PLAYING
                    else:
                        for k, r in _tech_tree_node_rects.items():
                            if r.collidepoint(event.pos):
                                if unlock_tree.try_unlock(k, manager._index):
                                    ide.update_allowed(
                                        unlock_tree.effective_commands(level.objective.allowed_commands)
                                    )
                                break
                continue

            #when frozen only let the overlay handle events so it can dismiss itself
            if frozen:
                if overlay.handle_event(event):
                    obj = level.objective
                    if obj.status == ObjectiveStatus.WIN:
                        _advance_level()
                    else:
                        _reload_level()
                    frozen = False
                continue

            #scroll the how to play modal when the mouse wheel moves
            if event.type == pygame.MOUSEWHEEL and _show_htp_ingame:
                _htp_scroll(-event.y * 24)
                continue

            #escape key closes the how to play modal
            if event.type == pygame.KEYDOWN:
                if _show_htp_ingame and event.key == pygame.K_ESCAPE:
                    _show_htp_ingame  = False
                    _htp_example_open = None
                    continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                #handle clicks inside the how to play modal
                if _show_htp_ingame:
                    #close button click
                    if _htp_ingame_close and _htp_ingame_close.collidepoint(event.pos):
                        _show_htp_ingame  = False
                        _htp_example_open = None
                        continue

                    #example button click toggles the code preview open or closed
                    for key, btn_rect in _htp_example_btns:
                        if btn_rect.collidepoint(event.pos):
                            if _htp_example_open == key:
                                _htp_example_open = None  #close if already open
                            else:
                                _htp_example_open = key   #open the clicked one
                            break

                    continue

                #center ide button snaps the ide back to the top left
                if _center_btn and _center_btn.collidepoint(event.pos):
                    ide.rect.x      = 20
                    ide.rect.y      = 20
                    ide.rect.width  = IDE.WIDTH
                    ide.rect.height = IDE.HEIGHT
                    continue

                #how to play button opens the modal
                if _htp_btn and _htp_btn.collidepoint(event.pos):
                    _show_htp_ingame   = True
                    _htp_scroll_offset = 0
                    _htp_example_open  = None
                    continue

                #reset button restarts the level
                if _reset_btn and _reset_btn.collidepoint(event.pos):
                    _reload_level()
                    continue

                if _unlocks_btn and _unlocks_btn.collidepoint(event.pos):
                    game_state = STATE_TECH_TREE
                    continue

            #pass the event to the ide and check if the run button was pressed
            code = ide.handle_event(event)
            if code is not None:
                try:
                    tree = ast.parse(code)
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

        #check if a desktop auth task finished and process the result
        if _auth_task is not None and _auth_task.done():
            result     = _auth_task.result()
            _auth_task = None
            if "error" in result:
                auth_ui.set_error(result["error"])
            else:
                current_user = result
                auth_ui.reset_form()
                game_state = STATE_PLAYING
                level.center_on(*screen.get_size())

        #draw the auth screen while waiting for the player to log in
        if game_state == STATE_AUTH:
            _pulse_timer += dt
            pulse = (math.sin(_pulse_timer * 3) + 1) / 2
            auth_ui.update(dt)
            auth_ui.draw_auth_screen(screen, pulse)
            pygame.display.flip()
            await asyncio.sleep(0)
            continue

        #draw the login or signup form while the player fills it in
        if game_state in (STATE_LOGIN, STATE_SIGNUP):
            auth_ui.update(dt)
            if game_state == STATE_LOGIN:
                auth_ui.draw_login_form(screen)
            else:
                auth_ui.draw_signup_form(screen)
            pygame.display.flip()
            #browser awaits the auth here since it cant do it in the event loop
            if _IS_BROWSER and _auth_creds is not None:
                u, p, mode = _auth_creds
                _auth_creds = None
                result = await (api_client.login(u, p) if mode == "login" else api_client.signup(u, p))
                if "error" in result:
                    auth_ui.set_error(result["error"])
                else:
                    current_user = result
                    auth_ui.reset_form()
                    game_state = STATE_PLAYING
                    level.center_on(*screen.get_size())
            await asyncio.sleep(0)
            continue

        _current_btn_rect = None

        if game_state == STATE_TECH_TREE:
            _tech_tree_node_rects, _tech_tree_back_rect = _unlock_screen.draw(
                screen, unlock_tree, manager._index
            )
            pygame.display.flip()
            await asyncio.sleep(0)
            continue

        #when frozen draw everything but let the overlay cover the screen
        if frozen:
            background.draw(screen)
            level.draw(screen)
            farmer.draw(screen)
            ide.draw(screen)
            _center_btn, _htp_btn, _reset_btn, _unlocks_btn = _draw_hud(screen, level)
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
            await asyncio.sleep(0)
            continue

        #update the objective timer while the level is being played
        obj = level.objective
        if obj.status == ObjectiveStatus.PLAYING:
            obj.update(dt)

        #if the level just ended freeze the game and stop the user thread
        if obj.status != ObjectiveStatus.PLAYING and not frozen:
            frozen = True
            _stop_user_thread()

        #desktop: step the threaded user code forward once the farmer arrives
        if not _IS_BROWSER:
            if (
                not frozen
                and _user_thread is not None
                and _user_thread.is_alive()
                and _done_event.is_set()
                and farmer._arrived
            ):
                _done_event.clear()
                _step_event.set()  #tell the thread to run the next command
        else:
            #browser: replay the next recorded action if the farmer is ready
            if not frozen:
                _tick_browser_actions()

        #update all game objects for this frame
        farmer.update(dt, level)
        ide.update(dt)
        level.update(dt, pygame.mouse.get_pos())

        #draw the environment in the correct order so things stack properly
        background.draw(screen)
        level.draw(screen)
        farmer.draw(screen)
        ide.draw(screen)
        _center_btn, _htp_btn, _reset_btn, _unlocks_btn = _draw_hud(screen, level)

        #draw the how to play modal on top if it is open
        if _show_htp_ingame:
            _htp_ingame_close, _htp_example_btns = _draw_htp_modal_ingame(screen)
        else:
            _htp_ingame_close  = None
            _htp_example_btns  = []

        #push the finished frame to the display
        pygame.display.flip()

        #print a debug grid every 5 seconds to show the level state in the console
        frame_count += 1
        if frame_count % 300 == 0:
            print_grid(level)
        #yield to javascript so the browser can process events and paint the canvas
        await asyncio.sleep(0)

    _stop_user_thread()
    pygame.quit()


asyncio.run(main())