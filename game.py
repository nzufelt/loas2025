"""
Here is a game, generated mostly by AI, that has a long prompt. 
The prompt is available in `game_prompt.md`.

Author: Primarily ChatGPT, with a little help from Nick Zufelt
Course: LoaS 2025, Purpose in the Age of AI
Date: 2025-08-07
"""

# Put my vibe-coded code here.

# pygame==2.x
import math
import random
import sys
import pygame

# ---------- Config ----------
WIDTH = HEIGHT = 500
FPS = 120

PLAYER_RADIUS = 15
PLAYER_SPEED = 220.0  # px/s

ENEMY_SIZE = 20
ENEMY_SPEED = 130.0  # slightly slower than player

OBSTACLE_SHORT, OBSTACLE_LONG = 50, 100
OBSTACLE_COUNT = 5
OBSTACLE_PERIOD = 6.0  # seconds between fresh random obstacle sets

FREEZE_TIME = 1.0      # player freeze duration when touching a rectangle
KNOCKBACK = 40.0       # how far player is repositioned away from rectangle after freeze
GAME_OVER_PAUSE = 1.8  # seconds the score is shown before auto-reset

BG = (14, 17, 22)
FG = (230, 235, 240)
GREEN = (60, 200, 80)
RED = (220, 60, 60)
BLUE = (65, 120, 245)
YELLOW = (240, 200, 40)

Vec2 = pygame.math.Vector2

# ---------- Utility ----------
def clamp(val, lo, hi):
    return lo if val < lo else hi if val > hi else val

def circle_rect_collision(center: Vec2, radius: float, rect: pygame.Rect) -> bool:
    nx = clamp(center.x, rect.left, rect.right)
    ny = clamp(center.y, rect.top, rect.bottom)
    dx = center.x - nx
    dy = center.y - ny
    return dx*dx + dy*dy <= radius*radius

def circle_rect_separation_vector(center: Vec2, rect: pygame.Rect) -> Vec2:
    # Vector from rect center to circle center (for direction away)
    return center - Vec2(rect.centerx, rect.centery)

def player_avoid_rect(player):
    # A small buffer around the player so new obstacles don't pop on top
    buffer = PLAYER_RADIUS * 2 + 16
    return pygame.Rect(int(player.pos.x - buffer/2), int(player.pos.y - buffer/2),
                       int(buffer), int(buffer))

def rect_corners(rect: pygame.Rect):
    return [
        Vec2(rect.left,  rect.top),
        Vec2(rect.right, rect.top),
        Vec2(rect.right, rect.bottom),
        Vec2(rect.left,  rect.bottom),
    ]

def rects_overlap_any(r: pygame.Rect, rects) -> bool:
    return any(r.colliderect(o) for o in rects)

def screen_corners_inset(inset: float):
    # Four screen corners, pulled inward by `inset` so the enemy is inside bounds.
    return [
        Vec2(inset, inset),                               # top-left
        Vec2(WIDTH - inset, inset),                       # top-right
        Vec2(WIDTH - inset, HEIGHT - inset),              # bottom-right
        Vec2(inset, HEIGHT - inset),                      # bottom-left
    ]

def within_world_rect(r: pygame.Rect) -> bool:
    return (0 <= r.left and 0 <= r.top and r.right <= WIDTH and r.bottom <= HEIGHT)

# ---------- Entities ----------
class Player:
    def __init__(self, pos: Vec2):
        self.pos = Vec2(pos)
        self.frozen_until = 0.0
        self._pending_knock_dir = None  # Vec2 or None

    def update(self, now, dt, target):
        if now < self.frozen_until:
            return
        # Move toward mouse target with capped speed; stop if very close
        to = Vec2(target) - self.pos
        dist = to.length()
        if dist > 0.001:
            step = min(PLAYER_SPEED * dt, dist)
            self.pos += to.normalize() * step

    def draw(self, surf):
        color = YELLOW if pygame.time.get_ticks()/1000.0 < self.frozen_until else GREEN
        pygame.draw.circle(surf, color, (int(self.pos.x), int(self.pos.y)), PLAYER_RADIUS)

    def collide_obstacles(self, now, obstacles):
        if now < self.frozen_until:
            return
        for ob in obstacles:
            if circle_rect_collision(self.pos, PLAYER_RADIUS, ob):
                # Apply freeze; when thawing, shove away from rectangle by KNOCKBACK
                self.frozen_until = now + FREEZE_TIME
                away = circle_rect_separation_vector(self.pos, ob)
                if away.length_squared() == 0:
                    # Degenerate: pick a random direction
                    ang = random.uniform(0, 2*math.pi)
                    away = Vec2(math.cos(ang), math.sin(ang))
                self._pending_knock_dir = away.normalize()
                self._pending_knock_rect = ob
                return

    def post_freeze_adjust(self, now):
        if self._pending_knock_dir and now >= self.frozen_until:
            # Reappear slightly away from the rectangle along stored direction
            self.pos += self._pending_knock_dir * KNOCKBACK
            # Keep inside bounds
            self.pos.x = clamp(self.pos.x, PLAYER_RADIUS, WIDTH - PLAYER_RADIUS)
            self.pos.y = clamp(self.pos.y, PLAYER_RADIUS, HEIGHT - PLAYER_RADIUS)
            self._pending_knock_dir = None

    def hits_edge(self) -> bool:
        return (self.pos.x - PLAYER_RADIUS <= 0 or
                self.pos.x + PLAYER_RADIUS >= WIDTH or
                self.pos.y - PLAYER_RADIUS <= 0 or
                self.pos.y + PLAYER_RADIUS >= HEIGHT)

    def rect_collision(self, enemy_rect: pygame.Rect) -> bool:
        return circle_rect_collision(self.pos, PLAYER_RADIUS, enemy_rect)


