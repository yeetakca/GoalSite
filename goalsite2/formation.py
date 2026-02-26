from __future__ import annotations

from typing import List, Tuple


def build_line_distribution(formation_name: str, team_size: int) -> List[int]:
    parts = [int(chunk) for chunk in formation_name.split("-") if chunk.strip().isdigit()]
    outfield_slots = max(team_size - 1, 1)

    if not parts:
        parts = [outfield_slots]

    total = sum(parts)
    if total <= 0:
        return [outfield_slots]

    scaled = [max(1, round(outfield_slots * p / total)) for p in parts]

    while sum(scaled) > outfield_slots:
        largest_idx = max(range(len(scaled)), key=lambda index: scaled[index])
        if scaled[largest_idx] > 1:
            scaled[largest_idx] -= 1
        else:
            break

    while sum(scaled) < outfield_slots:
        smallest_idx = min(range(len(scaled)), key=lambda index: scaled[index])
        scaled[smallest_idx] += 1

    return scaled


def role_positions(
    formation_name: str,
    team_size: int,
    pitch_rect: Tuple[int, int, int, int],
    team_id: int,
) -> List[tuple[str, tuple[float, float]]]:
    left, top, width, height = pitch_rect

    distribution = build_line_distribution(formation_name, team_size)
    roles = ["DEF", "MID", "FWD"]

    player_roles_positions: List[tuple[str, tuple[float, float]]] = []

    keeper_x = left + 35 if team_id == 0 else left + width - 35
    keeper_y = top + height / 2
    player_roles_positions.append(("GK", (keeper_x, keeper_y)))

    line_count = len(distribution)
    for line_index, line_players in enumerate(distribution):
        role = roles[min(line_index, len(roles) - 1)]

        progress = (line_index + 1) / (line_count + 1)
        if team_id == 0:
            line_x = left + 90 + progress * (width * 0.40)
        else:
            line_x = left + width - 90 - progress * (width * 0.40)

        if line_players == 1:
            ys = [top + height / 2]
        else:
            ys = [top + (height * (slot + 1) / (line_players + 1)) for slot in range(line_players)]

        for y in ys:
            player_roles_positions.append((role, (line_x, y)))

    return player_roles_positions[:team_size]
