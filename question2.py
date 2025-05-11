import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Animal Hero vs Human Enemies")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

font = pygame.font.SysFont("Arial", 24)
large_font = pygame.font.SysFont("Arial", 48)
# Load assets here (placeholder)
animal_img = pygame.image.load('game_assets/monkey_hero.png')
bullet_img= pygame.image.load('game_assets/bullet.png')
dog_img = pygame.image.load('game_assets/dog_enemy.png')
heart_img = pygame.image.load('game_assets/heart.png')
sahur_img = pygame.image.load('game_assets/sahur.png')
background_img = pygame.image.load('game_assets/background_resize.jpg')
tralala_img = pygame.image.load('game_assets/tralalelo.png')
bombardilo_img = pygame.image.load('game_assets/bomb.png')

# enemy_img = pygame.image.load('enem.png')

# Player class
class Player(pygame.sprite.Sprite):
    def __init__(self, score):
        super().__init__()
        self.original = animal_img
        self.original = pygame.transform.scale(self.original, (50, 50))
        self.image = self.original
        self.facing_right = True
        self.rect = self.image.get_rect()
        self.rect.x = 100
        self.rect.y = HEIGHT - 100
        self.vel_y = 0
        self.jump_power = -15
        self.gravity = 1
        self.speed = 5
        self.rect.center = (WIDTH // 2, HEIGHT // 2)
        self.health = 100
        self.lives = 3
        self.projectiles = pygame.sprite.Group()
        self.max_health = 100
        self.score = score

    def update(self, keys):
        if keys:
            if keys[pygame.K_LEFT]:
                self.rect.x -= 5
                if self.facing_right:
                    self.facing_right = False
                    self.image = pygame.transform.flip(self.original, True, False)
            elif keys[pygame.K_RIGHT]:
                self.rect.x += 5
                if not self.facing_right:
                    self.facing_right = True
                    self.image = self.original
        if keys[pygame.K_UP] and self.rect.bottom >= HEIGHT:
            self.vel_y = self.jump_power

        self.vel_y += self.gravity
        self.rect.y += self.vel_y

        if self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0

        self.projectiles.update()

    def shoot(self):
        proj = Projectile(self.rect.right, self.rect.centery, self.facing_right)
        self.projectiles.add(proj)
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0

    def collect_health(self, amount):
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
    def increase_score(self, amount):
        self.score += amount
        if self.score < 0:
            self.score = 0

    def draw_health_bar(self, surface):
        # Fixed position at the top-left corner
        health_bar_x = 40
        health_bar_y = 40
        
        # Draw health text
        health_text = font.render(f"Health: {self.health}", True, BLACK)
        surface.blit(health_text, (health_bar_x, health_bar_y - 30))  # Position text above the health bar
        
        # Health bar background (red)
        pygame.draw.rect(surface, RED, (health_bar_x, health_bar_y, self.max_health, 10))
      
        # Health bar fill (green)
        pygame.draw.rect(surface, GREEN, (health_bar_x, health_bar_y, self.health, 10))
    
    def draw_score(self, surface):
        # Fixed position at the top-left corner
        score_x = 40
        score_y = 70
        
        # Draw score text
        score_text = font.render(f"Score: {self.score}", True, BLACK)
        surface.blit(score_text, (score_x, score_y))

# Projectile class
class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, facing_right):
        super().__init__()
        self.image = bullet_img
        self.image = pygame.transform.scale(self.image, (20, 25))
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = 1 if facing_right else -1  # 1 for right, -1 for left
        self.speed = 10
        self.damage = 10

    def update(self):
        
        self.rect.x += self.speed * self.direction
        # Check if the projectile is off-screen
        # Adjust the check to account for the camera offset
        camera_x = self.rect.centerx - WIDTH // 2
        if self.rect.x < camera_x or self.rect.x > camera_x + WIDTH:
            self.kill()

