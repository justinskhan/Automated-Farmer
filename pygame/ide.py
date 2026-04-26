import pygame
import sys
 
# pygame.scrap (clipboard) is not supported in pygbag/WASM — calling init()
# in that environment raises pygame.error and kills the async task, which
# is why pressing play used to freeze on the loading screen. Detect the
# browser once here and use these helpers everywhere instead of calling
# pygame.scrap directly, so desktop keeps full copy/paste support and the
# browser build just silently no-ops clipboard operations.
_IS_BROWSER = sys.platform in ("emscripten", "wasi")
_scrap_ok: bool | None = None   # None = untested, True/False = known
_scrap_fallback: str = ""       # in-memory clipboard used when scrap is unavailable
 
 
def _scrap_available() -> bool:
    """Return True if pygame.scrap can be used. Tries to init once, caches result."""
    global _scrap_ok
    if _scrap_ok is not None:
        return _scrap_ok
    if _IS_BROWSER:
        _scrap_ok = False
        return False
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        _scrap_ok = True
    except Exception:
        _scrap_ok = False
    return _scrap_ok
 
 
def _clipboard_put(text: str) -> None:
    """Copy text to the system clipboard, falling back to an in-memory store."""
    global _scrap_fallback
    _scrap_fallback = text
    if not _scrap_available():
        return
    try:
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode())
    except Exception:
        pass
 
 
def _clipboard_get() -> str:
    """Read text from the system clipboard, falling back to the in-memory store."""
    if not _scrap_available():
        return _scrap_fallback
    try:
        data = pygame.scrap.get(pygame.SCRAP_TEXT)
        return data.decode() if data else _scrap_fallback
    except Exception:
        return _scrap_fallback
 
 
#setting colors for IDE and the text
_BG          = ( 30,  30,  40)
_TITLE_BG    = ( 20,  20,  30)
_LINE_NUM_BG = ( 25,  25,  35)
_TEXT        = (220, 220, 220)
_LINE_NUM    = (100, 100, 130)
_CURSOR      = (255, 255, 255)
_BORDER      = ( 80,  80, 110)
_RUN_BTN     = ( 50, 180,  80)
_RUN_HOVER   = ( 70, 210, 100)
_GRIP        = (100, 100, 130)
_OUTPUT_BG   = ( 15,  15,  25)
_OUTPUT_TEXT = (180, 220, 180)
_ERROR_TEXT  = (220,  80,  80)
_TIMER_OK    = (180, 220, 180)   #green when plenty of time left
_TIMER_WARN  = (230, 180,  50)   #yellow when under 20 seconds
_TIMER_CRIT  = (220,  80,  80)   #red when under 10 seconds
_SELECT_BG   = ( 70, 130, 180,  80)  #selection highlight color
 
_FONT_SIZE   = 14
_TITLE_H     = 28
_PADDING     = 6
_LINE_H      = 18
_LINE_NUM_W  = 28
_RUN_BTN_SZ  = 20
_GRIP_SIZE   = 14
_MIN_W       = 200
_MIN_H       = 120
_OUTPUT_H    = 60
 
# KMOD_CTRL covers Ctrl on Windows/Linux and the browser.
# KMOD_META covers Cmd on macOS.
# Combining both means copy/paste shortcuts work on every platform.
_CTRL_OR_CMD = pygame.KMOD_CTRL | pygame.KMOD_META
 