class Enemy:
    def __init__(self, pos: Vec2):
        self.pos = Vec2(pos)

    @property
    def rect(self) -> pygame.Rect:
        half = ENEMY_SIZE // 2
        return pygame.Rect(int(self.pos.x - half), int(self.pos.y - half), ENEMY_SIZE, ENEMY_SIZE)

    def update(self, dt, target: Vec2):
        to = Vec2(target) - self.pos
        if to.length_squared() > 0:
            self.pos += to.normalize() * (ENEMY_SPEED * dt)
        # keep within world bounds
        half = ENEMY_SIZE / 2
        self.pos.x = clamp(self.pos.x, half, WIDTH - half)
        self.pos.y = clamp(self.pos.y, half, HEIGHT - half)

    def draw(self, surf):
        pygame.draw.rect(surf, RED, self.rect)

    def bounce_on_obstacles(self, obstacles, player_pos: Vec2):
        r = self.rect
        if not any(r.colliderect(ob) for ob in obstacles):
            return

        # Teleport to the SCREEN corner nearest to the player
        half = ENEMY_SIZE / 2
        corners = screen_corners_inset(half + 1)  # +1 to avoid edge kissing
        target_corner = min(corners, key=lambda c: (c - player_pos).length_squared())

        self.pos = Vec2(target_corner.x, target_corner.y)
        # Clamp for safety
        self.pos.x = clamp(self.pos.x, half, WIDTH - half)
        self.pos.y = clamp(self.pos.y, half, HEIGHT - half)

# ---------- Obstacles ----------
def spawn_obstacles(avoid_rects=()):
    rects = []
    tries = 0
    while len(rects) < OBSTACLE_COUNT and tries < 800:
        tries += 1
        w, h = (OBSTACLE_SHORT, OBSTACLE_LONG) if random.random() < 0.5 else (OBSTACLE_LONG, OBSTACLE_SHORT)
        x = random.randint(0, WIDTH - w)
        y = random.randint(0, HEIGHT - h)
        r = pygame.Rect(x, y, w, h)
        if not within_world_rect(r):
            continue
        if rects_overlap_any(r, rects):
            continue
        if any(r.colliderect(a) for a in avoid_rects):
            continue
        rects.append(r)
    return rects

# ---------- Game ----------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Mouse Chase")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)

    def reset():
        player = Player(Vec2(WIDTH/2, HEIGHT/2))
        # start enemy in a random corner-ish spot not overlapping player
        epos = Vec2(random.choice([50, WIDTH-50]), random.choice([50, HEIGHT-50]))
        enemy = Enemy(epos)
        # Avoid spawning obstacles right on top of enemy
        obstacles = spawn_obstacles(avoid_rects=(enemy.rect, player_avoid_rect(player)))
        start_time = pygame.time.get_ticks() / 1000.0
        last_obstacle_refresh = start_time
        score_at_last_tick = 0
        return player, enemy, obstacles, start_time, last_obstacle_refresh, score_at_last_tick

    player, enemy, obstacles, start_time, last_refresh, score_prev = reset()
    game_over_until = 0.0
    score = 0

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / 1000.0
        now = pygame.time.get_ticks() / 1000.0

        # Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

        if now >= game_over_until:
            # --- Active gameplay ---
            mouse = pygame.mouse.get_pos()

            player.update(now, dt, mouse)
            player.collide_obstacles(now, obstacles)

            enemy.update(dt, player.pos)
            enemy.bounce_on_obstacles(obstacles, player.pos)

            player.post_freeze_adjust(now)

            # Scoring: +1 per 3 seconds survived
            elapsed = now - start_time
            score = int(elapsed // 3)

            # Periodic obstacle refresh
            if now - last_refresh >= OBSTACLE_PERIOD:
                obstacles = spawn_obstacles(avoid_rects=(enemy.rect, player_avoid_rect(player)))
                last_refresh = now

            # Loss conditions: player hits edge or enemy touches player
            if player.hits_edge() or player.rect_collision(enemy.rect):
                score_prev = score
                game_over_until = now + GAME_OVER_PAUSE
        else:
            # --- Game over screen then auto-reset ---
            if now >= game_over_until:
                player, enemy, obstacles, start_time, last_refresh, score_prev = reset()
                score = 0

        # --- Drawing ---
        screen.fill(BG)

        # Subtle border
        pygame.draw.rect(screen, (35, 40, 48), pygame.Rect(0, 0, WIDTH, HEIGHT), 3)

        # Obstacles
        for r in obstacles:
            pygame.draw.rect(screen, BLUE, r)

        # Enemy & Player
        enemy.draw(screen)
        player.draw(screen)

        # HUD
        txt = font.render(f"Score: {score}", True, FG)
        screen.blit(txt, (10, 8))

        # Game over overlay
        if now < game_over_until:
            surf = font.render(f"You lost! Final score: {score_prev}", True, FG)
            rect = surf.get_rect(center=(WIDTH/2, HEIGHT/2))
            screen.blit(surf, rect)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
