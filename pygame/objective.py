from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
 
 
#tracks whether the level is still running, won, or failed
class ObjectiveStatus(Enum):
    PLAYING = auto()
    WIN     = auto()
    FAIL    = auto()
 
 
#holds the goal and rules for each level
@dataclass
class Objective:
    #how many crops the player needs to harvest to win
    harvests_required: int = 1
 
    #time limit in seconds, set to None if there is no limit
    time_limit: float | None = None
 
    #which commands are allowed in the ide for this level
    #while is added on level 5 to unlock while loop syntax
    allowed_commands: list[str] = field(
        default_factory=lambda: ["move", "plant", "harvest"]
    )
 
    #runtime state tracked each frame by main.py
    harvests_done: int = 0
    elapsed: float = 0.0
    status: ObjectiveStatus = ObjectiveStatus.PLAYING
 
    #resets all runtime state back to the start
    def reset(self) -> None:
        self.harvests_done = 0
        self.elapsed = 0.0
        self.status = ObjectiveStatus.PLAYING
 
    #called every time the player successfully harvests a crop
    def record_harvest(self) -> None:
        if self.status != ObjectiveStatus.PLAYING:
            return
        self.harvests_done += 1
        self._check_win()
 
    #advances the timer each frame and triggers fail if time runs out
    def update(self, dt: float) -> None:
        if self.status != ObjectiveStatus.PLAYING:
            return
        if self.time_limit is not None:
            self.elapsed += dt
            if self.elapsed >= self.time_limit:
                self.status = ObjectiveStatus.FAIL
 
    #checks if the player has hit the harvest goal and sets win if so
    def _check_win(self) -> None:
        if self.harvests_done >= self.harvests_required:
            self.status = ObjectiveStatus.WIN
 
    #returns how many seconds are left, or None if there is no timer
    @property
    def time_remaining(self) -> float | None:
        if self.time_limit is None:
            return None
        return max(0.0, self.time_limit - self.elapsed)
 
    #returns a short summary used by the overlay to show progress
    def summary_lines(self) -> list[str]:
        lines = [f"Harvest {self.harvests_done}/{self.harvests_required} crops"]
        if self.time_limit is not None:
            remaining = self.time_remaining
            lines.append(f"Time left: {remaining:.1f}s")
        return lines