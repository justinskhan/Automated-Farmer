from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class TreeNode:
    key: str
    label: str
    sublabel: str
    min_level_index: int   # manager._index must be >= this to allow unlocking
    parent_key: Optional[str]
    col: int               # grid column for visual layout (0-4)
    row: int               # grid row for visual layout (0-4)


# Tree is laid out on a 5×5 grid:
#
#              col 0        col 2        col 4
# row 0                   [move]
# row 1                   [plant]
# row 2                   [harvest]
# row 3      [if/else]               [for loop]
# row 4                              [while loop]
#
NODES: dict[str, TreeNode] = {
    "move":    TreeNode("move",    "Move",        "move(direction)",     0, None,      2, 0),
    "plant":   TreeNode("plant",   "Plant",       "plant(crop)",         0, "move",    2, 1),
    "harvest": TreeNode("harvest", "Harvest",     "harvest()",           0, "plant",   2, 2),
    "if":      TreeNode("if",      "If / Else",   "if, elif, else",      1, "harvest", 0, 3),
    "for":     TreeNode("for",     "For Loops",   "for i in range(n):",  2, "harvest", 4, 3),
    "while":   TreeNode("while",   "While Loops", "while condition:",    4, "for",     4, 4),
}

EDGES: list[tuple[str, str]] = [
    ("move",    "plant"),
    ("plant",   "harvest"),
    ("harvest", "if"),
    ("harvest", "for"),
    ("for",     "while"),
]

_AUTO_UNLOCKED: frozenset[str] = frozenset({"move", "plant", "harvest"})


class UnlockTree:
    def __init__(self) -> None:
        self._unlocked: set[str] = set(_AUTO_UNLOCKED)

    def is_unlocked(self, key: str) -> bool:
        return key in self._unlocked

    def can_unlock(self, key: str, level_index: int) -> bool:
        """Return True if the player can click to unlock this node right now."""
        if key in self._unlocked:
            return False
        node = NODES.get(key)
        if node is None:
            return False
        if level_index < node.min_level_index:
            return False
        if node.parent_key and node.parent_key not in self._unlocked:
            return False
        return True

    def try_unlock(self, key: str, level_index: int) -> bool:
        """Unlock the node if allowed. Returns True on success."""
        if not self.can_unlock(key, level_index):
            return False
        self._unlocked.add(key)
        return True

    def effective_commands(self, level_commands: list[str]) -> list[str]:
        """Intersect a level's allowed_commands list with what is unlocked."""
        return [cmd for cmd in level_commands if cmd in self._unlocked]
