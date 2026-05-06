"""Draws the tech-tree unlock screen."""
from __future__ import annotations

import pygame
from ui_scale import s as _s
from unlock_tree import UnlockTree, NODES, EDGES

# ── palette ────────────────────────────────────────────────────────────────────
_BG          = ( 28,  35,  28)
_LINE        = ( 65,  90,  65)

_NODE_UNL_BG  = ( 42,  60,  42)
_NODE_UNL_BDR = ( 78, 118,  78)
_NODE_UNL_TXT = (162, 210, 148)

_NODE_AVL_BG  = ( 48, 138,  48)
_NODE_AVL_BDR = ( 95, 200,  95)
_NODE_AVL_TXT = (235, 255, 225)
_NODE_AVL_HOV = ( 68, 162,  68)   # hover tint

_NODE_LCK_BG  = ( 38,  38,  50)
_NODE_LCK_BDR = ( 58,  58,  74)
_NODE_LCK_TXT = ( 95,  95, 108)


def draw(
    surface: pygame.Surface,
    unlock_tree: UnlockTree,
    level_index: int,
) -> tuple[dict[str, pygame.Rect], pygame.Rect]:
    """
    Render the unlock tech-tree.
    Returns (node_rects_by_key, back_button_rect).
    """
    sw, sh = surface.get_size()
    surface.fill(_BG)

    # ── title ──────────────────────────────────────────────────────────────
    font_title = pygame.font.SysFont("Consolas", _s(26), bold=True)
    title_surf = font_title.render("Unlocks", True, (148, 215, 128))
    surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, _s(16)))

    # ── layout ─────────────────────────────────────────────────────────────
    NODE_W  = _s(148)
    NODE_H  = _s(64)
    COL_GAP = _s(198)   # center-to-center horizontal distance
    ROW_GAP = _s(126)   # center-to-center vertical distance

    grid_w = 4 * COL_GAP
    ox = (sw - grid_w) // 2
    oy = _s(72)

    def _ctr(col: int, row: int) -> tuple[int, int]:
        return (ox + col * COL_GAP, oy + row * ROW_GAP)

    mouse = pygame.mouse.get_pos()

    # ── connector lines ────────────────────────────────────────────────────
    for pk, ck in EDGES:
        px, py = _ctr(NODES[pk].col, NODES[pk].row)
        cx, cy = _ctr(NODES[ck].col, NODES[ck].row)
        p_bot  = (px, py + NODE_H // 2 + _s(2))
        c_top  = (cx, cy - NODE_H // 2 - _s(2))
        lw     = _s(2)
        if px == cx:
            pygame.draw.line(surface, _LINE, p_bot, c_top, lw)
        else:
            mid_y = (py + cy) // 2
            pygame.draw.line(surface, _LINE, p_bot,       (px, mid_y), lw)
            pygame.draw.line(surface, _LINE, (px, mid_y), (cx, mid_y), lw)
            pygame.draw.line(surface, _LINE, (cx, mid_y), c_top,       lw)

    # ── nodes ──────────────────────────────────────────────────────────────
    font_label  = pygame.font.SysFont("Consolas", _s(14), bold=True)
    font_sub    = pygame.font.SysFont("Consolas", _s(11))
    font_status = pygame.font.SysFont("Consolas", _s(11), bold=True)

    node_rects: dict[str, pygame.Rect] = {}

    for key, nd in NODES.items():
        cx, cy = _ctr(nd.col, nd.row)
        rect = pygame.Rect(cx - NODE_W // 2, cy - NODE_H // 2, NODE_W, NODE_H)
        node_rects[key] = rect

        unlocked  = unlock_tree.is_unlocked(key)
        available = unlock_tree.can_unlock(key, level_index)
        hovered   = available and rect.collidepoint(mouse)

        if unlocked:
            bg, bdr, tc, status = _NODE_UNL_BG, _NODE_UNL_BDR, _NODE_UNL_TXT, "Unlocked"
        elif available:
            bg  = _NODE_AVL_HOV if hovered else _NODE_AVL_BG
            bdr = _NODE_AVL_BDR
            tc  = _NODE_AVL_TXT
            status = "Unlock"
        else:
            bg, bdr, tc, status = _NODE_LCK_BG, _NODE_LCK_BDR, _NODE_LCK_TXT, "Locked"

        pygame.draw.rect(surface, bg,  rect, border_radius=_s(6))
        pygame.draw.rect(surface, bdr, rect, _s(1), border_radius=_s(6))

        # node label (top half)
        lbl = font_label.render(nd.label, True, tc)
        surface.blit(lbl, (cx - lbl.get_width() // 2,
                            cy - _s(12) - lbl.get_height() // 2))

        # sublabel / command hint (middle)
        sub = font_sub.render(nd.sublabel, True, tuple(max(0, c - 40) for c in tc))
        surface.blit(sub, (cx - sub.get_width() // 2, cy - sub.get_height() // 2))

        # status badge (bottom half)
        st = font_status.render(status, True, tc)
        surface.blit(st, (cx - st.get_width() // 2,
                           cy + _s(12) - st.get_height() // 2))

    # ── back button ────────────────────────────────────────────────────────
    bw, bh      = _s(112), _s(38)
    back_rect   = pygame.Rect(_s(18), sh - bh - _s(18), bw, bh)
    back_hov    = back_rect.collidepoint(mouse)
    pygame.draw.rect(surface, (58, 128, 58) if back_hov else (42, 98, 42),
                     back_rect, border_radius=_s(5))
    pygame.draw.rect(surface, (88, 162, 88), back_rect, _s(1), border_radius=_s(5))
    font_back = pygame.font.SysFont("Consolas", _s(13), bold=True)
    bl = font_back.render("← Back", True, (228, 255, 228))
    surface.blit(bl, (back_rect.centerx - bl.get_width()  // 2,
                       back_rect.centery - bl.get_height() // 2))

    return node_rects, back_rect
