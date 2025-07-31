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
JUMP_STRENGTH = -10
PLAYER_SPEED = 5
KOOPA_SPEED = 1
KOOPA_SHELL_SPEED = 8 # Speed when kicked

# --- Pygame Setup ---
pg.mixer.pre_init(44100, -16, 2, 512)
pg.init()
screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pg.display.set_caption("Koopa Engine")
clock = pg.time.Clock()

# --- Sound ---
def make_beep(freq=440, ms=120, vol=0.5, sr=44100):
    samples = int(sr * ms / 1000)
    t = np.arange(samples)
    wave = (2 * (t * freq / sr % 1 < 0.5) - 1) * vol   # 50% duty square
    audio = np.int16(wave * 32767)
    # Audio needs to be created as stereo (2 channels)
    audio = np.dstack((audio, audio))[0]
    return pg.sndarray.make_sound(audio)

# --- Define sounds ---
SFX_COIN = make_beep(880) # Coin sound
SFX_JUMP = make_beep(523, 100, 0.3) # Jump sound
SFX_KICK = make_beep(660, 50, 0.3) # Kick sound (shell)
SFX_STOMP = make_beep(392, 100, 0.4) # Stomp sound
SFX_POWERUP = make_beep(660, 100, 0.4) # Power-up sound

# --- Sprite Management ---
# Placeholder for sprites; in a real engine, these would be loaded from image files
# For now, we'll define simple colored surfaces
class SpriteSheet:
    def __init__(self):
        self.player_img = pg.Surface((32, 32), pg.SRCALPHA)
        self.player_img.fill((255, 0, 0)) # Red for player (Koopa)
        self.koopa_img = pg.Surface((32, 32), pg.SRCALPHA)
        self.koopa_img.fill((0, 128, 0)) # Green for Koopa Troopa
        self.shell_img = pg.Surface((24, 24), pg.SRCALPHA)
        self.shell_img.fill((128, 128, 0)) # Brownish for shell
        self.block_img = pg.Surface((32, 32), pg.SRCALPHA)
        self.block_img.fill((139, 69, 19)) # Brown for blocks
        self.coin_img = pg.Surface((20, 20), pg.SRCALPHA)
        self.coin_img.fill((255, 215, 0)) # Gold for coins

sprite_sheet = SpriteSheet()

# --- Worlds + Levels ---
# Define levels with tile characters (e.g., '#' for solid blocks, 'C' for coins, 'K' for Koopas)
WORLDS = [
    [  # World 1
        [
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "..................###...........................................................",
            "..............................................###...............................",
            ".............................###................................................",
            "................................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "################################################################################",
        ],
        [
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "................................................................................",
            "################################################################################",
        ],
    ],
    # Add more worlds here if needed, but ensure they have enough levels
    *[ # Placeholder worlds to prevent index errors
        [["################################################################################"]*8] for _ in range(4)
    ]
]

current_world = 0
current_level = 0

def get_level():
    """Safely gets the current level data."""
    if 0 <= current_world < len(WORLDS):
        if 0 <= current_level < len(WORLDS[current_world]):
            return WORLDS[current_world][current_level]
    # Fallback to a default empty level on error
    return [["."*80]*8]

def load_level(world, level):
    global current_world, current_level
    # Boundary checks for loading levels
    if 0 <= world < len(WORLDS):
        current_world = world
        if 0 <= level < len(WORLDS[current_world]):
            current_level = level
        else:
            current_level = 0 # Default to first level if invalid
    else:
        current_world = 0 # Default to first world if invalid
        current_level = 0