# Enemy class
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, health=50):
        super().__init__()
        self.image = pygame.Surface((40, 60))
        self.image.fill((0, 0, 255))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.health = 50
        self.speed = 2
        

    def update(self, player):
        # Simple behavior: Move towards the player
        if self.rect.x < player.rect.x:
            self.rect.x += 2  # Move right
        elif self.rect.x > player.rect.x:
            self.rect.x -= 2  # Move left

        # If the enemy collides with the player, damage the player
        if self.rect.colliderect(player.rect):
            player.take_damage(1)  # Enemy attacks the player with damage 1
            


    def take_damage(self, amount, player):
        self.health -= amount
        if self.health <= 0:
            self.kill()  # Remove the enemy if health reaches 0
            player.increase_score(10)  # Increase player's score when enemy is killed
    
    def display_health(self, surface, camera_x):
        # Display enemy health above the enemy
        health_text = font.render(f"Health: {self.health}", True, BLACK)
        surface.blit(health_text, (self.rect.x - camera_x, self.rect.y - 30))
        # Draw health bar
        # health_bar_x = self.rect.x
        # health_bar_y = self.rect.y - 10
        # pygame.draw.rect(surface, RED, (health_bar_x, health_bar_y, 50, 5))  # Background
            
        
        

class DogEnemy(Enemy):
    def __init__(self, x, y, health=50):
        super().__init__(x, y, health)
        self.image = dog_img
        self.image = pygame.transform.scale(self.image, (50, 50))
        self.speed = 3  # Dogs are faster than regular enemies

    def update(self, player):
        # Move towards the player with increased speed
        if self.rect.x < player.rect.x:
            self.rect.x += self.speed
        elif self.rect.x > player.rect.x:
            self.rect.x -= self.speed

        # If the dog collides with the player, deal more damage
        if self.rect.colliderect(player.rect):
            player.take_damage(2)  # Dog attacks the player with damage 2
class SahurEnemy(Enemy):
    def __init__(self, x, y, health=50):
        super().__init__(x, y, health)
        self.image = sahur_img
        self.image = pygame.transform.scale(self.image, (70, 70))
        self.speed = 1  # Sahur is slower than regular enemies

    # Create a new enemy
class TralalaEnemy(Enemy):
    def __init__(self, x, y, health=50):
        super().__init__(x, y, health)
        self.image = tralala_img
        self.image = pygame.transform.scale(self.image, (200, 150))
        
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = 1.5  # Tralala is slower than regular enemies

    def update(self, player):
        # Move towards the player with decreased speed
        if self.rect.x < player.rect.x:
            self.rect.x += self.speed
        elif self.rect.x > player.rect.x:
            self.rect.x -= self.speed

        # If the sahur collides with the player, deal less damage
        if self.rect.colliderect(player.rect):
            player.take_damage(0.5)  # Sahur attacks the player with damage 0.5

class BombardiloEnemy(Enemy):
    def __init__(self, x, y, health=50):
        super().__init__(x, y, health)
        self.image = bombardilo_img
        self.image = pygame.transform.scale(self.image, (300, 300))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = 2

    def update(self, player):
        # Move towards the player with increased speed
        if self.rect.x < player.rect.x:
            self.rect.x += self.speed
        elif self.rect.x > player.rect.x:
            self.rect.x -= self.speed

        # If the bombardilo collides with the player, deal more damage
        if self.rect.colliderect(player.rect):
            player.take_damage(3)  # Bombardilo attacks the player with damage 3


# Collectible class
class Collectible(pygame.sprite.Sprite):
    def __init__(self, x, y, type):
        super().__init__()
        self.image = pygame.Surface((20, 20))
        self.image.fill((255, 255, 0))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.type = type

class Heart(Collectible):
    def __init__(self, x, y, type = "health"):
        super().__init__(x, y, type)
        self.image = heart_img
        self.image = pygame.transform.scale(self.image, (30, 30))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.type = type

  # --- Level Loading Function ---
# This function will load different enemies and collectibles based on the level number  
def load_level(level, all_sprites, enemies, collectibles):
    # Clear previous level's enemies and collectibles
    enemies.empty()
    collectibles.empty()
    all_sprites.empty()

    # Load different setups for each level
    if level == 1:
        # Level 1 setup
        # enemy1 = SahurEnemy(600, HEIGHT - 75, 100)
        enemy1 = SahurEnemy(600, HEIGHT - 75, 100)
        enemy2 = DogEnemy(700, HEIGHT - 60, 100)
        enemies.add(enemy1, enemy2)
        collectibles.add(Heart(400, HEIGHT - 40, 'health'))

    elif level == 2:
        # Level 2 setup
        enemy1 = TralalaEnemy(800, HEIGHT - 140, 120)
        enemies.add(enemy1)
        collectibles.add(Heart(600, HEIGHT - 40, 'life'))

    elif level == 3:
        # Level 3 setup - Boss Level
        boss = BombardiloEnemy(1500, HEIGHT - 200, 300)
        enemies.add(boss)
        collectibles.add(Heart(800, HEIGHT - 40, 'health'))

    # Add them to all_sprites for easier group management
    all_sprites.add(enemies)
    all_sprites.add(collectibles)
