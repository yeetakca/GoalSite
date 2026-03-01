# GoalSite2 Plan

## 1) Vision

Create a **2D football (soccer) simulation in Pygame** where players and the ball are represented as dots.

The project has two purposes:

1. Be fun/playable with keyboard control.
2. Serve as a clean base environment for future reinforcement learning (RL).

## 2) Core Requirements (MVP)

- Render a playable 2D pitch, two teams, and one ball.
- Represent all entities (players + ball) as dots.
- Assign every player a **formation role**.
- Support **config-based startup**.
- If human control is enabled in config, assign control to **one random player**.
- Team/player count must be configurable.
- Teams must **switch sides at halftime**.
- At halftime, second half restarts from reset formation locations on swapped sides.

## 3) Configuration

At game start, load settings from a config file (or equivalent runtime config object).

Minimum config fields:

- `team_size` (int)
- `human_control_enabled` (bool)
- `random_human_player` (bool, default: true)
- `formation_name` (string, e.g. `4-4-2`)
- `match_duration_seconds` (int)

Nice-to-have fields (post-MVP):

- `player_max_speed`
- `player_max_stamina`
- `sprint_stamina_drain`
- `stamina_regen_rate`
- `exhaustion_cooldown_seconds`
- `post_kick_pickup_lockout_seconds`
- `logs_enabled`
- `action_debug_logs`
- `ball_friction`
- `tick_rate`
- `seed`

## 4) Gameplay Controls

### Movement

- `Arrow Up`: move up
- `Arrow Down`: move down
- `Arrow Left`: move left
- `Arrow Right`: move right
- `E`: sprint

Stamina behavior:

- Sprinting consumes stamina.
- Stamina regenerates over time only when sprint input is not held.
- Reaching zero stamina triggers a short sprint lockout (`exhaustion_cooldown_seconds`) to prevent micro-burst sprint jitter.
- Each player has a visible stamina bar.

### Attack Mode

- `S`: short pass
- `A`: long pass
- `D`: shot

### Defense Mode

- `W`: normal tackle

## 5) Formation & Roles

Each player must have:

- Team ID
- Role (GK, DEF, MID, FWD)
- Home position from formation template

Behavior expectation:

- Without ball: players bias toward their role/home zone.
- With ball nearby: players can leave home zone with bounded aggression.

## 6) RL-Readiness Requirements

- Deterministic stepping option via fixed tick rate + random seed.
- Programmatic reset of match state.
- Structured state output (positions, velocities, possession, score, time).
- Action interface that can accept both keyboard and agent actions.
- Reward hook points (goal scored, possession gain, successful pass, etc.).

## 7) Development Phases

### Phase 1: World + Rendering

- Pitch dimensions and boundaries
- Dot rendering for players/ball
- Game loop and fixed update cadence

### Phase 2: Input + Player Control

- Keyboard movement + sprint
- Human control of one random player (if enabled)

### Phase 3: Ball + Basic Football Actions

- Pass/shot actions
- Ball movement and friction
- Possession detection

### Phase 4: Team Logic

- Formation spawn templates
- Role-based positioning and simple AI movement
- Basic attack/defense mode switching

### Phase 5: RL Interface

- Reset/step API
- Observation and reward output
- Seeded reproducibility checks

## 8) Acceptance Criteria (MVP Done When)

- Game runs from config with no hardcoded team size.
- Human control can be toggled and assigned to a random player.
- All listed keys trigger expected behavior in attack/defense contexts.
- Players keep formation identity while still reacting to play.
- Environment can reset and step for future RL integration.

## 9) Out of Scope (for MVP)

- Advanced graphics/animations
- Full real-world football rules engine
- Multiplayer networking
- Complex tactical AI
