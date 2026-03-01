from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional

import pygame

from goalsite2.entities import Ball, Player, TeamState
from goalsite2.formation import role_positions


@dataclass
class InputState:
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    sprint: bool = False


class Game:
    def __init__(self, config: Dict):
        pygame.init()

        self.config = config
        seed = self.config.get("seed")
        self.random = random.Random(seed)

        self.screen_width = 1200
        self.screen_height = 760
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("GoalSite2 MVP")

        self.clock = pygame.time.Clock()
        self.tick_rate = int(self.config.get("tick_rate", 60))

        self.pitch = pygame.Rect(60, 60, self.screen_width - 120, self.screen_height - 120)
        self.left_goal = pygame.Rect(self.pitch.left - 8, self.pitch.centery - 70, 8, 140)
        self.right_goal = pygame.Rect(self.pitch.right, self.pitch.centery - 70, 8, 140)

        self.team_size = max(2, int(self.config.get("team_size", 3)))
        self.player_max_speed = float(self.config.get("player_max_speed", 170.0))
        self.player_max_stamina = float(self.config.get("player_max_stamina", 100.0))
        self.sprint_stamina_drain = float(self.config.get("sprint_stamina_drain", 40.0))
        self.stamina_regen_rate = float(self.config.get("stamina_regen_rate", 15.0))
        self.exhaustion_cooldown_seconds = float(self.config.get("exhaustion_cooldown_seconds", 0.45))
        self.action_debug_logs = bool(self.config.get("logs_enabled", False))
        self.post_kick_pickup_lockout_seconds = float(self.config.get("post_kick_pickup_lockout_seconds", 0.12))
        self.ball_friction = float(self.config.get("ball_friction", 0.985))
        self.match_duration = int(self.config.get("match_duration_seconds", 90))
        self.formation_name = str(self.config.get("formation_name", "1-1-1"))

        self.teams = [TeamState(team_id=0), TeamState(team_id=1)]
        self.players: List[Player] = []
        self.ball = Ball(position=pygame.Vector2(self.pitch.centerx, self.pitch.centery))
        self.ball_pickup_lockout = 0.0

        self.input_state = InputState()
        self.active_player_id: Optional[int] = None

        self.time_remaining = float(self.match_duration)
        self.running = True
        self.last_action_at = 0
        self.action_cooldown_ms = 140
        self.first_half_duration = self.match_duration / 2.0
        self.halftime_done = False
        self.team0_attacks_right = True

        self._spawn_match()

    def _spawn_match(self) -> None:
        self.players.clear()

        pitch_rect = (self.pitch.left, self.pitch.top, self.pitch.width, self.pitch.height)
        team0_positions = role_positions(self.formation_name, self.team_size, pitch_rect, 0)
        team1_positions = role_positions(self.formation_name, self.team_size, pitch_rect, 1)

        player_id = 0
        for team_id, position_bundle in ((0, team0_positions), (1, team1_positions)):
            for role, (x, y) in position_bundle:
                self.players.append(
                    Player(
                        player_id=player_id,
                        team_id=team_id,
                        role=role,
                        home_position=pygame.Vector2(x, y),
                        position=pygame.Vector2(x, y),
                        max_speed=self.player_max_speed,
                        max_stamina=self.player_max_stamina,
                        stamina=self.player_max_stamina,
                        exhaustion_cooldown=0.0,
                    )
                )
                player_id += 1

        self.ball.position = pygame.Vector2(self.pitch.centerx, self.pitch.centery)
        self.ball.velocity = pygame.Vector2(0, 0)
        self.ball.possessor_id = None
        self.team0_attacks_right = True
        self.halftime_done = False

        self._assign_human_control()
        self._recompute_possession()

    def _assign_human_control(self) -> None:
        if not self.config.get("human_control_enabled", True):
            self.active_player_id = None
            return

        candidate_ids = [player.player_id for player in self.players if player.team_id == 0]
        if not candidate_ids:
            self.active_player_id = None
            return

        if self.config.get("random_human_player", True):
            self.active_player_id = self.random.choice(candidate_ids)
        else:
            self.active_player_id = candidate_ids[0]

    def _active_player(self) -> Optional[Player]:
        if self.active_player_id is None:
            return None
        return next((player for player in self.players if player.player_id == self.active_player_id), None)

    def _recompute_possession(self) -> None:
        for team in self.teams:
            team.has_possession = False

        for player in self.players:
            player.has_ball = self.ball.possessor_id == player.player_id
            if player.has_ball:
                self.teams[player.team_id].has_possession = True

    def _is_attack_mode(self) -> bool:
        active_player = self._active_player()
        if active_player is None:
            return False
        return self.teams[active_player.team_id].has_possession

    def _player_vector_from_input(self) -> pygame.Vector2:
        vector = pygame.Vector2(0, 0)
        if self.input_state.up:
            vector.y -= 1
        if self.input_state.down:
            vector.y += 1
        if self.input_state.left:
            vector.x -= 1
        if self.input_state.right:
            vector.x += 1

        if vector.length_squared() > 0:
            vector = vector.normalize()
        return vector

    def _nearest_teammate(self, source: Player, far: bool = False) -> Optional[Player]:
        teammates = [
            player
            for player in self.players
            if player.team_id == source.team_id and player.player_id != source.player_id
        ]
        if not teammates:
            return None

        if far:
            return max(teammates, key=lambda player: player.position.distance_to(source.position))
        return min(teammates, key=lambda player: player.position.distance_to(source.position))

    def _kick_ball_toward(self, source: Player, target: pygame.Vector2, power: float) -> bool:
        direction = target - source.position
        if direction.length_squared() == 0:
            return False
        direction = direction.normalize()

        self.ball.possessor_id = None
        self.ball.position = source.position + direction * (source.radius + self.ball.radius + 2)
        self.ball.velocity = direction * power
        self.ball_pickup_lockout = self.post_kick_pickup_lockout_seconds
        self._recompute_possession()
        return True

    def _log_action_attempt(
        self,
        key: int,
        success: bool,
        reason: str,
        active_player: Optional[Player],
        attack_mode: Optional[bool] = None,
        has_ball: Optional[bool] = None,
    ) -> None:
        if not self.action_debug_logs:
            return

        player_id = "none" if active_player is None else str(active_player.player_id)
        team_id = "none" if active_player is None else str(active_player.team_id)
        stamina = "n/a" if active_player is None else f"{active_player.stamina:.1f}"
        attack_label = "n/a" if attack_mode is None else str(attack_mode)
        has_ball_label = "n/a" if has_ball is None else str(has_ball)
        time_left = max(0, int(self.time_remaining))
        print(
            f"[ACTION] key={pygame.key.name(key)} success={success} reason={reason} "
            f"player={player_id} team={team_id} attack={attack_label} has_ball={has_ball_label} "
            f"stamina={stamina} t={time_left}s"
        )

    def _attempt_action(self, key: int) -> None:
        now = pygame.time.get_ticks()
        if now - self.last_action_at < self.action_cooldown_ms:
            remaining = self.action_cooldown_ms - (now - self.last_action_at)
            self._log_action_attempt(key, False, f"cooldown:{max(0, remaining)}ms", self._active_player())
            return

        active_player = self._active_player()
        if active_player is None:
            self._log_action_attempt(key, False, "no_active_player", None)
            return

        attack_mode = self._is_attack_mode()
        has_ball = active_player.has_ball

        if key == pygame.K_s:
            if attack_mode and has_ball:
                teammate = self._nearest_teammate(active_player)
                if teammate is not None:
                    kicked = self._kick_ball_toward(active_player, teammate.position, 260)
                    if kicked:
                        self._log_action_attempt(key, True, "short_pass", active_player, attack_mode, has_ball)
                    else:
                        self._log_action_attempt(key, False, "invalid_kick_direction", active_player, attack_mode, has_ball)
                else:
                    self._log_action_attempt(key, False, "no_teammate", active_player, attack_mode, has_ball)
                self.last_action_at = now
            else:
                reason = "not_attack_mode" if not attack_mode else "no_ball"
                self._log_action_attempt(key, False, reason, active_player, attack_mode, has_ball)
            return

        if key == pygame.K_a:
            if attack_mode and has_ball:
                teammate = self._nearest_teammate(active_player, far=True)
                if teammate is not None:
                    kicked = self._kick_ball_toward(active_player, teammate.position, 420)
                    if kicked:
                        self._log_action_attempt(key, True, "long_pass", active_player, attack_mode, has_ball)
                    else:
                        self._log_action_attempt(key, False, "invalid_kick_direction", active_player, attack_mode, has_ball)
                else:
                    self._log_action_attempt(key, False, "no_teammate", active_player, attack_mode, has_ball)
                self.last_action_at = now
            else:
                reason = "not_attack_mode" if not attack_mode else "no_ball"
                self._log_action_attempt(key, False, reason, active_player, attack_mode, has_ball)
            return

        if key == pygame.K_w:
            if not attack_mode:
                if self.ball.position.distance_to(active_player.position) < 24:
                    self.ball.possessor_id = active_player.player_id
                    self.last_action_at = now
                    self._log_action_attempt(key, True, "tackle_success", active_player, attack_mode, has_ball)
                else:
                    self._log_action_attempt(key, False, "too_far_from_ball", active_player, attack_mode, has_ball)
            else:
                self._log_action_attempt(key, False, "in_attack_mode", active_player, attack_mode, has_ball)
            return

        if key == pygame.K_d:
            if attack_mode and has_ball:
                team0_target_x = self.pitch.right if self.team0_attacks_right else self.pitch.left
                team1_target_x = self.pitch.left if self.team0_attacks_right else self.pitch.right
                goal_x = team0_target_x if active_player.team_id == 0 else team1_target_x
                goal_y = self.pitch.centery
                kicked = self._kick_ball_toward(active_player, pygame.Vector2(goal_x, goal_y), 520)
                if kicked:
                    self._log_action_attempt(key, True, "shot", active_player, attack_mode, has_ball)
                else:
                    self._log_action_attempt(key, False, "invalid_kick_direction", active_player, attack_mode, has_ball)
            else:
                reason = "not_attack_mode" if not attack_mode else "no_ball"
                self._log_action_attempt(key, False, reason, active_player, attack_mode, has_ball)
            self.last_action_at = now
            return

        self._log_action_attempt(key, False, "unsupported_action_key", active_player, attack_mode, has_ball)

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_UP:
                    self.input_state.up = True
                elif event.key == pygame.K_DOWN:
                    self.input_state.down = True
                elif event.key == pygame.K_LEFT:
                    self.input_state.left = True
                elif event.key == pygame.K_RIGHT:
                    self.input_state.right = True
                elif event.key == pygame.K_e:
                    self.input_state.sprint = True
                elif event.key in {pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_w}:
                    self._attempt_action(event.key)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_UP:
                    self.input_state.up = False
                elif event.key == pygame.K_DOWN:
                    self.input_state.down = False
                elif event.key == pygame.K_LEFT:
                    self.input_state.left = False
                elif event.key == pygame.K_RIGHT:
                    self.input_state.right = False
                elif event.key == pygame.K_e:
                    self.input_state.sprint = False

    def _update_players(self, dt: float) -> None:
        if self.ball_pickup_lockout > 0:
            self.ball_pickup_lockout = max(0.0, self.ball_pickup_lockout - dt)

        active_player = self._active_player()
        active_vector = self._player_vector_from_input()

        for player in self.players:
            if active_player is not None and player.player_id == active_player.player_id:
                moving = active_vector.length_squared() > 0
                if player.exhaustion_cooldown > 0:
                    player.exhaustion_cooldown = max(0.0, player.exhaustion_cooldown - dt)

                wants_sprint = self.input_state.sprint and moving
                sprinting = wants_sprint and player.stamina > 0 and player.exhaustion_cooldown <= 0
                speed = player.max_speed * (1.45 if sprinting else 1.0)
                player.velocity = active_vector * speed

                if sprinting:
                    player.stamina = max(0.0, player.stamina - self.sprint_stamina_drain * dt)
                    if player.stamina <= 0:
                        player.exhaustion_cooldown = self.exhaustion_cooldown_seconds
                else:
                    if not self.input_state.sprint:
                        player.stamina = min(player.max_stamina, player.stamina + self.stamina_regen_rate * dt)
                    if wants_sprint and player.stamina <= 0 and player.exhaustion_cooldown <= 0:
                        player.exhaustion_cooldown = self.exhaustion_cooldown_seconds
            else:
                player.velocity = pygame.Vector2(0, 0)
                player.stamina = min(player.max_stamina, player.stamina + self.stamina_regen_rate * dt)
                player.exhaustion_cooldown = max(0.0, player.exhaustion_cooldown - dt)

            player.position += player.velocity * dt
            player.position.x = max(self.pitch.left + 4, min(self.pitch.right - 4, player.position.x))
            player.position.y = max(self.pitch.top + 4, min(self.pitch.bottom - 4, player.position.y))

            if (
                self.ball_pickup_lockout <= 0
                and self.ball.possessor_id is None
                and player.position.distance_to(self.ball.position) < player.radius + self.ball.radius + 2
            ):
                self.ball.possessor_id = player.player_id

    def _update_ball(self, dt: float) -> None:
        possessor = next((player for player in self.players if player.player_id == self.ball.possessor_id), None)
        if possessor is not None:
            direction = possessor.velocity
            if direction.length_squared() > 0:
                direction = direction.normalize()
            self.ball.position = possessor.position + direction * (possessor.radius + self.ball.radius + 2)
            self.ball.velocity = pygame.Vector2(0, 0)
        else:
            self.ball.position += self.ball.velocity * dt
            self.ball.velocity *= self.ball_friction

            if self.ball.position.x < self.pitch.left:
                self.ball.position.x = self.pitch.left
                self.ball.velocity.x *= -0.4
            elif self.ball.position.x > self.pitch.right:
                self.ball.position.x = self.pitch.right
                self.ball.velocity.x *= -0.4

            if self.ball.position.y < self.pitch.top:
                self.ball.position.y = self.pitch.top
                self.ball.velocity.y *= -0.4
            elif self.ball.position.y > self.pitch.bottom:
                self.ball.position.y = self.pitch.bottom
                self.ball.velocity.y *= -0.4

        self._check_goal()
        self._recompute_possession()

    def _check_goal(self) -> None:
        ball_rect = pygame.Rect(
            int(self.ball.position.x - self.ball.radius),
            int(self.ball.position.y - self.ball.radius),
            self.ball.radius * 2,
            self.ball.radius * 2,
        )

        team0_goal_is_right = self.team0_attacks_right

        if ball_rect.colliderect(self.left_goal):
            if team0_goal_is_right:
                self.teams[1].score += 1
            else:
                self.teams[0].score += 1
            self._reset_after_goal()
        elif ball_rect.colliderect(self.right_goal):
            if team0_goal_is_right:
                self.teams[0].score += 1
            else:
                self.teams[1].score += 1
            self._reset_after_goal()

    def _switch_sides_at_halftime(self) -> None:
        self.team0_attacks_right = not self.team0_attacks_right
        self.halftime_done = True

        for player in self.players:
            mirrored_home_x = self.pitch.left + self.pitch.right - player.home_position.x
            player.home_position = pygame.Vector2(mirrored_home_x, player.home_position.y)
            player.position = player.home_position.copy()
            player.velocity = pygame.Vector2(0, 0)

        self.ball.position = pygame.Vector2(self.pitch.centerx, self.pitch.centery)
        self.ball.velocity = pygame.Vector2(0, 0)
        self.ball.possessor_id = None
        self.ball_pickup_lockout = 0.0
        self._recompute_possession()

    def _reset_after_goal(self) -> None:
        for player in self.players:
            player.position = player.home_position.copy()
            player.velocity = pygame.Vector2(0, 0)
            player.has_ball = False
            player.stamina = player.max_stamina
            player.exhaustion_cooldown = 0.0
        self.ball.position = pygame.Vector2(self.pitch.centerx, self.pitch.centery)
        self.ball.velocity = pygame.Vector2(0, 0)
        self.ball.possessor_id = None
        self.ball_pickup_lockout = 0.0

    def _draw(self) -> None:
        self.screen.fill((18, 95, 40))
        pygame.draw.rect(self.screen, (230, 230, 230), self.pitch, 3)
        pygame.draw.line(self.screen, (230, 230, 230), (self.pitch.centerx, self.pitch.top), (self.pitch.centerx, self.pitch.bottom), 2)
        pygame.draw.circle(self.screen, (230, 230, 230), (self.pitch.centerx, self.pitch.centery), 70, 2)

        pygame.draw.rect(self.screen, (230, 230, 230), self.left_goal, 2)
        pygame.draw.rect(self.screen, (230, 230, 230), self.right_goal, 2)

        role_font = pygame.font.SysFont("consolas", 12)
        active_player = self._active_player()
        for player in self.players:
            color = (90, 160, 255) if player.team_id == 0 else (255, 110, 110)
            if player.role == "GK":
                color = (145, 200, 255) if player.team_id == 0 else (255, 185, 145)

            pygame.draw.circle(self.screen, color, (int(player.position.x), int(player.position.y)), player.radius)

            bar_width = 18
            bar_height = 4
            bar_left = int(player.position.x - (bar_width / 2))
            bar_top = int(player.position.y - player.radius - 10)
            ratio = 0.0 if player.max_stamina <= 0 else max(0.0, min(1.0, player.stamina / player.max_stamina))

            pygame.draw.rect(self.screen, (30, 30, 30), (bar_left, bar_top, bar_width, bar_height))
            if ratio > 0.65:
                bar_color = (70, 220, 80)
            elif ratio > 0.3:
                bar_color = (235, 210, 70)
            else:
                bar_color = (235, 90, 80)
            pygame.draw.rect(self.screen, bar_color, (bar_left, bar_top, int(bar_width * ratio), bar_height))

            if active_player is not None and player.player_id == active_player.player_id:
                pygame.draw.circle(self.screen, (255, 235, 0), (int(player.position.x), int(player.position.y)), player.radius + 3, 2)

            role_surface = role_font.render(player.role, True, (245, 245, 245))
            role_rect = role_surface.get_rect(center=(int(player.position.x), int(player.position.y + player.radius + 10)))
            self.screen.blit(role_surface, role_rect)

        pygame.draw.circle(self.screen, (240, 240, 240), (int(self.ball.position.x), int(self.ball.position.y)), self.ball.radius)

        font = pygame.font.SysFont("consolas", 22)
        mode = "ATTACK" if self._is_attack_mode() else "DEFENSE"
        half_label = "2nd Half" if self.halftime_done else "1st Half"
        score_text = f"Blue {self.teams[0].score} - {self.teams[1].score} Red"
        time_text = f"Time: {max(0, int(self.time_remaining))}"
        mode_text = f"Mode: {mode} | {half_label}"
        help_text = "Arrows move, E sprint, S short pass, A long pass, W tackle, D shot"

        self.screen.blit(font.render(score_text, True, (255, 255, 255)), (65, 18))
        self.screen.blit(font.render(time_text, True, (255, 255, 255)), (530, 18))
        self.screen.blit(font.render(mode_text, True, (255, 255, 255)), (910, 18))

        small_font = pygame.font.SysFont("consolas", 16)
        self.screen.blit(small_font.render(help_text, True, (240, 240, 240)), (66, self.screen_height - 30))

        pygame.display.flip()

    def reset(self) -> None:
        self.time_remaining = float(self.match_duration)
        for team in self.teams:
            team.score = 0
        self._spawn_match()

    def step(self) -> Dict:
        dt = 1.0 / self.tick_rate
        self._update_players(dt)
        self._update_ball(dt)
        self.time_remaining -= dt

        observation = {
            "ball": {
                "x": self.ball.position.x,
                "y": self.ball.position.y,
                "vx": self.ball.velocity.x,
                "vy": self.ball.velocity.y,
                "possessor_id": self.ball.possessor_id,
            },
            "players": [
                {
                    "id": player.player_id,
                    "team": player.team_id,
                    "role": player.role,
                    "x": player.position.x,
                    "y": player.position.y,
                    "vx": player.velocity.x,
                    "vy": player.velocity.y,
                    "stamina": player.stamina,
                    "max_stamina": player.max_stamina,
                }
                for player in self.players
            ],
            "score": [self.teams[0].score, self.teams[1].score],
            "time_remaining": self.time_remaining,
        }
        return observation

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.tick_rate) / 1000.0
            self._handle_events()
            self._update_players(dt)
            self._update_ball(dt)

            self.time_remaining -= dt
            if not self.halftime_done and self.time_remaining <= self.first_half_duration:
                self._switch_sides_at_halftime()
            if self.time_remaining <= 0:
                self.running = False

            self._draw()

        pygame.quit()
