from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pygame


@dataclass
class Player:
    player_id: int
    team_id: int
    role: str
    home_position: pygame.Vector2
    position: pygame.Vector2
    velocity: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    radius: int = 7
    max_speed: float = 170.0
    has_ball: bool = False
    max_stamina: float = 100.0
    stamina: float = 100.0


@dataclass
class Ball:
    position: pygame.Vector2
    velocity: pygame.Vector2 = field(default_factory=lambda: pygame.Vector2(0, 0))
    radius: int = 4
    possessor_id: Optional[int] = None


@dataclass
class TeamState:
    team_id: int
    score: int = 0
    has_possession: bool = False
