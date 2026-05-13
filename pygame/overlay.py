from __future__ import annotations
import pygame
import math
from objective import ObjectiveStatus
from ui_scale import s as _s
 
 
#colors for the overlay panel and buttons
_OVERLAY_WIN_BG  = ( 20,  60,  20, 210)
_OVERLAY_FAIL_BG = ( 60,  20,  20, 210)
_TITLE_WIN       = ( 80, 230,  80)
_TITLE_FAIL      = (230,  80,  80)
_BODY_TEXT       = (220, 220, 220)
_BTN_COLOR       = ( 60, 140,  60)
_BTN_HOVER       = ( 80, 180,  80)
_BTN_FAIL_COLOR  = (140,  60,  60)
_BTN_FAIL_HOVER  = (180,  80,  80)
_BTN_TEXT        = (255, 255, 255)
 
#font sizes for the overlay
_FONT_TITLE_SIZE = _s(32)
_FONT_BODY_SIZE  = _s(18)
_FONT_BTN_SIZE   = _s(18)
_FONT_SMALL_SIZE = _s(13)
 
#star fill and border colors
_STAR_GOLD        = (255, 200,  20)
_STAR_GOLD_BORDER = (200, 140,   0)
_STAR_GLOW        = (255, 230,  80)
_STAR_EMPTY       = ( 45,  45,  45)
_STAR_EMPTY_BORD  = ( 80,  80,  80)
 
#star animation timing in seconds
_STAR_DELAY = 0.30
_STAR_STEP  = 0.22
_POP_DUR    = 0.28
 
 
def _calc_stars(elapsed: float, time_limit: float | None) -> int:
    #3 stars if used 50% or less of the time limit
    #2 stars if used 80% or less of the time limit
    #1 star if completed but used more than 80%
    #no time limit always gives 3 stars
    if time_limit is None or time_limit <= 0:
        return 3
    ratio = elapsed / time_limit
    if ratio <= 0.50:
        return 3
    if ratio <= 0.80:
        return 2
    return 1
 
 
def _star_points(cx: int, cy: int, r: float, n: int = 5) -> list[tuple[int, int]]:
    #returns the vertices of an n-pointed star centered at cx, cy with outer radius r
    r_in = r * 0.42
    pts  = []
    for i in range(n * 2):
        angle = math.pi / n * i - math.pi / 2
        rad   = r if i % 2 == 0 else r_in
        pts.append((int(cx + rad * math.cos(angle)),
                    int(cy + rad * math.sin(angle))))
    return pts
 
 