#Goal: 
#Setting an IDE window that mimics vscode that has a run button and is resizable  
class IDE:
    #default height and width
    WIDTH  = 420
    HEIGHT = 260
 
    def __init__(self, x: int = 20, y: int = 20):
        #creates a rectangle with the default height and width
        self.rect = pygame.Rect(x, y, self.WIDTH, self.HEIGHT)
        #lines will start with one empty line
        self.lines: list[str] = [""]
        #sets the cursor to beginning of IDE when new
        self.cursor_row = 0
        self.cursor_col = 0
        self.focused = False
        #avoids loading font before ide is open
        self._font: pygame.font.Font | None = None
        #no dragging on default for resizing
        self._dragging = False
        self._drag_offset = (0, 0)
 
        self._resizing = False
        self._resize_start: tuple[int, int, int, int] = (0, 0, 0, 0)
 
        self._run_hovered = False
        self._grip_hovered = False
        self._blink_timer = 0.0
        self._cursor_visible = True
 
        #selection anchor — set when mouse is pressed, used to highlight a range
        self._sel_anchor: tuple[int, int] | None = None
        self._sel_end:    tuple[int, int] | None = None
        self._mouse_selecting = False
 
        #output panel messages and whether they are errors
        self._output_lines: list[tuple[str, bool]] = []
 
        #selection tracking in order to edit IDE quickly
        self.selection_start = None
 
        #stores the allowed commands list so main.py can update it each level
        self._allowed: list[str] = []
 
        #stores time remaining so the title bar can show a countdown
        self._time_remaining: float | None = None
 
    #called by main.py whenever the level changes to update allowed commands
    def update_allowed(self, commands: list[str]) -> None:
        self._allowed = list(commands)
 
    #called each frame by main.py with the time remaining or None if no timer
    def set_timer(self, seconds: float | None) -> None:
        self._time_remaining = seconds
 
    #this functions makes sure font isnt loaded until until needed
    def _font_obj(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("Consolas", _FONT_SIZE)
        return self._font
 
    #helps relocate the IDE name
    def _title_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.width, _TITLE_H)
 
    #run button creation
    def _run_btn_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.rect.right - _RUN_BTN_SZ - 6,
            self.rect.top + (_TITLE_H - _RUN_BTN_SZ) // 2,
            _RUN_BTN_SZ,
            _RUN_BTN_SZ,
        )
 
    #creating a rectangle "grip" on the bottom right of the IDE 
    def _grip_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.rect.right - _GRIP_SIZE,
            self.rect.bottom - _GRIP_SIZE,
            _GRIP_SIZE,
            _GRIP_SIZE,
        )
 
    #returns the rect for the output panel at the bottom of the IDE
    def _output_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.rect.x,
            self.rect.bottom - _OUTPUT_H,
            self.rect.width,
            _OUTPUT_H,
        )
 
    #converts a mouse position into a (row, col) cursor position in the text
    def _pos_to_row_col(self, mx: int, my: int) -> tuple[int, int]:
        font     = self._font_obj()
        code_top = self.rect.y + _TITLE_H
        code_x   = self.rect.x + _LINE_NUM_W + _PADDING
        y0       = code_top + _PADDING
 
        #clamp row to valid range
        row = (my - y0) // _LINE_H
        row = max(0, min(row, len(self.lines) - 1))
 
        line = self.lines[row]
        #find the character column closest to the mouse x position
        col = 0
        for i in range(len(line) + 1):
            char_x = code_x + font.size(line[:i])[0]
            if char_x > mx:
                break
            col = i
        return row, col
 
    #returns the normalised (start, end) of the current selection or None
    def _selection_range(self) -> tuple[tuple[int, int], tuple[int, int]] | None:
        if self._sel_anchor is None or self._sel_end is None:
            return None
        if self._sel_anchor == self._sel_end:
            return None
        a = self._sel_anchor
        b = self._sel_end
        #put the earlier position first
        if (a[0], a[1]) > (b[0], b[1]):
            a, b = b, a
        return a, b
 
    #returns all selected text as a single string
    def _selected_text(self) -> str:
        sel = self._selection_range()
        if sel is None:
            return ""
        (r1, c1), (r2, c2) = sel
        if r1 == r2:
            return self.lines[r1][c1:c2]
        parts = [self.lines[r1][c1:]]
        for r in range(r1 + 1, r2):
            parts.append(self.lines[r])
        parts.append(self.lines[r2][:c2])
        return "\n".join(parts)
 
    #deletes the currently selected text and moves cursor to selection start
    def _delete_selection(self) -> None:
        sel = self._selection_range()
        if sel is None:
            return
        (r1, c1), (r2, c2) = sel
        before = self.lines[r1][:c1]
        after  = self.lines[r2][c2:]
        self.lines[r1] = before + after
        del self.lines[r1 + 1 : r2 + 1]
        self.cursor_row  = r1
        self.cursor_col  = c1
        self._sel_anchor = None
        self._sel_end    = None
 
    #adds a message to the output panel
    def log(self, message: str, error: bool = False) -> None:
        #split multi line messages into separate lines
        for line in message.splitlines():
            self._output_lines.append((line, error))
        #only keep the last few lines so panel doesnt overflow
        self._output_lines = self._output_lines[-3:]
 
    #clears the output panel
    def clear_output(self) -> None:
        self._output_lines = []
 
    #this function runs everytime something happens in our IDE
    #this includes mouseclicks, text typing, clicking around 
    def handle_event(self, event: pygame.event.Event) -> str | None:
        #for mouse will only read LMB
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
 
            #first we want to resize the rectangle grip to make sure nothing breaks
            if self._grip_rect().collidepoint(pos):
                self._resizing = True
                self._resize_start = (pos[0], pos[1], self.rect.width, self.rect.height)
                return None
 
            #run button creation
            if self._run_btn_rect().collidepoint(pos):
                self.clear_output()
                return "\n".join(self.lines)
 
            #title bar being used to drag the window around 
            if self._title_rect().collidepoint(pos):
                self._dragging = True
                self._drag_offset = (pos[0] - self.rect.x, pos[1] - self.rect.y)
                self.focused = True
                return None
 
            #click inside code area — move cursor to clicked line and column
            code_area = pygame.Rect(
                self.rect.x,
                self.rect.y + _TITLE_H,
                self.rect.width,
                self.rect.height - _TITLE_H - _OUTPUT_H,
            )
            if code_area.collidepoint(pos):
                self.focused = True
                row, col = self._pos_to_row_col(*pos)
                self.cursor_row       = row
                self.cursor_col       = col
                #start a new selection anchor at the clicked position
                self._sel_anchor      = (row, col)
                self._sel_end         = (row, col)
                self._mouse_selecting = True
                return None
 
            self.focused = self.rect.collidepoint(pos)
 
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging        = False
            self._resizing        = False
            self._mouse_selecting = False
 
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
 
            if self._dragging:
                self.rect.x = mx - self._drag_offset[0]
                self.rect.y = my - self._drag_offset[1]
 
            elif self._resizing:
                ox, oy, ow, oh = self._resize_start
                self.rect.width  = max(_MIN_W, ow + (mx - ox))
                self.rect.height = max(_MIN_H, oh + (my - oy))
 
            #drag to select text across lines
            elif self._mouse_selecting and self.focused:
                row, col         = self._pos_to_row_col(mx, my)
                self._sel_end    = (row, col)
                self.cursor_row  = row
                self.cursor_col  = col
 
            self._run_hovered  = self._run_btn_rect().collidepoint(event.pos)
            self._grip_hovered = self._grip_rect().collidepoint(event.pos)
 
        elif event.type == pygame.KEYDOWN and self.focused:
            self._handle_key(event)
 
        return None
 
    def update(self, dt: float) -> None:
        self._blink_timer += dt
        if self._blink_timer >= 0.5:
            self._blink_timer = 0.0
            self._cursor_visible = not self._cursor_visible
 
    def _handle_key(self, event: pygame.event.Event) -> None:
        row, col = self.cursor_row, self.cursor_col
        line = self.lines[row]
 
        # _CTRL_OR_CMD detects Ctrl on Windows/Linux/browser AND Cmd on macOS
        # so that copy/paste/select-all shortcuts work on every platform
        ctrl_pressed  = pygame.key.get_mods() & _CTRL_OR_CMD
        shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
 
        #Ctrl+A / Cmd+A = select all lines
        if event.key == pygame.K_a and ctrl_pressed:
            self._sel_anchor = (0, 0)
            last             = len(self.lines) - 1
            self._sel_end    = (last, len(self.lines[last]))
            self.cursor_row  = last
            self.cursor_col  = len(self.lines[last])
            return
 
        #Ctrl+C / Cmd+C = copy selected text to clipboard (uses safe helper so pygbag/WASM no-ops)
        if event.key == pygame.K_c and ctrl_pressed:
            text = self._selected_text()
            if text:
                _clipboard_put(text)
            return
 
        #Ctrl+X / Cmd+X = cut selected text to clipboard (uses safe helper so pygbag/WASM no-ops)
        if event.key == pygame.K_x and ctrl_pressed:
            text = self._selected_text()
            if text:
                _clipboard_put(text)
                self._delete_selection()
            return
 
        #Ctrl+V / Cmd+V = paste from clipboard (uses safe helper so pygbag/WASM no-ops)
        if event.key == pygame.K_v and ctrl_pressed:
            #delete any active selection before pasting
            self._delete_selection()
            text = _clipboard_get()
            if text:
                #normalise line endings so windows and mac paste correctly
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                row, col  = self.cursor_row, self.cursor_col
                line      = self.lines[row]
                before    = line[:col]
                after     = line[col:]
                paste_lines = text.split("\n")
                self.lines[row] = before + paste_lines[0]
                for i, pl in enumerate(paste_lines[1:], start=1):
                    self.lines.insert(row + i, pl)
                self.cursor_row = row + len(paste_lines) - 1
                if len(paste_lines) == 1:
                    self.cursor_col = col + len(paste_lines[0])
                else:
                    self.cursor_col = len(paste_lines[-1])
                self.lines[self.cursor_row] += after
            return
 
        if event.key == pygame.K_RETURN:
            #delete selection first if there is one
            self._delete_selection()
            row, col = self.cursor_row, self.cursor_col
            line = self.lines[row]
            self.lines[row] = line[:col]
            self.lines.insert(row + 1, line[col:])
            self.cursor_row += 1
            self.cursor_col = 0
 
        elif event.key == pygame.K_BACKSPACE:
            if self._selection_range():
                self._delete_selection()
            elif col > 0:
                self.lines[row] = line[:col - 1] + line[col:]
                self.cursor_col -= 1
            elif row > 0:
                prev = self.lines[row - 1]
                self.cursor_col = len(prev)
                self.lines[row - 1] = prev + line
                self.lines.pop(row)
                self.cursor_row -= 1
 
        elif event.key == pygame.K_DELETE:
            if self._selection_range():
                self._delete_selection()
            elif col < len(line):
                self.lines[row] = line[:col] + line[col + 1:]
            elif row < len(self.lines) - 1:
                self.lines[row] = line + self.lines[row + 1]
                self.lines.pop(row + 1)
 
        elif event.key == pygame.K_LEFT:
            if not shift_pressed:
                self._sel_anchor = None
                self._sel_end    = None
            if col > 0:
                self.cursor_col -= 1
            elif row > 0:
                self.cursor_row -= 1
                self.cursor_col = len(self.lines[self.cursor_row])
 
        elif event.key == pygame.K_RIGHT:
            if not shift_pressed:
                self._sel_anchor = None
                self._sel_end    = None
            if col < len(line):
                self.cursor_col += 1
            elif row < len(self.lines) - 1:
                self.cursor_row += 1
                self.cursor_col = 0
 
        elif event.key == pygame.K_UP:
            if not shift_pressed:
                self._sel_anchor = None
                self._sel_end    = None
            if row > 0:
                self.cursor_row -= 1
                self.cursor_col = min(col, len(self.lines[self.cursor_row]))
 
        elif event.key == pygame.K_DOWN:
            if not shift_pressed:
                self._sel_anchor = None
                self._sel_end    = None
            if row < len(self.lines) - 1:
                self.cursor_row += 1
                self.cursor_col = min(col, len(self.lines[self.cursor_row]))
 
        elif event.key == pygame.K_HOME:
            if not shift_pressed:
                self._sel_anchor = None
                self._sel_end    = None
            self.cursor_col = 0
 
        elif event.key == pygame.K_END:
            if not shift_pressed:
                self._sel_anchor = None
                self._sel_end    = None
            self.cursor_col = len(self.lines[self.cursor_row])
 
        elif event.key == pygame.K_TAB:
            self._delete_selection()
            row, col = self.cursor_row, self.cursor_col
            self.lines[row] = self.lines[row][:col] + "    " + self.lines[row][col:]
            self.cursor_col += 4
 
        elif event.unicode and event.unicode.isprintable():
            #replace selection with the typed character if there is one
            self._delete_selection()
            row, col = self.cursor_row, self.cursor_col
            self.lines[row] = self.lines[row][:col] + event.unicode + self.lines[row][col:]
            self.cursor_col += 1
 
    #creates the ide itself
    def draw(self, surface: pygame.Surface) -> None:
        font = self._font_obj()
 
        #initialise clipboard support the first time we draw — safe in pygbag/WASM
        #where pygame.scrap is unavailable and would otherwise crash the async task
        _scrap_available()
 
 
        pygame.draw.rect(surface, _BG, self.rect, border_radius=6)
        pygame.draw.rect(surface, _BORDER, self.rect, 1, border_radius=6)
 
        #title bar
        title_r = self._title_rect()
        pygame.draw.rect(surface, _TITLE_BG, title_r,
                         border_top_left_radius=6, border_top_right_radius=6)
        label = font.render("  </> Farmer IDE", True, _TEXT)
        surface.blit(label, (title_r.x + _PADDING,
                              title_r.y + (_TITLE_H - label.get_height()) // 2))
 
        #timer shown in title bar, changes color as time gets low
        if self._time_remaining is not None:
            t = self._time_remaining
            if t < 10:
                tcol = _TIMER_CRIT
            elif t < 20:
                tcol = _TIMER_WARN
            else:
                tcol = _TIMER_OK
            t_surf = font.render(f"{t:.0f}s", True, tcol)
            t_x = self._run_btn_rect().left - t_surf.get_width() - 8
            t_y = title_r.y + (_TITLE_H - t_surf.get_height()) // 2
            surface.blit(t_surf, (t_x, t_y))
 
        #run button
        run_r = self._run_btn_rect()
        pygame.draw.rect(surface, _RUN_HOVER if self._run_hovered else _RUN_BTN,
                         run_r, border_radius=4)
        tx, ty = run_r.x + 6, run_r.y + 4
        tw, th = run_r.width - 10, run_r.height - 8
        pygame.draw.polygon(surface, (255, 255, 255), [
            (tx,      ty),
            (tx,      ty + th),
            (tx + tw, ty + th // 2),
        ])
 
        #code area clipped so text doesnt overflow outside the ide
        code_top    = self.rect.y + _TITLE_H
        code_area_h = self.rect.height - _TITLE_H - _OUTPUT_H
        text_area   = pygame.Rect(self.rect.x, code_top,
                                  self.rect.width, code_area_h)
        old_clip = surface.get_clip()
        surface.set_clip(text_area)
 
        sidebar = pygame.Rect(self.rect.x, text_area.y, _LINE_NUM_W, text_area.height)
        pygame.draw.rect(surface, _LINE_NUM_BG, sidebar)
 
        code_x = self.rect.x + _LINE_NUM_W + _PADDING
        y0     = text_area.y + _PADDING
 
        sel = self._selection_range()
 
        for i, line in enumerate(self.lines):
            ly = y0 + i * _LINE_H
            if ly > text_area.bottom:
                break
 
            num_surf = font.render(str(i + 1), True, _LINE_NUM)
            surface.blit(num_surf, (self.rect.x + _PADDING, ly))
 
            #draw selection highlight behind the text for any selected rows
            if sel is not None:
                (r1, c1), (r2, c2) = sel
                if r1 <= i <= r2:
                    sel_c1 = c1 if i == r1 else 0
                    sel_c2 = c2 if i == r2 else len(line)
                    sx1 = code_x + font.size(line[:sel_c1])[0]
                    sx2 = code_x + font.size(line[:sel_c2])[0]
                    #extend highlight to end of row for lines in the middle of a selection
                    if i < r2:
                        sx2 = self.rect.right
                    sel_surf = pygame.Surface((max(1, sx2 - sx1), _LINE_H), pygame.SRCALPHA)
                    sel_surf.fill(_SELECT_BG)
                    surface.blit(sel_surf, (sx1, ly))
 
            surface.blit(font.render(line, True, _TEXT), (code_x, ly))
 
            if self.focused and self._cursor_visible and i == self.cursor_row:
                cx = code_x + font.size(line[:self.cursor_col])[0]
                pygame.draw.line(surface, _CURSOR, (cx, ly), (cx, ly + _LINE_H - 2), 2)
 
        surface.set_clip(old_clip)
 
        #output panel at the bottom of the IDE
        out_r = self._output_rect()
        pygame.draw.rect(surface, _OUTPUT_BG, out_r)
        pygame.draw.line(surface, _BORDER, out_r.topleft, out_r.topright, 1)
 
        surface.set_clip(out_r)
        for i, (msg, is_error) in enumerate(self._output_lines):
            color = _ERROR_TEXT if is_error else _OUTPUT_TEXT
            surf = font.render(msg, True, color)
            surface.blit(surf, (out_r.x + _PADDING, out_r.y + _PADDING + i * _LINE_H))
        surface.set_clip(old_clip)
 
        #resize grip on the bottom right corner
        grip = self._grip_rect()
        grip_col = (160, 160, 190) if self._grip_hovered else _GRIP
        for i in range(3):
            offset = i * 4 + 2
            #drawing the 3 lines on the bottom right
            pygame.draw.line(surface, grip_col,
                             (grip.right - offset, grip.bottom - 2),
                             (grip.right - 2, grip.bottom - offset), 1)
 