import pygame as pg
import numpy as np
import sys
from pygame.locals import *
import os

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TILE_SIZE = 32
GRAVITY = 0.5
JUMP_STRENGTH = -12  # Stronger jump for 3D feel
PLAYER_SPEED = 6
KOOPA_SPEED = 2
KOOPA_SHELL_SPEED = 10  # Faster for dash vibe
PARALLAX_SPEED = 0.5  # For pseudo-3D background

# --- Pygame Setup ---
pg.mixer.pre_init(44100, -16, 2, 512)
pg.init()
screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pg.display.set_caption("KOOPA ENGINE")
clock = pg.time.Clock()

# --- Sound ---
def make_beep(freq=440, ms=120, vol=0.5, sr=44100):
    samples = int(sr * ms / 1000)
    t = np.arange(samples)
    wave = (2 * (t * freq / sr % 1 < 0.5) - 1) * vol   # 50% duty square
    audio = np.int16(wave * 32767)
    audio = np.dstack((audio, audio))[0]
    return pg.sndarray.make_sound(audio)

# --- Define sounds (Koopa-themed yells) ---
SFX_COIN = make_beep(880, 80, 0.6)  # Koopa coin chomp
SFX_JUMP = make_beep(523, 100, 0.4)  # Koopa leap
SFX_KICK = make_beep(660, 50, 0.5)  # Shell smash
SFX_STOMP = make_beep(392, 100, 0.5)  # Koopa crush
SFX_POWERUP = make_beep(660, 150, 0.6)  # Shell power
SFX_DASH = make_beep(784, 200, 0.7)  # Dash yell