# Groups


def display_game_over():
    game_over_text = large_font.render("GAME OVER", True, BLACK)
    restart_text = font.render("Press R to Restart or Q to Quit", True, BLACK)
    screen.fill(WHITE)
    screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 3))
    screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2))
    pygame.display.flip()

def display_level_complete():
    level_complete_text = large_font.render("LEVEL COMPLETE", True, BLACK)
    next_level_text = font.render("Press N for Next Level or Q to Quit", True, BLACK)
    screen.fill(WHITE)
    screen.blit(level_complete_text, (WIDTH // 2 - level_complete_text.get_width() // 2, HEIGHT // 3))
    screen.blit(next_level_text, (WIDTH // 2 - next_level_text.get_width() // 2, HEIGHT // 2))
    pygame.display.flip()

def maingame(level=1, current_score=0):
    all_sprites = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    collectibles = pygame.sprite.Group()
    player = Player(current_score)

    # all_sprites.add(player)   # We'll manually draw with camera offset
    all_sprites.add(player.projectiles)  # We'll draw projectiles manually too

    

    bg_scroll = 0
    current_level = level
    load_level(current_level, all_sprites, enemies, collectibles)

    # Game loop
    running = True
    while running:
        clock.tick(60)

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.shoot()

        keys = pygame.key.get_pressed()
        player.update(keys)

        # Camera center on player
        camera_x = player.rect.centerx - WIDTH // 2

        # Background scroll based on camera
        bg_scroll = camera_x % background_img.get_width()

        screen.blit(background_img, (-bg_scroll, 0))
        screen.blit(background_img, (-bg_scroll + background_img.get_width(), 0))

        # Collision: projectiles hit enemies
        for projectile in player.projectiles:
            hit_list = pygame.sprite.spritecollide(projectile, enemies, False)
            for hit in hit_list:
                hit.health -= 10
                projectile.kill()
                if hit.health <= 0:
                    hit.kill()
                    player.increase_score(10)

        # Collision: player collects items
        collected = pygame.sprite.spritecollide(player, collectibles, True)
        for item in collected:
            if item.type == 'health':
                player.health = min(100, player.health + 20)
            elif item.type == 'life':
                player.lives += 1

        # --- DRAW EVERYTHING with camera offset ---

        # Player
        screen.blit(player.image, (player.rect.x - camera_x, player.rect.y))

        # Player's projectiles
        for projectile in player.projectiles:
            screen.blit(projectile.image, (projectile.rect.x - camera_x, projectile.rect.y))

        # Enemies
        for enemy in enemies:
            enemy.display_health(screen, camera_x)  # Display enemy health above the enemy
            enemy.update(player)
            
            screen.blit(enemy.image, (enemy.rect.x - camera_x, enemy.rect.y))
            

        # Collectibles
        for collectible in collectibles:
            screen.blit(collectible.image, (collectible.rect.x - camera_x, collectible.rect.y))

        # Health bar (fixed on screen)
        player.draw_health_bar(screen)
        player.draw_score(screen) 
         
        # Check player health
        if player.health <= 0:
            display_game_over()
            waiting_for_input = True
            while waiting_for_input:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        waiting_for_input = False
                        running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:  # Restart the game
                            maingame()
                        if event.key == pygame.K_q:  # Quit the game
                            waiting_for_input = False
                            running = False

        if len(enemies) == 0:
            display_level_complete()
            waiting_for_input = True
            while waiting_for_input:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_n:  # Next level
                            maingame(current_level + 1, player.score)
                            waiting_for_input = False
                        if event.key == pygame.K_q:  # Quit the game
                            pygame.quit()
                            sys.exit()
                    
        pygame.display.flip()    

        

    pygame.quit()

maingame()