# --- Tile Map Class ---
class TileMap:
    def __init__(self, data):
        self.data = data
        self.tile_size = TILE_SIZE
        self.width = len(data[0]) # Assuming rectangular map
        self.height = len(data)
        self.tiles = [] # List of rectangles representing tiles
        self.coins = [] # List of coin positions
        self.koopas = [] # List of Koopa Troopa positions

    def load_tiles(self):
        """Create a list of rectangles for collision."""
        self.tiles = []
        self.coins = []
        self.koopas = []
        for y, row in enumerate(self.data):
            for x, tile_char in enumerate(row):
                if tile_char == '#': # Solid block
                    rect = pg.Rect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)
                    self.tiles.append(rect)
                elif tile_char == 'C': # Coin
                    coin_pos = (x * self.tile_size + self.tile_size // 2, y * self.tile_size + self.tile_size // 2)
                    self.coins.append(coin_pos)
                elif tile_char == 'K': # Koopa Troopa
                    koopa_pos = (x * self.tile_size, y * self.tile_size)
                    self.koopas.append(koopa_pos)

    def draw(self, surface):
        """Draw the tiles."""
        for tile_rect in self.tiles:
            pg.draw.rect(surface, 'brown', tile_rect)
        # Draw coins
        for coin_pos in self.coins:
            coin_rect = pg.Rect(coin_pos[0]-10, coin_pos[1]-10, 20, 20)
            pg.draw.circle(surface, 'gold', coin_pos, 10)
        # Draw koopas
        for koopa_pos in self.koopas:
            koopa_rect = pg.Rect(koopa_pos[0], koopa_pos[1], 32, 32)
            pg.draw.rect(surface, 'green', koopa_rect)

# --- Base Entity Class ---
class Entity(pg.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = pg.math.Vector2(0, 0)

    def update(self, tile_map):
        pass # Override in subclasses

# --- Player Class (Koopa) ---
class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, sprite_sheet.player_img)
        self.on_ground = False
        self.jumping = False
        self.shell_state = False # False = normal, True = shell
        self.shell_timer = 0 # Timer for shell state duration

    def update(self, tile_map):
        # Apply gravity
        self.vel.y += GRAVITY
        if self.vel.y > 5: self.vel.y = 5

        keys = pg.key.get_pressed()
        # Horizontal movement
        if keys[K_LEFT]:
            self.vel.x = -PLAYER_SPEED
        elif keys[K_RIGHT]:
            self.vel.x = PLAYER_SPEED
        else:
            self.vel.x = 0

        # Jumping
        if keys[K_SPACE] and self.on_ground:
            self.vel.y = JUMP_STRENGTH
            self.on_ground = False
            self.jumping = True
            SFX_JUMP.play() # Play jump sound

        # Shell mode toggle (e.g., press 'X' or similar)
        # Note: This is a placeholder logic. In a real game, you'd want a proper input handler.
        # if keys[K_x]: # Example key for shell mode
        #     if not self.shell_state:
        #         self.shell_state = True
        #         self.shell_timer = 300 # Duration in frames
        #         # Change appearance to shell
        #         self.image = sprite_sheet.shell_img # Replace with actual shell image
        #         # Adjust size/position if needed

        # Update position
        self.rect.x += self.vel.x
        self.check_collisions(tile_map, 'horizontal')
        self.rect.y += self.vel.y
        self.check_collisions(tile_map, 'vertical')

        # Update shell timer
        if self.shell_state:
            self.shell_timer -= 1
            if self.shell_timer <= 0:
                self.shell_state = False
                # Restore normal appearance
                self.image = sprite_sheet.player_img # Replace with actual normal image
                # Adjust size/position if needed

    def check_collisions(self, tile_map, direction):
        # Get list of potential collisions
        collidable_tiles = tile_map.tiles
        for tile_rect in collidable_tiles:
            if self.rect.colliderect(tile_rect):
                if direction == 'horizontal':
                    # Horizontal collision
                    if self.vel.x > 0: # Moving right
                        self.rect.right = tile_rect.left
                    elif self.vel.x < 0: # Moving left
                        self.rect.left = tile_rect.right
                elif direction == 'vertical':
                    # Vertical collision
                    if self.vel.y > 0: # Falling down
                        self.rect.bottom = tile_rect.top
                        self.vel.y = 0
                        self.on_ground = True
                        self.jumping = False
                    elif self.vel.y < 0: # Jumping up
                        self.rect.top = tile_rect.bottom
                        self.vel.y = 0

# --- Koopa Troopa Class ---
class Koopa(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, sprite_sheet.koopa_img)
        self.direction = 1 # 1 for right, -1 for left
        self.walk_speed = KOOPA_SPEED
        self.shell = False # True if in shell mode
        self.shell_timer = 0 # Timer for shell state duration

    def update(self, tile_map):
        # Basic AI: Move back and forth
        self.vel.x = self.walk_speed * self.direction

        # Check if at edge or hitting a wall
        # Simple check: move one step forward and see if it's valid
        old_x = self.rect.x
        self.rect.x += self.vel.x
        # Check collisions with tiles
        collidable_tiles = tile_map.tiles
        collision = False
        for tile_rect in collidable_tiles:
            if self.rect.colliderect(tile_rect):
                # If collides with a tile, reverse direction
                if self.direction == 1:
                    self.rect.right = tile_rect.left
                else:
                    self.rect.left = tile_rect.right
                self.direction *= -1 # Reverse direction
                collision = True
                break

        # If no collision, restore previous position
        if not collision:
            self.rect.x = old_x

        # Apply gravity
        self.vel.y += GRAVITY
        if self.vel.y > 5: self.vel.y = 5

        # Fall down if not on ground
        self.rect.y += self.vel.y
        self.check_collisions(tile_map)

        # Update shell timer
        if self.shell:
            self.shell_timer -= 1
            if self.shell_timer <= 0:
                self.shell = False
                # Restore normal appearance
                self.image = sprite_sheet.koopa_img # Replace with actual normal image

    def check_collisions(self, tile_map):
        collidable_tiles = tile_map.tiles
        for tile_rect in collidable_tiles:
            if self.rect.colliderect(tile_rect):
                if self.vel.y > 0: # Falling down
                    self.rect.bottom = tile_rect.top
                    self.vel.y = 0

    def kick(self):
        # Called when player kicks the Koopa
        SFX_KICK.play()
        self.shell = True
        self.shell_timer = 180 # Duration in frames
        # Change direction based on kick direction (simplified)
        self.direction = 1 if self.vel.x < 0 else -1
        self.vel.x = self.direction * KOOPA_SHELL_SPEED
        self.vel.y = -5 # Small upward kick
        # Change image to shell
        self.image = sprite_sheet.shell_img # Replace with actual shell image

# --- Game Object Manager ---
class GameManager:
    def __init__(self):
        self.player = Player(200, 64)
        self.all_sprites = pg.sprite.Group(self.player)
        self.koopas = pg.sprite.Group()
        self.enemies = pg.sprite.Group()
        self.current_level_data = get_level()
        self.tile_map = TileMap(self.current_level_data)
        self.tile_map.load_tiles()
        self.score = 0
        self.lives = 3

    def load_level(self, world, level):
        load_level(world, level)
        self.current_level_data = get_level()
        self.tile_map = TileMap(self.current_level_data)
        self.tile_map.load_tiles()
        self.player.rect.topleft = (200, 64) # Reset player position
        self.player.vel.y = 0 # Reset vertical velocity
        self.koopas.empty() # Clear existing enemies
        self.enemies.empty()
        # Spawn Koopas from the tile map
        for koopa_pos in self.tile_map.koopas:
            koopa = Koopa(koopa_pos[0], koopa_pos[1])
            self.koopas.add(koopa)
            self.enemies.add(koopa)
            self.all_sprites.add(koopa)

    def update(self):
        self.all_sprites.update(self.tile_map)
        self.koopas.update(self.tile_map)

        # Handle collisions between player and enemies
        # Check if player is jumping on an enemy
        player_feet = pg.Rect(self.player.rect.x, self.player.rect.bottom - 5, self.player.rect.width, 10)
        for enemy in self.enemies:
            if isinstance(enemy, Koopa) and enemy.rect.colliderect(player_feet) and self.player.vel.y > 0:
                # Stomp effect
                SFX_STOMP.play()
                enemy.kill() # Remove enemy
                self.player.vel.y = JUMP_STRENGTH * 0.8 # Bounce
                self.score += 100 # Increase score
                # Add the enemy to a temporary group to handle removal after bounce
                # This is a simplified way to handle stomp effect
                self.enemies.remove(enemy)
                continue # Skip to next enemy to avoid double processing

            # Check if player touches an enemy
            if isinstance(enemy, Koopa) and self.player.rect.colliderect(enemy.rect):
                # If player is in shell state, kick the enemy
                if self.player.shell_state:
                    enemy.kick()
                    self.score += 50 # Bonus for kicking
                else:
                    # Player loses a life or dies
                    self.lives -= 1
                    if self.lives <= 0:
                        print("Game Over!")
                        return False # Signal to end game
                    else:
                        # Reset player position
                        self.player.rect.topleft = (200, 64)
                        self.player.vel.y = 0
        return True # Continue game

    def draw(self, surface):
        surface.fill('black') # Clear screen
        self.tile_map.draw(surface) # Draw tiles, coins, and koopas
        self.all_sprites.draw(surface) # Draw player and other sprites
        # Draw UI elements (score, lives)
        font = pg.font.SysFont(None, 36)
        score_text = font.render(f"Score: {self.score}", True, (255, 255, 255))
        lives_text = font.render(f"Lives: {self.lives}", True, (255, 255, 255))
        surface.blit(score_text, (10, 10))
        surface.blit(lives_text, (10, 50))

# --- Main Game Loop ---
def main():
    game_manager = GameManager()
    running = True
    while running:
        # Event Handling
        for e in pg.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                running = False
            if e.type == KEYDOWN:
                # World select (number keys 1-5)
                if K_1 <= e.key <= K_5:
                    game_manager.load_level(e.key - K_1, 0)
                # Level select (number keys 7-9, for levels 1-3)
                if e.key in [K_7, K_8, K_9]:
                    game_manager.load_level(game_manager.current_world, e.key - K_7)

        # Update
        if not game_manager.update():
            running = False # End game if player loses all lives

        # Draw everything
        game_manager.draw(screen)

        pg.display.flip()
        clock.tick(60)

    pg.quit()
    sys.exit()

if __name__ == '__main__':
    main()
