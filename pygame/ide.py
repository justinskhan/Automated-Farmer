import pygame

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

#Goal: 
#Setting an IDE window that mimics vscode that has a run button and is resizable  
class IDE:
    #default height and width
    WIDTH  = 420
    HEIGHT = 260

    def __init__(self, x: int = 20, y: int = 20):
        #creates a rectangle width the default height and width
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
        self._resize_start: tuple[int, int, int, int] = (0, 0, 0, 0)  # mx, my, w, h

        self._run_hovered = False
        self._grip_hovered = False
        self._blink_timer = 0.0
        self._cursor_visible = True

        #output panel messages and whether they are errors
        self._output_lines: list[tuple[str, bool]] = []

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

            #first we want to reisze the rectangle grip to make sure nothing breaks
            if self._grip_rect().collidepoint(pos):
                self._resizing = True
                self._resize_start = (pos[0], pos[1], self.rect.width, self.rect.height)
                return None

            # run button creation
            if self._run_btn_rect().collidepoint(pos):
                self.clear_output()
                return "\n".join(self.lines)

            # title bar being used to drag the window around 
            if self._title_rect().collidepoint(pos):
                self._dragging = True
                self._drag_offset = (pos[0] - self.rect.x, pos[1] - self.rect.y)
                self.focused = True
                return None

            self.focused = self.rect.collidepoint(pos)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
            self._resizing = False

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos

            if self._dragging:
                self.rect.x = mx - self._drag_offset[0]
                self.rect.y = my - self._drag_offset[1]

            elif self._resizing:
                ox, oy, ow, oh = self._resize_start
                self.rect.width  = max(_MIN_W, ow + (mx - ox))
                self.rect.height = max(_MIN_H, oh + (my - oy))

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

        if event.key == pygame.K_RETURN:
            self.lines[row] = line[:col]
            self.lines.insert(row + 1, line[col:])
            self.cursor_row += 1
            self.cursor_col = 0

        elif event.key == pygame.K_BACKSPACE:
            if col > 0:
                self.lines[row] = line[:col - 1] + line[col:]
                self.cursor_col -= 1
            elif row > 0:
                prev = self.lines[row - 1]
                self.cursor_col = len(prev)
                self.lines[row - 1] = prev + line
                self.lines.pop(row)
                self.cursor_row -= 1

        elif event.key == pygame.K_DELETE:
            if col < len(line):
                self.lines[row] = line[:col] + line[col + 1:]
            elif row < len(self.lines) - 1:
                self.lines[row] = line + self.lines[row + 1]
                self.lines.pop(row + 1)

        elif event.key == pygame.K_LEFT:
            if col > 0:
                self.cursor_col -= 1
            elif row > 0:
                self.cursor_row -= 1
                self.cursor_col = len(self.lines[self.cursor_row])

        elif event.key == pygame.K_RIGHT:
            if col < len(line):
                self.cursor_col += 1
            elif row < len(self.lines) - 1:
                self.cursor_row += 1
                self.cursor_col = 0

        elif event.key == pygame.K_UP:
            if row > 0:
                self.cursor_row -= 1
                self.cursor_col = min(col, len(self.lines[self.cursor_row]))

        elif event.key == pygame.K_DOWN:
            if row < len(self.lines) - 1:
                self.cursor_row += 1
                self.cursor_col = min(col, len(self.lines[self.cursor_row]))

        elif event.key == pygame.K_HOME:
            self.cursor_col = 0

        elif event.key == pygame.K_END:
            self.cursor_col = len(self.lines[self.cursor_row])

        elif event.key == pygame.K_TAB:
            self.lines[row] = line[:col] + "    " + line[col:]
            self.cursor_col += 4

        elif event.unicode and event.unicode.isprintable():
            self.lines[row] = line[:col] + event.unicode + line[col:]
            self.cursor_col += 1

    def draw(self, surface: pygame.Surface) -> None:
        font = self._font_obj()

        pygame.draw.rect(surface, _BG, self.rect, border_radius=6)
        pygame.draw.rect(surface, _BORDER, self.rect, 1, border_radius=6)

        #title bar
        title_r = self._title_rect()
        pygame.draw.rect(surface, _TITLE_BG, title_r,
                         border_top_left_radius=6, border_top_right_radius=6)
        label = font.render("  </> Farmer IDE", True, _TEXT)
        surface.blit(label, (title_r.x + _PADDING,
                              title_r.y + (_TITLE_H - label.get_height()) // 2))

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

        #code area (clipped) shrunk to make room for output panel
        code_area_h = self.rect.height - _TITLE_H - _OUTPUT_H
        text_area = pygame.Rect(self.rect.x, self.rect.y + _TITLE_H,
                                self.rect.width, code_area_h)
        old_clip = surface.get_clip()
        surface.set_clip(text_area)

        sidebar = pygame.Rect(self.rect.x, text_area.y, _LINE_NUM_W, text_area.height)
        pygame.draw.rect(surface, _LINE_NUM_BG, sidebar)

        code_x = self.rect.x + _LINE_NUM_W + _PADDING
        y0 = text_area.y + _PADDING

        for i, line in enumerate(self.lines):
            ly = y0 + i * _LINE_H
            if ly > text_area.bottom:
                break

            num_surf = font.render(str(i + 1), True, _LINE_NUM)
            surface.blit(num_surf, (self.rect.x + _PADDING, ly))

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

        #resize on the bottom right corner
        grip = self._grip_rect()
        grip_col = (160, 160, 190) if self._grip_hovered else _GRIP
        for i in range(3):
            offset = i * 4 + 2
            #drawing the 3 lines on the bottom right
            pygame.draw.line(surface, grip_col,
                             (grip.right - offset, grip.bottom - 2),
                             (grip.right - 2, grip.bottom - offset), 1)