class Overlay:
    #draws a full-screen overlay when a level ends
    #win shows an animated star rating and a next level button
    #lose shows a failure message and a retry button
    #handle_event returns true when the player clicks the button
 
    def __init__(self) -> None:
        self._btn_rect:   pygame.Rect | None = None
        self._hovered                         = False
 
        #fonts loaded lazily on first draw
        self._title_font: pygame.font.Font | None = None
        self._body_font:  pygame.font.Font | None = None
        self._btn_font:   pygame.font.Font | None = None
        self._small_font: pygame.font.Font | None = None
 
        #animation state
        self._anim_t   = 0.0
        self._stars    = 0
        self._computed = False
 
    def handle_event(self, event: pygame.event.Event) -> bool:
        #returns true if the player clicked the continue button
        if self._btn_rect is None:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self._btn_rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_rect.collidepoint(event.pos):
                self._reset_anim()
                return True
        return False
 
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
        #advance the animation clock once per frame
        self._anim_t += 1 / 60
 
        title_font, body_font, btn_font, small_font = self._fonts()
        sw, sh = surface.get_size()
        is_win = status == ObjectiveStatus.WIN
 
        #draw a semi-transparent colored backdrop over the whole screen
        bg_color = _OVERLAY_WIN_BG if is_win else _OVERLAY_FAIL_BG
        backdrop = pygame.Surface((sw, sh), pygame.SRCALPHA)
        backdrop.fill(bg_color)
        surface.blit(backdrop, (0, 0))
 
        #draw the centered panel box
        pw = _s(440)
        ph = _s(310) if is_win else _s(280)
        px = (sw - pw) // 2
        py = (sh - ph) // 2
        panel = pygame.Rect(px, py, pw, ph)
 
        pygame.draw.rect(surface, (20, 20, 30), panel, border_radius=_s(12))
        pygame.draw.rect(surface, (80, 80, 110), panel, _s(2), border_radius=_s(12))
 
        old_clip = surface.get_clip()
        surface.set_clip(panel)
 
        total_h = _s(32 + 8)   
        total_h += _s(18 + 14)
        if is_win:
            total_h += _s(88)  
            total_h += _s(17 + 4) * 2  
        else:
            total_h += _s(17 + 6) * 2 
        btn_h_est = btn_font.size("X")[1] + _s(14)
        total_h += _s(14) + btn_h_est 

        y = py + (ph - total_h) // 2 
        #draw the title text
        title_text  = "Level Complete!" if is_win else "Time's Up!"
        title_color = _TITLE_WIN if is_win else _TITLE_FAIL
        title_surf  = title_font.render(title_text, True, title_color)
        surface.blit(title_surf, (px + (pw - title_surf.get_width()) // 2, y))
        y += title_surf.get_height() + _s(8)
 
        #draw the level name below the title
        name_surf = body_font.render(level_name, True, _BODY_TEXT)
        surface.blit(name_surf, (px + (pw - name_surf.get_width()) // 2, y))
        y += name_surf.get_height() + _s(14)
 
        if is_win:
            #calculate star rating once when the overlay first appears
            if not self._computed:
                self._stars    = _calc_stars(elapsed, time_limit)
                self._computed = True
 
            #stars draw outside the panel clip so glows arent cut off at the edges
            surface.set_clip(old_clip)
            self._draw_stars(surface, px, y, pw)
            surface.set_clip(panel)
            y += _s(88)
 
            #draw harvest count and time used stats
            stats = [f"Harvested: {harvests_done} / {harvests_required}"]
            if time_limit is not None:
                stats.append(f"Time: {elapsed:.1f}s / {time_limit:.0f}s")
            for line in stats:
                ls = small_font.render(line, True, (160, 200, 160))
                surface.blit(ls, (px + (pw - ls.get_width()) // 2, y))
                y += ls.get_height() + _s(4)
 
            btn_label     = "Next Level"
            btn_base_col  = _BTN_COLOR
            btn_hover_col = _BTN_HOVER
 
        else:
            #reset computed so stars recalculate fresh on the next win
            self._computed = False
 
            #draw harvest count and a tip for the player
            stats = [
                f"Harvested: {harvests_done} / {harvests_required}",
                "Tip: plan your route and use loops to save time.",
            ]
            for line in stats:
                ls = small_font.render(line, True, (200, 140, 140))
                surface.blit(ls, (px + (pw - ls.get_width()) // 2, y))
                y += ls.get_height() + _s(6)
 
            btn_label     = "Try Again"
            btn_base_col  = _BTN_FAIL_COLOR
            btn_hover_col = _BTN_FAIL_HOVER
 
        #draw the next level or retry button
        btn_surf = btn_font.render(btn_label, True, _BTN_TEXT)
        bw = btn_surf.get_width() + _s(44)
        bh = btn_surf.get_height() + _s(14)
        bx = px + (pw - bw) // 2
        by = y + _s(14) 
        self._btn_rect = pygame.Rect(bx, by, bw, bh)
 
        pygame.draw.rect(surface,
                         btn_hover_col if self._hovered else btn_base_col,
                         self._btn_rect, border_radius=_s(6))
        surface.blit(btn_surf,
                     (bx + (bw - btn_surf.get_width())  // 2,
                      by + (bh - btn_surf.get_height()) // 2))
 
        surface.set_clip(old_clip)
 
    def _fonts(self):
        #load all fonts once and cache them
        if self._title_font is None:
            self._title_font = pygame.font.SysFont("Consolas", _FONT_TITLE_SIZE, bold=True)
            self._body_font  = pygame.font.SysFont("Consolas", _FONT_BODY_SIZE)
            self._btn_font   = pygame.font.SysFont("Consolas", _FONT_BTN_SIZE,   bold=True)
            self._small_font = pygame.font.SysFont("Consolas", _FONT_SMALL_SIZE)
        return self._title_font, self._body_font, self._btn_font, self._small_font
 
    def _reset_anim(self) -> None:
        #reset the animation so stars play again next time the overlay opens
        self._anim_t   = 0.0
        self._computed = False
 
    def _draw_stars(self, surface: pygame.Surface,
                    panel_x: int, top_y: int, panel_w: int) -> None:
        #draws three stars with a staggered bounce pop-in animation
        #earned stars are gold, unearned stars are dark outlines
        spacing  = _s(82)
        total_w  = spacing * 2
        start_x  = panel_x + panel_w // 2 - total_w // 2
        base_r   = _s(26)
        centre_y = top_y + _s(36)
 
        for i in range(3):
            cx         = start_x + i * spacing
            star_start = _STAR_DELAY + i * _STAR_STEP
            t_local    = self._anim_t - star_start
            earned     = (i + 1) <= self._stars
 
            if t_local < 0:
                #not yet time for this star, draw a dim placeholder
                self._blit_star(surface, cx, centre_y, base_r,
                                _STAR_EMPTY, _STAR_EMPTY_BORD, alpha=70)
                continue
 
            prog = min(1.0, t_local / _POP_DUR)
 
            if not earned:
                #unearned stars fade in as dark outlines with no pop
                self._blit_star(surface, cx, centre_y, base_r,
                                _STAR_EMPTY, _STAR_EMPTY_BORD,
                                alpha=int(70 + 80 * prog))
                continue
 
            #bounce easing: scale overshoots then settles back to full size
            if prog < 0.55:
                t = prog / 0.55
                t = t * t * (3 - 2 * t)
                r = int(base_r * t * 1.40)
            elif prog < 0.78:
                t = (prog - 0.55) / 0.23
                r = int(base_r * (1.40 - 0.40 * t))
            else:
                r = base_r
 
            r = max(r, 1)
 
            #draw a gold glow ring that fades as the star finishes landing
            if prog > 0.5:
                glow_fade = 1.0 - (prog - 0.5) / 0.5
                ga        = int(140 * glow_fade)
                gr        = r + _s(10)
                gsurf     = pygame.Surface((gr * 2 + 4, gr * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(gsurf, (*_STAR_GLOW, ga), (gr + 2, gr + 2), gr)
                surface.blit(gsurf, (cx - gr - 2, centre_y - gr - 2))
 
            self._blit_star(surface, cx, centre_y, r, _STAR_GOLD, _STAR_GOLD_BORDER)
 
            #shoot sparkle particles outward at the peak of the pop
            if 0.50 < prog < 0.88:
                self._draw_sparkles(surface, cx, centre_y, r, prog)
 
    def _blit_star(self, surface: pygame.Surface,
                   cx: int, cy: int, r: int,
                   fill, border, alpha: int = 255) -> None:
        #draws a single star shape, using an offscreen surface when alpha is needed
        pts = _star_points(cx, cy, r)
        if alpha < 255:
            size = r * 2 + 4
            tmp  = pygame.Surface((size, size), pygame.SRCALPHA)
            shifted = [(x - cx + r + 2, y - cy + r + 2) for x, y in pts]
            pygame.draw.polygon(tmp, (*fill,   alpha), shifted)
            pygame.draw.polygon(tmp, (*border, alpha), shifted, _s(1))
            surface.blit(tmp, (cx - r - 2, cy - r - 2))
        else:
            pygame.draw.polygon(surface, fill,   pts)
            pygame.draw.polygon(surface, border, pts, _s(1))
 
    @staticmethod
    def _draw_sparkles(surface: pygame.Surface,
                       cx: int, cy: int, r: int, prog: float) -> None:
        #draws eight gold particles that fly outward as the star pops in
        burst = (prog - 0.50) / 0.38
        dist  = r * 2.0 * burst
        alpha = int(255 * (1 - burst))
        for i in range(8):
            angle = 2 * math.pi * i / 8
            sx    = int(cx + dist * math.cos(angle))
            sy    = int(cy + dist * math.sin(angle))
            size  = max(2, int(_s(4) * (1 - burst)))
            dot   = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 220, 60, alpha), (size, size), size)
            surface.blit(dot, (sx - size, sy - size))