from __future__ import annotations
import math
import pygame

_PANEL_BG           = ( 15,  15,  25, 210)
_BORDER             = ( 80,  80, 110)
_TITLE_COLOR        = (220, 240, 200)
_SUBTITLE_COLOR     = (100, 180, 100)
_BTN_GREEN          = ( 50, 180,  80)
_BTN_GREEN_HOVER    = ( 70, 210, 100)
_BTN_BORDER         = ( 30, 100,  50)
_BTN_OUTLINE        = ( 35,  60,  35)
_BTN_OUTLINE_HOVER  = ( 60,  90,  60)
_INPUT_BG           = ( 25,  25,  40)
_INPUT_FOCUS_BG     = ( 40,  40,  65)
_INPUT_BORDER       = ( 70,  70, 100)
_INPUT_BORDER_FOCUS = (100, 160, 200)
_TEXT_COLOR         = (220, 220, 220)
_LABEL_COLOR        = (160, 160, 200)
_ERROR_COLOR        = (220,  80,  80)
_BACK_BG            = ( 40,  40,  60)
_BACK_BG_HOVER      = ( 65,  65,  95)


class _InputField:
    def __init__(self, label: str, masked: bool = False) -> None:
        self.label   = label
        self.masked  = masked
        self.value   = ""
        self.focused = False
        self.rect    = pygame.Rect(0, 0, 0, 0)
        self._cursor_timer = 0.0
        self._cursor_vis   = True

    def update(self, dt: float) -> None:
        if self.focused:
            self._cursor_timer += dt
            if self._cursor_timer >= 0.5:
                self._cursor_timer = 0.0
                self._cursor_vis   = not self._cursor_vis
        else:
            self._cursor_vis   = False
            self._cursor_timer = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if not self.focused or event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_BACKSPACE:
            self.value = self.value[:-1]
        elif event.key not in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
            if len(self.value) < 32 and event.unicode.isprintable():
                self.value += event.unicode

    def draw(self, surface: pygame.Surface, x: int, y: int, w: int) -> None:
        font_label = pygame.font.SysFont("Consolas", 13)
        font_text  = pygame.font.SysFont("Consolas", 16)

        h         = 38
        self.rect = pygame.Rect(x, y, w, h)

        lbl = font_label.render(self.label, True, _LABEL_COLOR)
        surface.blit(lbl, (x, y - lbl.get_height() - 4))

        bg  = _INPUT_FOCUS_BG if self.focused else _INPUT_BG
        bdr = _INPUT_BORDER_FOCUS if self.focused else _INPUT_BORDER
        pygame.draw.rect(surface, bg,  self.rect, border_radius=4)
        pygame.draw.rect(surface, bdr, self.rect, 1, border_radius=4)

        display = ("*" * len(self.value)) if self.masked else self.value
        if self.focused and self._cursor_vis:
            display += "|"

        txt = font_text.render(display, True, _TEXT_COLOR)
        surface.blit(txt, (x + 10, y + (h - txt.get_height()) // 2))


class AuthUI:
    def __init__(self) -> None:
        self._username = _InputField("Username")
        self._password = _InputField("Password", masked=True)
        self._error    = ""
        self._pending  = False

        self._btn_login_rect:  pygame.Rect | None = None
        self._btn_signup_rect: pygame.Rect | None = None
        self._btn_submit_rect: pygame.Rect | None = None
        self._btn_back_rect:   pygame.Rect | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def username(self) -> str:
        return self._username.value.strip()

    @property
    def password(self) -> str:
        return self._password.value

    def reset_form(self) -> None:
        self._username.value   = ""
        self._password.value   = ""
        self._username.focused = False
        self._password.focused = False
        self._error   = ""
        self._pending = False

    def set_error(self, msg: str) -> None:
        self._error   = msg
        self._pending = False

    def set_pending(self, state: bool) -> None:
        self._pending = state
        if state:
            self._error = ""

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self._username.update(dt)
        self._password.update(dt)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event_auth(self, event: pygame.event.Event) -> str | None:
        """Returns 'login' | 'signup' | None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_login_rect and self._btn_login_rect.collidepoint(event.pos):
                return "login"
            if self._btn_signup_rect and self._btn_signup_rect.collidepoint(event.pos):
                return "signup"
        return None

    def handle_event_form(self, event: pygame.event.Event) -> str | None:
        """Returns 'submit' | 'back' | None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_submit_rect and self._btn_submit_rect.collidepoint(event.pos):
                return "submit"
            if self._btn_back_rect and self._btn_back_rect.collidepoint(event.pos):
                return "back"
            # Focus management
            clicked_field = False
            if self._username.rect.collidepoint(event.pos):
                self._username.focused = True
                self._password.focused = False
                clicked_field = True
            elif self._password.rect.collidepoint(event.pos):
                self._password.focused = True
                self._username.focused = False
                clicked_field = True
            if not clicked_field:
                self._username.focused = False
                self._password.focused = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and not self._pending:
                return "submit"
            if event.key == pygame.K_TAB:
                if self._username.focused:
                    self._username.focused = False
                    self._password.focused = True
                else:
                    self._username.focused = True
                    self._password.focused = False
                return None
            if event.key == pygame.K_ESCAPE:
                return "back"

        self._username.handle_event(event)
        self._password.handle_event(event)
        return None

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw_auth_screen(self, surface: pygame.Surface, pulse: float) -> None:
        sw, sh = surface.get_size()
        surface.fill((173, 216, 230))

        panel_w = 520
        panel_h = 300
        panel_x = (sw - panel_w) // 2
        panel_y = (sh - panel_h) // 2 - 30

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill(_PANEL_BG)
        surface.blit(panel_surf, (panel_x, panel_y))

        font_sub  = pygame.font.SysFont("Consolas", 15)
        font_big  = pygame.font.SysFont("Consolas", 52, bold=True)

        sub = font_sub.render("< Learn to code through farming />", True, _SUBTITLE_COLOR)
        surface.blit(sub, (sw // 2 - sub.get_width() // 2, panel_y + 28))

        t1 = font_big.render("Automated", True, (220, 240, 200))
        t2 = font_big.render("Farmer",    True, (160, 210, 120))
        surface.blit(t1, (sw // 2 - t1.get_width() // 2, panel_y + 64))
        surface.blit(t2, (sw // 2 - t2.get_width() // 2, panel_y + 124))

        icons = [
            ((sw // 2 - 90, panel_y + 220), (210, 180,  50), "sq"),
            ((sw // 2 - 40, panel_y + 220), (255, 220,   0), "ci"),
            ((sw // 2 + 10, panel_y + 220), (220,  50,  50), "ci"),
            ((sw // 2 + 60, panel_y + 220), (230, 120,  20), "tr"),
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

        btn_w = int(150 + pulse * 5)
        btn_h = int(48  + pulse * 2)
        gap   = 20
        total = btn_w * 2 + gap
        bx    = sw // 2 - total // 2
        by    = panel_y + panel_h + 24
        mouse = pygame.mouse.get_pos()

        font_btn = pygame.font.SysFont("Consolas", 18, bold=True)

        self._btn_login_rect = pygame.Rect(bx, by, btn_w, btn_h)
        login_col = _BTN_GREEN_HOVER if self._btn_login_rect.collidepoint(mouse) else _BTN_GREEN
        pygame.draw.rect(surface, login_col, self._btn_login_rect, border_radius=6)
        pygame.draw.rect(surface, _BTN_BORDER, self._btn_login_rect, 2, border_radius=6)
        lbl = font_btn.render("LOGIN", True, (255, 255, 255))
        surface.blit(lbl, (self._btn_login_rect.centerx - lbl.get_width() // 2,
                           self._btn_login_rect.centery - lbl.get_height() // 2))

        self._btn_signup_rect = pygame.Rect(bx + btn_w + gap, by, btn_w, btn_h)
        signup_col = _BTN_OUTLINE_HOVER if self._btn_signup_rect.collidepoint(mouse) else _BTN_OUTLINE
        pygame.draw.rect(surface, signup_col, self._btn_signup_rect, border_radius=6)
        pygame.draw.rect(surface, _BTN_BORDER, self._btn_signup_rect, 2, border_radius=6)
        lbl2 = font_btn.render("SIGN UP", True, (200, 240, 180))
        surface.blit(lbl2, (self._btn_signup_rect.centerx - lbl2.get_width() // 2,
                            self._btn_signup_rect.centery - lbl2.get_height() // 2))

    def _draw_form(self, surface: pygame.Surface, heading: str, submit_label: str) -> None:
        sw, sh = surface.get_size()
        surface.fill((173, 216, 230))

        form_w = 400
        form_h = 310
        fx     = (sw - form_w) // 2
        fy     = (sh - form_h) // 2 - 20

        panel_surf = pygame.Surface((form_w, form_h), pygame.SRCALPHA)
        panel_surf.fill(_PANEL_BG)
        surface.blit(panel_surf, (fx, fy))
        pygame.draw.rect(surface, _BORDER, pygame.Rect(fx, fy, form_w, form_h), 1, border_radius=6)

        font_heading = pygame.font.SysFont("Consolas", 26, bold=True)
        h_surf = font_heading.render(heading, True, _TITLE_COLOR)
        surface.blit(h_surf, (fx + form_w // 2 - h_surf.get_width() // 2, fy + 22))

        field_w = form_w - 60
        field_x = fx + 30
        self._username.draw(surface, field_x, fy + 84,  field_w)
        self._password.draw(surface, field_x, fy + 164, field_w)

        if self._error:
            font_err = pygame.font.SysFont("Consolas", 13)
            err_surf = font_err.render(self._error, True, _ERROR_COLOR)
            surface.blit(err_surf, (fx + form_w // 2 - err_surf.get_width() // 2, fy + 214))

        mouse    = pygame.mouse.get_pos()
        font_btn = pygame.font.SysFont("Consolas", 16, bold=True)

        btn_w = 160
        btn_h = 42
        sbx   = fx + form_w // 2 - btn_w // 2
        sby   = fy + form_h - 56
        self._btn_submit_rect = pygame.Rect(sbx, sby, btn_w, btn_h)

        if self._pending:
            sub_col   = (50, 100, 60)
            sub_label = "..."
        else:
            sub_col   = _BTN_GREEN_HOVER if self._btn_submit_rect.collidepoint(mouse) else _BTN_GREEN
            sub_label = submit_label

        pygame.draw.rect(surface, sub_col, self._btn_submit_rect, border_radius=6)
        pygame.draw.rect(surface, _BTN_BORDER, self._btn_submit_rect, 2, border_radius=6)
        s = font_btn.render(sub_label, True, (255, 255, 255))
        surface.blit(s, (self._btn_submit_rect.centerx - s.get_width() // 2,
                         self._btn_submit_rect.centery - s.get_height() // 2))

        self._btn_back_rect = pygame.Rect(fx + 10, fy + 10, 70, 26)
        back_col = _BACK_BG_HOVER if self._btn_back_rect.collidepoint(mouse) else _BACK_BG
        pygame.draw.rect(surface, back_col, self._btn_back_rect, border_radius=4)
        pygame.draw.rect(surface, _BORDER, self._btn_back_rect, 1, border_radius=4)
        font_back = pygame.font.SysFont("Consolas", 12, bold=True)
        b = font_back.render("< Back", True, (200, 200, 220))
        surface.blit(b, (self._btn_back_rect.centerx - b.get_width() // 2,
                         self._btn_back_rect.centery - b.get_height() // 2))

    def draw_login_form(self, surface: pygame.Surface) -> None:
        self._draw_form(surface, "Login", "LOGIN")

    def draw_signup_form(self, surface: pygame.Surface) -> None:
        self._draw_form(surface, "Sign Up", "SIGN UP")
