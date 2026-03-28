
Copy

from __future__ import annotations
import pygame
from objective import ObjectiveStatus
 
 
#colors for the overlay panel and buttons
_OVERLAY_WIN_BG  = ( 20,  60,  20, 210)   #dark green semi-transparent backdrop
_OVERLAY_FAIL_BG = ( 60,  20,  20, 210)   #dark red semi-transparent backdrop
_TITLE_WIN       = ( 80, 230,  80)
_TITLE_FAIL      = (230,  80,  80)
_BODY_TEXT       = (220, 220, 220)
_BTN_COLOR       = ( 60, 140,  60)
_BTN_HOVER       = ( 80, 180,  80)
_BTN_FAIL_COLOR  = (140,  60,  60)
_BTN_FAIL_HOVER  = (180,  80,  80)
_BTN_TEXT        = (255, 255, 255)
 
#font sizes for the overlay
_FONT_TITLE_SIZE = 32
_FONT_BODY_SIZE  = 20
_FONT_BTN_SIZE   = 18
 
 
#this class draws the win or fail screen that freezes the game
class Overlay:
 
    def __init__(self) -> None:
        self._title_font: pygame.font.Font | None = None
        self._body_font:  pygame.font.Font | None = None
        self._btn_font:   pygame.font.Font | None = None
        self._btn_rect:   pygame.Rect | None = None
        self._hovered = False
 
    #avoids loading fonts before the overlay is first drawn
    def _fonts(self) -> tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]:
        if self._title_font is None:
            self._title_font = pygame.font.SysFont("Consolas", _FONT_TITLE_SIZE, bold=True)
            self._body_font  = pygame.font.SysFont("Consolas", _FONT_BODY_SIZE)
            self._btn_font   = pygame.font.SysFont("Consolas", _FONT_BTN_SIZE, bold=True)
        return self._title_font, self._body_font, self._btn_font  # type: ignore[return-value]
 
    #returns true if the player clicked the continue button
    def handle_event(self, event: pygame.event.Event) -> bool:
        if self._btn_rect is None:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self._btn_rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_rect.collidepoint(event.pos):
                return True
        return False
 
    #draws the full overlay including backdrop, panel, stats and button
    def draw(
        self,
        surface: pygame.Surface,
        status: ObjectiveStatus,
        level_name: str,
        harvests_done: int,
        harvests_required: int,
        elapsed: float,
        time_limit: float | None,
    ) -> None:
        title_font, body_font, btn_font = self._fonts()
        sw, sh = surface.get_size()
 
        #draw a semi-transparent colored backdrop over the whole screen
        is_win = status == ObjectiveStatus.WIN
        bg_color = _OVERLAY_WIN_BG if is_win else _OVERLAY_FAIL_BG
        backdrop = pygame.Surface((sw, sh), pygame.SRCALPHA)
        backdrop.fill(bg_color)
        surface.blit(backdrop, (0, 0))
 
        #draw the centered panel box
        pw, ph = 420, 280
        px, py = (sw - pw) // 2, (sh - ph) // 2
        panel = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(surface, (20, 20, 30), panel, border_radius=12)
        pygame.draw.rect(surface, (80, 80, 110), panel, 2, border_radius=12)
 
        #clip everything so nothing renders outside the panel
        old_clip = surface.get_clip()
        surface.set_clip(panel)
 
        y = py + 20
 
        #draw the title text
        title_text = "Level Complete!" if is_win else "Time's Up!"
        title_color = _TITLE_WIN if is_win else _TITLE_FAIL
        title_surf = title_font.render(title_text, True, title_color)
        surface.blit(title_surf, (px + (pw - title_surf.get_width()) // 2, y))
        y += title_surf.get_height() + 12
 
        #draw the level name below the title
        name_surf = body_font.render(level_name, True, _BODY_TEXT)
        surface.blit(name_surf, (px + (pw - name_surf.get_width()) // 2, y))
        y += name_surf.get_height() + 16
 
        #draw harvest count and optional time used stats
        stats = [f"Crops harvested: {harvests_done} / {harvests_required}"]
        if time_limit is not None:
            stats.append(f"Time used: {elapsed:.1f}s / {time_limit:.0f}s")
        for line in stats:
            s = body_font.render(line, True, _BODY_TEXT)
            surface.blit(s, (px + (pw - s.get_width()) // 2, y))
            y += s.get_height() + 6
 
        y += 10
 
        #draw the next level or retry button
        btn_label = "Next Level" if is_win else "Retry"
        btn_surf = btn_font.render(btn_label, True, _BTN_TEXT)
        bw = btn_surf.get_width() + 40
        bh = btn_surf.get_height() + 14
        bx = px + (pw - bw) // 2
        by = y
 
        self._btn_rect = pygame.Rect(bx, by, bw, bh)
 
        base = _BTN_COLOR if is_win else _BTN_FAIL_COLOR
        hov  = _BTN_HOVER if is_win else _BTN_FAIL_HOVER
        pygame.draw.rect(surface, hov if self._hovered else base,
                         self._btn_rect, border_radius=6)
        surface.blit(btn_surf, (bx + 20, by + 7))
 
        surface.set_clip(old_clip)