# --- Sprite Management ---
# Koopa-themed drawings on surfaces (no PNGs)
def draw_koopa(surface, color, shell_color, size=32, eyes=True):
    # Simple Koopa: oval shell, head, eyes
    pg.draw.ellipse(surface, shell_color, (0, size//4, size, size//2))  # Shell
    pg.draw.circle(surface, color, (size//2, size//4), size//4)  # Head
    if eyes:
        pg.draw.circle(surface, (255,255,255), (size//2 - 5, size//4 - 5), 3)  # Eye1
        pg.draw.circle(surface, (255,255,255), (size//2 + 5, size//4 - 5), 3)  # Eye2
        pg.draw.circle(surface, (0,0,0), (size//2 - 5, size//4 - 5), 1)  # Pupil1
        pg.draw.circle(surface, (0,0,0), (size//2 + 5, size//4 - 5), 1)  # Pupil2

class SpriteSheet:
    def __init__(self):
        # Player: Red Koopa
        self.player_img = pg.Surface((32, 32), pg.SRCALPHA)
        draw_koopa(self.player_img, (255, 0, 0), (200, 0, 0))
        
        # Enemy Koopa: Green Koopa
        self.koopa_img = pg.Surface((32, 32), pg.SRCALPHA)
        draw_koopa(self.koopa_img, (0, 128, 0), (0, 100, 0))
        
        # Shell: Yellow spinning shell
        self.shell_img = pg.Surface((24, 24), pg.SRCALPHA)
        draw_koopa(self.shell_img, (255, 215, 0), (200, 180, 0), 24, eyes=False)
        
        # Block: Stacked Koopa shells (brown)
        self.block_img = pg.Surface((32, 32), pg.SRCALPHA)
        draw_koopa(self.block_img, (139, 69, 19), (100, 50, 10), eyes=False)
        
        # Coin: Shiny Koopa badge
        self.coin_img = pg.Surface((20, 20), pg.SRCALPHA)
        draw_koopa(self.coin_img, (255, 215, 0), (200, 180, 0), 20, eyes=True)

sprite_sheet = SpriteSheet()

# --- Background for pseudo-3D ---
def draw_background(surface):
    # Parallax layers: far hills (Koopa shells), mid ground, foreground
    for i in range(3):  # Layers
        color = (50 + i*50, 100 + i*30, 200 - i*50)
        pg.draw.rect(surface, color, (0, SCREEN_HEIGHT//2 + i*100, SCREEN_WIDTH, SCREEN_HEIGHT//2))
    # Add Koopa hill patterns
    for x in range(0, SCREEN_WIDTH, 100):
        draw_koopa(surface, (0,100,0), (0,80,0), 50, False)  # Wait, draw on bg? Simple ellipses
        pg.draw.ellipse(surface, (0,80,0), (x - camera_x * (0.2 + i*0.1), 400 + i*50, 100, 50))

camera_x = 0  # For parallax

# --- Worlds + Levels (Expanded for 3D World vibe: multi-paths, slopes faked) ---
WORLDS = [
    [  # World 1: Basic Koopa Plains
        [
            "................................................................................",
            "................................................................................",
            "..................###..............................................K............",
            "..............................................###...............................",
            ".............................###..................C.............................",
            "................................................................................",
            "........K.......................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            "...................................###..........................................",
            "................K.................#...#........................................",
            "..................................#...#................C.......................",
            "..................................#...#.........................................",
            "...................................###..................K......................",
            "................................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            ".................###............................................................",
            "........K.......#...#..............................###..........................",
            "................#...#.............................#...#........C................",
            "................#...#.............................#...#.........................",
            ".................###..............................#...#........K................",
            "................................................................................",
            "################################################################################",
        ],
    ],
    [  # World 2: Shell Mountains
        [
            "................................................................................",
            "..............................#.................................................",
            ".............................#.#......................K.........................",
            "............................#...#....................###........................",
            "........C..................#...#...................#...#......................",
            "............................#...#...................#...#........K.............",
            ".............................#.#....................#...#......................",
            "..............................#......................###.......................",
            "................................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            "................#...............................................................",
            "...............#.#........................................C.....................",
            "..............#...#..............................K..............................",
            ".............#.....#............................................................",
            "............#.......#...........................###..............................",
            "...........#.........#.........................#...#........K..................",
            "..........#...........#........................#...#............................",
            ".........#.............#.......................#...#...........................",
            "........#...............#......................###.............................",
            "................................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            "................................................................................",
            "...............###..............................................K...............",
            "..............#...#....................................C........................",
            ".............#.....#............................................................",
            "............#.......#..........................K.................................",
            "...........#.........#..........................................................",
            "..........#...........#.........................................................",
            ".........#.............#........................................................",
            "........#...............#......................................................",
            ".......#.................#.....................................................",
            "......#...................#....................................................",
            ".....#.....................#...................................................",
            "....#.......................#..................................................",
            "...#.........................#.................................................",
            "................................................................................",
            "################################################################################",
        ],
    ],
    [  # World 3: Koopa Castle
        [
            "................................................................................",
            "................................................................................",
            "................................................................................",
            ".................K.........................................###..................",
            "..........................................................#...#........C........",
            "..........................................................#...#.................",
            "..........................................................#...#........K........",
            "...........................................................###..................",
            "................................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            "...............#................................................................",
            "..............#.#........................................K......................",
            ".............#...#.....................................###.....................",
            "............#.....#...................................#...#........C...........",
            "...........#.......#..................................#...#....................",
            "..........#.........#........................K........#...#....................",
            ".........#...........#...............................#...#.....................",
            "........#.............#..............................###.......................",
            "................................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            "................................................................................",
            "..............###...............................................K...............",
            ".............#...#.....................................C........................",
            "............#.....#.............................................................",
            "...........#.......#...................................###......................",
            "..........#.........#........................K.........#...#....................",
            ".........#...........#................................#...#....................",
            "........#.............#...............................#...#.....................",
            ".......#...............#..............................###.......................",
            "................................................................................",
            "################################################################################",
        ],
    ],
]

current_world = 0
current_level = 0

def get_level():
    if 0 <= current_world < len(WORLDS) and 0 <= current_level < len(WORLDS[current_world]):
        return WORLDS[current_world][current_level]
    return ["." * 80 for _ in range(16)]  # Taller levels for 3D feel

def load_level(world, level):
    global current_world, current_level
    current_world = max(0, min(world, len(WORLDS) - 1))
    current_level = max(0, min(level, len(WORLDS[current_world]) - 1))

# --- Tile Map Class ---
class TileMap:
    def __init__(self, data):
        self.data = data
        self.tile_size = TILE_SIZE
        self.width = len(data[0])
        self.height = len(data)
        self.tiles = []
        self.coin_positions = []  # Positions for coin sprites
        self.koopa_positions = []  # Positions for Koopa spawns

    def load_tiles(self):
        self.tiles = []
        self.coin_positions = []
        self.koopa_positions = []
        for y, row in enumerate(self.data):
            for x, tile_char in enumerate(row):
                if tile_char == '#':
                    rect = pg.Rect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)
                    self.tiles.append(rect)
                elif tile_char == 'C':
                    pos = (x * self.tile_size + self.tile_size // 2 - 10, y * self.tile_size + self.tile_size // 2 - 10)
                    self.coin_positions.append(pos)
                elif tile_char == 'K':
                    pos = (x * self.tile_size, y * self.tile_size)
                    self.koopa_positions.append(pos)

    def draw(self, surface):
        for tile_rect in self.tiles:
            surface.blit(sprite_sheet.block_img, tile_rect.topleft)  # Use Koopa block img

# --- Base Entity Class ---
class Entity(pg.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = pg.math.Vector2(0, 0)
        self.on_ground = False

    def apply_gravity(self):
        self.vel.y += GRAVITY
        if self.vel.y > 10:
            self.vel.y = 10

    def check_collisions_x(self, tiles):
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.vel.x > 0:
                    self.rect.right = tile.left
                elif self.vel.x < 0:
                    self.rect.left = tile.right
                self.vel.x = 0  # Stop on wall hit for 3D feel

    def check_collisions_y(self, tiles):
        self.on_ground = False
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.vel.y > 0:
                    self.rect.bottom = tile.top
                    self.vel.y = 0
                    self.on_ground = True
                elif self.vel.y < 0:
                    self.rect.top = tile.bottom
                    self.vel.y = 0

# --- Player Class (Red Koopa) ---
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, sprite_sheet.player_img)
        self.shell_state = False
        self.shell_timer = 0
        self.dash_speed = 0  # For 3D World dash

    def update(self, tile_map, keys):
        self.apply_gravity()

        # Movement (WASD for 3D-like freedom, but 2D)
        self.vel.x = 0
        if keys[K_LEFT] or keys[K_a]:
            self.vel.x = -PLAYER_SPEED
        if keys[K_RIGHT] or keys[K_d]:
            self.vel.x += PLAYER_SPEED

        # Jump
        if (keys[K_SPACE] or keys[K_w]) and self.on_ground:
            self.vel.y = JUMP_STRENGTH
            SFX_JUMP.play()

        # Shell mode (press X for dash like cat suit)
        if keys[K_x] and not self.shell_state:
            self.shell_state = True
            self.shell_timer = 300
            self.image = sprite_sheet.shell_img
            self.rect.height = 24  # Smaller shell
            self.rect.y += 8  # Adjust pos
            self.dash_speed = PLAYER_SPEED * 2
            SFX_POWERUP.play()

        if self.shell_state:
            self.vel.x *= 1.2  # Accelerate
            self.shell_timer -= 1
            if self.shell_timer <= 0:
                self.shell_state = False
                self.image = sprite_sheet.player_img
                self.rect.height = 32
                self.rect.y -= 8
                self.dash_speed = 0

        # Update pos
        self.rect.x += self.vel.x + self.dash_speed * (1 if self.vel.x > 0 else -1 if self.vel.x < 0 else 0)
        self.check_collisions_x(tile_map.tiles)
        self.rect.y += self.vel.y
        self.check_collisions_y(tile_map.tiles)

# --- Coin Class (Koopa Badge) ---
class Coin(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, sprite_sheet.coin_img)

    def update(self, tile_map):
        pass  # Static, but can add spin anim later

# --- Koopa Enemy Class (Green Koopa) ---
class Koopa(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, sprite_sheet.koopa_img)
        self.direction = 1
        self.shell = False
        self.shell_timer = 0

    def update(self, tile_map):
        self.apply_gravity()

        if not self.shell:
            self.vel.x = KOOPA_SPEED * self.direction
        else:
            self.vel.x = KOOPA_SHELL_SPEED * self.direction

        # Move and check
        self.rect.x += self.vel.x
        hit_wall = False
        for tile in tile_map.tiles:
            if self.rect.colliderect(tile):
                if self.vel.x > 0:
                    self.rect.right = tile.left
                else:
                    self.rect.left = tile.right
                hit_wall = True
                break
        if hit_wall:
            self.direction *= -1

        # Check for edge (3D World style patrol)
        if self.on_ground:
            edge_check = pg.Rect(self.rect.x + self.vel.x, self.rect.bottom, self.rect.width, 2)
            if not any(edge_check.colliderect(tile) for tile in tile_map.tiles):
                self.direction *= -1

        self.rect.y += self.vel.y
        self.check_collisions_y(tile_map.tiles)

        if self.shell:
            self.shell_timer -= 1
            if self.shell_timer <= 0:
                self.shell = False
                self.image = sprite_sheet.koopa_img

    def stomp(self):
        SFX_STOMP.play()
        self.shell = True
        self.shell_timer = 180
        self.image = sprite_sheet.shell_img
        self.vel.x = 0  # Stop to be kicked

    def kick(self, direction):
        SFX_KICK.play()
        self.shell = True
        self.shell_timer = 300  # Longer for chase
        self.direction = direction
        self.vel.x = KOOPA_SHELL_SPEED * self.direction
        self.vel.y = -5

# --- Game Object Manager ---
class GameManager:
    def __init__(self):
        self.player = Player(100, 100)
        self.all_sprites = pg.sprite.Group(self.player)
        self.coins = pg.sprite.Group()
        self.koopas = pg.sprite.Group()
        self.load_level(0, 0)
        self.score = 0
        self.lives = 3
        global camera_x
        camera_x = 0

    def load_level(self, world, level):
        load_level(world, level)
        self.tile_map = TileMap(get_level())
        self.tile_map.load_tiles()
        self.player.rect.topleft = (100, 100)
        self.player.vel = pg.math.Vector2(0, 0)
        self.coins.empty()
        self.koopas.empty()
        self.all_sprites = pg.sprite.Group(self.player)
        for pos in self.tile_map.coin_positions:
            coin = Coin(*pos)
            self.coins.add(coin)
            self.all_sprites.add(coin)
        for pos in self.tile_map.koopa_positions:
            koopa = Koopa(*pos)
            self.koopas.add(koopa)
            self.all_sprites.add(koopa)

    def update(self):
        keys = pg.key.get_pressed()
        self.player.update(self.tile_map, keys)

        for koopa in self.koopas:
            koopa.update(self.tile_map)

        # Camera follow for 3D depth
        global camera_x
        camera_x = self.player.rect.x - SCREEN_WIDTH // 2

        # Coin collection
        collected = pg.sprite.spritecollide(self.player, self.coins, True)
        for coin in collected:
            self.score += 50
            SFX_COIN.play()

        # Enemy interactions
        for koopa in pg.sprite.spritecollide(self.player, self.koopas, False):
            if self.player.vel.y > 0 and self.player.rect.bottom < koopa.rect.centery:  # Stomp check
                koopa.stomp()
                self.player.vel.y = JUMP_STRENGTH * 0.7
                self.score += 100
            elif self.player.shell_state:  # Kick in shell
                direction = 1 if self.player.vel.x > 0 else -1
                koopa.kick(direction)
                self.score += 200
            else:  # Hurt
                self.lives -= 1
                SFX_STOMP.play()  # Hurt sound
                if self.lives <= 0:
                    return False
                self.player.rect.topleft = (100, 100)
                self.player.vel = pg.math.Vector2(0, 0)

        # Level complete check (reach right end)
        if self.player.rect.x > self.tile_map.width * TILE_SIZE - 100:
            self.current_level += 1
            if self.current_level >= len(WORLDS[self.current_world]):
                self.current_world += 1
                self.current_level = 0
            if self.current_world >= len(WORLDS):
                print("You Win!")
                return False
            self.load_level(self.current_world, self.current_level)

        return True

    def draw(self, surface):
        draw_background(surface)
        # Draw tiles with camera offset
        for tile in self.tile_map.tiles:
            shifted = tile.copy()
            shifted.x -= camera_x
            surface.blit(sprite_sheet.block_img, shifted.topleft)
        # Draw sprites with offset
        for sprite in self.all_sprites:
            shifted_rect = sprite.rect.copy()
            shifted_rect.x -= camera_x
            surface.blit(sprite.image, shifted_rect)
        # UI
        font = pg.font.SysFont(None, 36)
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_text = font.render(f"Lives: {self.lives}", True, (255, 255, 255))
        world_text = font.render(f"World {current_world+1}-{current_level+1}", True, (255, 255, 255))
        surface.blit(score_text, (10, 10))
        surface.blit(lives_text, (10, 50))
        surface.blit(world_text, (10, 90))

# --- Main Game Loop ---
def main():
    game_manager = GameManager()
    running = True
    while running:
        for e in pg.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                running = False

        if not game_manager.update():
            running = False  # Game over or win

        game_manager.draw(screen)
        pg.display.flip()
        clock.tick(60)

    pg.quit()
    sys.exit()

if __name__ == '__main__':
    main()
