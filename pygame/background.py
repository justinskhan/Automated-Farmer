#This file will hold the background code  for the game 

import math
import random
import pygame


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------

def _lerp_color(a, b, t):
    """Linearly interpolate between two RGB tuples."""
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _draw_gradient_rect(surface, top_color, bottom_color, rect):
    """Fill a rectangle with a vertical gradient."""
    x, y, w, h = rect
    for row in range(h):
        t = row / max(h - 1, 1)
        color = _lerp_color(top_color, bottom_color, t)
        pygame.draw.line(surface, color, (x, y + row), (x + w - 1, y + row))


# ---------------------------------------------------------------------------
# Cloud
# ---------------------------------------------------------------------------

class _Cloud:
    def __init__(self, sw, sh, speed_scale=1.0, y_band=(0.04, 0.28)):
        self.sw = sw
        self.sh = sh
        self.speed_scale = speed_scale
        self._spawn(offscreen=True)

    def _spawn(self, offscreen=False):
        self.y = random.uniform(0.04, 0.28) * self.sh
        # cloud is made of 3-6 overlapping ellipses
        n = random.randint(3, 6)
        self.puffs = []
        cx = 0
        for i in range(n):
            rx = random.randint(28, 60)
            ry = random.randint(18, 36)
            ox = cx + random.randint(-10, rx)
            oy = random.randint(-ry // 2, ry // 2)
            self.puffs.append((ox, oy, rx, ry))
            cx = ox + rx

        self.width = max(ox + rx for ox, _, rx, _ in self.puffs)
        self.speed = random.uniform(18, 45) * self.speed_scale
        self.alpha = random.randint(170, 230)

        if offscreen:
            self.x = random.uniform(-self.width, self.sw + self.width)
        else:
            self.x = self.sw + self.width + 10

    def update(self, dt):
        self.x -= self.speed * dt
        if self.x + self.width < -20:
            self._spawn(offscreen=False)

    def draw(self, surface):
        cloud_surf = pygame.Surface((self.width + 4, 80), pygame.SRCALPHA)
        color = (255, 255, 255, self.alpha)
        for ox, oy, rx, ry in self.puffs:
            pygame.draw.ellipse(cloud_surf, color,
                                pygame.Rect(ox, 36 + oy - ry, rx * 2, ry * 2))
        surface.blit(cloud_surf, (int(self.x), int(self.y) - 36))


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

class Background:
    # Sky palette: (top, bottom) for sky gradient
    SKY_TOP    = (100, 160, 230)
    SKY_BOTTOM = (173, 216, 230)

    # Hill colours – two depth layers
    HILL_BACK  = (110, 170, 100)
    HILL_FRONT = (80,  140,  70)

    # Grass tuft colour
    GRASS_COLOR = (60, 120, 50)

    def __init__(self, color=(173, 216, 230)):
        # `color` param kept for API compatibility; we ignore it.
        self._sky_cache: pygame.Surface | None = None
        self._cache_size = (0, 0)

        # Clouds – two layers: slow/far and fast/near
        self._clouds_far:  list[_Cloud] = []
        self._clouds_near: list[_Cloud] = []

        # Grass tufts along the bottom strip
        self._tufts: list[dict] = []

        # Sun bob
        self._time = 0.0

        # We initialise lazily on first draw so we know the screen size.
        self._initialised = False

    # ------------------------------------------------------------------
    def _init(self, sw, sh):
        self._initialised = True

        # --- clouds ---
        self._clouds_far  = [_Cloud(sw, sh, speed_scale=0.55) for _ in range(4)]
        self._clouds_near = [_Cloud(sw, sh, speed_scale=1.1)  for _ in range(3)]

        # --- grass tufts ---
        num_tufts = sw // 14
        for _ in range(num_tufts):
            self._tufts.append({
                "x":     random.randint(0, sw),
                "h":     random.randint(6, 14),
                "phase": random.uniform(0, math.tau),
            })

        # Pre-render the static sky gradient into a surface we can blit fast.
        self._bake_sky(sw, sh)

    def _bake_sky(self, sw, sh):
        self._sky_cache = pygame.Surface((sw, sh))
        _draw_gradient_rect(self._sky_cache,
                            self.SKY_TOP, self.SKY_BOTTOM,
                            (0, 0, sw, sh))
        self._cache_size = (sw, sh)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        sw, sh = surface.get_size()

        if not self._initialised:
            self._init(sw, sh)

        # Rebake sky cache if window was resized
        if (sw, sh) != self._cache_size:
            self._bake_sky(sw, sh)

        dt = 0.016   # we don't have dt here; approximate 60 fps
        self._time += dt

        # 1. Sky gradient
        surface.blit(self._sky_cache, (0, 0))

        # 2. Sun
        self._draw_sun(surface, sw, sh)

        # 3. Far clouds
        for c in self._clouds_far:
            c.update(dt)
            c.draw(surface)

        # 4. Back hills
        self._draw_hills(surface, sw, sh,
                         color=self.HILL_BACK,
                         freq=0.0028, amp=0.10, offset=0.58, phase=0.0)

        # 5. Near clouds (in front of back hills)
        for c in self._clouds_near:
            c.update(dt)
            c.draw(surface)

        # 6. Front hills
        self._draw_hills(surface, sw, sh,
                         color=self.HILL_FRONT,
                         freq=0.0042, amp=0.07, offset=0.68, phase=2.1)

        # 7. Grass strip + tufts
        self._draw_grass(surface, sw, sh)

    # ------------------------------------------------------------------
    def _draw_sun(self, surface, sw, sh):
        bob = math.sin(self._time * 0.3) * 4
        cx  = int(sw * 0.82)
        cy  = int(sh * 0.12 + bob)
        r   = 28

        # outer glow rings
        glow_surf = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
        for i in range(4, 0, -1):
            alpha = 18 * i
            gr    = r + i * 10
            pygame.draw.circle(glow_surf, (255, 240, 120, alpha),
                               (r * 3, r * 3), gr)
        surface.blit(glow_surf, (cx - r * 3, cy - r * 3))

        # sun disc
        pygame.draw.circle(surface, (255, 235, 80), (cx, cy), r)
        pygame.draw.circle(surface, (255, 200, 40), (cx, cy), r, 3)

    # ------------------------------------------------------------------
    def _draw_hills(self, surface, sw, sh, color, freq, amp, offset, phase):
        """Draw a smoothly undulating hill silhouette."""
        points = [(0, sh)]
        for x in range(0, sw + 1, 3):
            y = sh * offset - math.sin(x * freq + phase) * sh * amp
            points.append((x, int(y)))
        points.append((sw, sh))
        pygame.draw.polygon(surface, color, points)

    # ------------------------------------------------------------------
    def _draw_grass(self, surface, sw, sh):
        # Solid strip at the very bottom
        strip_h = int(sh * 0.06)
        strip_y = sh - strip_h
        pygame.draw.rect(surface, self.GRASS_COLOR,
                         pygame.Rect(0, strip_y, sw, strip_h))

        # Animated tufts
        sway = math.sin(self._time * 1.8) * 2.5
        for t in self._tufts:
            bx = t["x"]
            by = strip_y
            h  = t["h"]
            tip_x = bx + int(sway * math.sin(t["phase"] + self._time))
            # draw a simple V-shape tuft
            pygame.draw.line(surface, (40, 100, 35),
                             (bx, by), (tip_x, by - h), 2)
            pygame.draw.line(surface, (50, 115, 40),
                             (bx + 3, by), (tip_x + 4, by - h + 2), 2)
            pygame.draw.line(surface, (35, 90, 30),
                             (bx - 3, by), (tip_x - 3, by - h + 3), 2)
