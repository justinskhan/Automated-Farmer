import pygame

# lines the player cannot edit
LOCKED_TOP = "while True:"

class IDE:
    def __init__(self, screen_w, screen_h):
        self.visible = False
        self.rect = pygame.Rect(screen_w // 4, screen_h // 4, screen_w // 2, screen_h // 2)

        # only the editable lines between the locked lines
        self.lines = ["    "]
        self.cursor_line = 0

        self.font = pygame.font.SysFont("Courier New", 16)

        # dragging state
        self.dragging = False
        self.drag_offset = (0, 0)

        # title bar
        self.title_bar_height = 28

        # horizontal scroll offset
        self.scroll_x = 0

        # cursor blink
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_interval = 500  # ms
        self.focused = False

        # backspace hold repeat
        self.backspace_held = False
        self.backspace_timer = 0
        self.backspace_initial_delay = 400  # ms before repeat starts
        self.backspace_repeat_interval = 50  # ms between repeats
        self._backspace_repeating = False

        # command queue delay
        self._command_delay = 0.4  # seconds between each command
        self._command_timer = 0.0
        self._command_queue = []
        self._running = False

    def toggle(self):
        self.visible = not self.visible

    def _title_bar_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, self.title_bar_height)

    def _close_btn_rect(self):
        size = 20
        return pygame.Rect(self.rect.right - size - 4, self.rect.y + 4, size, size)

    def resize(self, screen_w, screen_h):
        self.rect = pygame.Rect(screen_w // 4, screen_h // 4, screen_w // 2, screen_h // 2)

    def _do_backspace(self):
        line = self.lines[self.cursor_line]
        if line.strip():
            self.lines[self.cursor_line] = line[:-1]
        elif len(line) > 4:
            self.lines[self.cursor_line] = line[:-1]
        elif self.cursor_line > 0:
            self.lines.pop(self.cursor_line)
            self.cursor_line -= 1

    def update(self, dt, farmer, level):

        # cursor blink and backspace only when visible
        if self.visible:
            self.cursor_timer += dt * 1000
            if self.cursor_timer >= self.cursor_blink_interval:
                self.cursor_timer = 0
                self.cursor_visible = not self.cursor_visible

        # held backspace
        if self.backspace_held and self.focused:
            self.backspace_timer += dt * 1000
            threshold = self.backspace_initial_delay if not self._backspace_repeating else self.backspace_repeat_interval
            if self.backspace_timer >= threshold:
                self.backspace_timer = 0
                self._backspace_repeating = True
                self._do_backspace()

        # step through command queue — wait for farmer to arrive AND delay timer
        if self._running and self._command_queue and farmer._arrived:
            self._command_timer += dt
            if self._command_timer >= self._command_delay:
                self._command_timer = 0.0
                print(f"[IDE] dispatching command, queue size={len(self._command_queue)}, farmer._arrived={farmer._arrived}")
                cmd = self._command_queue.pop(0)
                cmd(farmer, level)

        if self._running and not self._command_queue and farmer._arrived:
            self._queue_from_code()  # refill and loop forever

    def handle_event(self, event):
        if not self.visible:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_btn_rect().collidepoint(event.pos):
                self.visible = False
                self.focused = False
                return
            if self._title_bar_rect().collidepoint(event.pos):
                self.dragging = True
                self.drag_offset = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
            if self.rect.collidepoint(event.pos):
                self.focused = True
                self.cursor_visible = True
                self.cursor_timer = 0
            else:
                self.focused = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            if event.button == 4:
                self.scroll_x = max(0, self.scroll_x - 20)
            elif event.button == 5:
                self.scroll_x += 20

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = event.pos[0] - self.drag_offset[0]
                self.rect.y = event.pos[1] - self.drag_offset[1]

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_BACKSPACE:
                self.backspace_held = False
                self._backspace_repeating = False
                self.backspace_timer = 0

        elif event.type == pygame.KEYDOWN and self.focused:
            self.cursor_visible = True
            self.cursor_timer = 0

            if event.key == pygame.K_RETURN:
                self.lines.insert(self.cursor_line + 1, "    ")
                self.cursor_line += 1
                self.scroll_x = 0
            elif event.key == pygame.K_BACKSPACE:
                self.backspace_held = True
                self.backspace_timer = 0
                self._backspace_repeating = False
                self._do_backspace()
            elif event.key == pygame.K_UP:
                if self.cursor_line > 0:
                    self.cursor_line -= 1
            elif event.key == pygame.K_DOWN:
                if self.cursor_line < len(self.lines) - 1:
                    self.cursor_line += 1
            else:
                if event.unicode:
                    self.lines[self.cursor_line] += event.unicode
                    line_w = self.font.size(self.lines[self.cursor_line])[0]
                    code_area_w = self.rect.w - 10
                    if line_w - self.scroll_x > code_area_w:
                        self.scroll_x = line_w - code_area_w
                    self._queue_from_code()

    def get_code(self):
        body = "\n".join(self.lines)
        return f"while True:\n{body}"

    def _queue_from_code(self):
        """Rebuild the command queue from current code silently."""
        queue = []

        def move_up():
            queue.append(lambda f, l: f.move_up(l))

        def move_down():
            queue.append(lambda f, l: f.move_down(l))

        def move_left():
            queue.append(lambda f, l: f.move_left(l))

        def move_right():
            queue.append(lambda f, l: f.move_right(l))

        safe_globals = {
            "__builtins__": {},
            "move_up": move_up,
            "move_down": move_down,
            "move_left": move_left,
            "move_right": move_right,
        }

        body = "\n".join(line[4:] if line.startswith("    ") else line for line in self.lines)
        try:
            exec(body, safe_globals)
        except Exception:
            return  # incomplete code while typing, just ignore

        if queue:
            self._command_queue = queue
            self._running = True

    def run_code(self, farmer, level):
        """Called by F5 — same as auto-run."""
        self._queue_from_code()
        print(f"[IDE] run_code: queued {len(self._command_queue)} commands, running={self._running}")

    def draw(self, screen):
        if not self.visible:
            return

        line_h = 20
        locked_color   = (140, 140, 110)
        editable_color = (200, 255, 200)

        # main panel
        pygame.draw.rect(screen, (30, 30, 30), self.rect, border_radius=6)

        # title bar
        title_rect = self._title_bar_rect()
        pygame.draw.rect(screen, (255, 255, 255), title_rect, border_radius=6)

        # close button
        close_rect = self._close_btn_rect()
        pygame.draw.rect(screen, (180, 50, 50), close_rect, border_radius=4)
        x_surf = self.font.render("X", True, (255, 255, 255))
        x_rect = x_surf.get_rect(center=close_rect.center)
        screen.blit(x_surf, x_rect)

        # clip to code area
        code_area = pygame.Rect(self.rect.x + 2, self.rect.y + self.title_bar_height, self.rect.w - 4, self.rect.h - self.title_bar_height - 2)
        screen.set_clip(code_area)

        y = self.rect.y + self.title_bar_height + 4
        x0 = self.rect.x + 5 - self.scroll_x

        # locked while True line
        top_surf = self.font.render(LOCKED_TOP, True, locked_color)
        screen.blit(top_surf, (x0, y))
        y += line_h

        # editable lines
        for i, line in enumerate(self.lines):
            if y + line_h > self.rect.bottom:
                break
            surf = self.font.render(line, True, editable_color)
            screen.blit(surf, (x0, y))

            # blinking cursor
            if i == self.cursor_line and self.focused and self.cursor_visible:
                cursor_x = self.rect.x + 5 + self.font.size(line)[0] - self.scroll_x
                pygame.draw.line(screen, editable_color, (cursor_x, y), (cursor_x, y + 18), 2)

            y += line_h

        screen.set_clip(None)

        # border
        pygame.draw.rect(screen, (80, 80, 100), self.rect, width=2, border_radius=6)