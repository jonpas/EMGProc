import random
import pygame

from .models.snake import Snake
from .models.cube import Cube
from .models.menu import MenuGame

pygame.init()


class MainGame:
    def __init__(self, stream=None):
        self.width = 500
        self.height = 500
        self.rows = 20
        self.window = pygame.display.set_mode((self.width, self.height))
        self.caption = "SnaPy"
        self.color = (255, 0, 0)
        self.menu_font = pygame.font.Font("game/fonts/menu_font.ttf", 24)
        self.name_font = pygame.font.Font("game/fonts/name_font.ttf", 30)
        self.cre_by = pygame.font.Font("game/fonts/menu_font.ttf", 14)
        self.score_font = pygame.font.Font("game/fonts/menu_font.ttf", 12)

        print("Created by Wultes - https://github.com/wultes/")
        print("Modified by Jonpas for Myo armband input")
        self.stream = stream

        self.menu()

    def setup(self):
        self.player = Snake(self.color, (10, 10))
        self.snack = Cube(self.random_snack(), color=(0, 255, 0))
        self.score = 0
        self.paused = False
        self.last_gesture = "idle"

    def draw_score(self):
        textobj = self.score_font.render(f"Score: {self.score}", 1, (0, 0, 0))
        textreact = textobj.get_rect()
        textreact.topleft = (10, 10)
        self.window.blit(textobj, textreact)

    def draw_myo_frequency(self):
        freq = self.stream.frequency
        textobj = self.score_font.render(f"{freq} Hz", 1,
                                         pygame.Color("darkgreen") if freq > 180 else pygame.Color("red"))
        textreact = textobj.get_rect()
        textreact.topright = (self.width - 10, 10)
        self.window.blit(textobj, textreact)

    def draw_myo_gesture(self):
        gesture = self.last_gesture
        textobj = self.score_font.render(f"{gesture}", 1,
                                         pygame.Color("darkgreen") if gesture != "idle" else pygame.Color("grey"))
        textreact = textobj.get_rect()
        textreact.topright = (self.width - 10, 30)
        self.window.blit(textobj, textreact)

    def draw(self):
        self.window.fill((255, 255, 255))
        self.player.draw(self.window)
        self.snack.draw(self.window)
        self.draw_score()
        self.draw_myo_frequency()
        self.draw_myo_gesture()
        pygame.display.update()

    def random_snack(self):
        positions = self.player.body
        while True:
            x = random.randrange(self.rows)
            y = random.randrange(self.rows)
            if len(list(filter(lambda z: z.pos == (x, y), positions))) <= 0:
                break

        return(x, y)

    def menu(self):
        try:
            pygame.display.set_caption(self.caption)
            menu = MenuGame()

            while True:
                # Delay required to not take up all CPU time away from Myo thread
                pygame.time.delay(100)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise KeyboardInterrupt()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_q:
                            raise KeyboardInterrupt()
                        elif event.key == pygame.K_SPACE:
                            self.setup()
                            self.run()

                menu.draw(self.window)
        except KeyboardInterrupt:
            pass

        return 0

    def run(self):
        try:
            pygame.display.set_caption(self.caption)
            clock = pygame.time.Clock()

            while True:
                pygame.time.delay(50)
                clock.tick(5)

                # Keyboard input
                move = None
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        raise KeyboardInterrupt()
                    elif ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_q:
                            raise KeyboardInterrupt()
                        elif ev.key == pygame.K_p:
                            self.paused = not self.paused
                        elif not self.paused:
                            if ev.key == pygame.K_LEFT or ev.key == pygame.K_a:
                                move = "left"
                            elif ev.key == pygame.K_RIGHT or ev.key == pygame.K_d:
                                move = "right"

                if self.paused:
                    continue

                # Gesture input
                gesture = self.stream.gesture
                if gesture != self.last_gesture:
                    self.last_gesture = gesture

                    if gesture == "extension":
                        move = "right"
                    elif gesture == "flexion":
                        move = "left"

                self.player.move(move)
                if self.player.body[0].pos == self.snack.pos:
                    self.score += 1
                    self.player.add_cube()
                    self.snack = Cube(self.random_snack(), color=(0, 255, 0))

                for x in range(len(self.player.body)):
                    if self.player.body[x].pos in list(map(lambda z: z.pos, self.player.body[x + 1:])):
                        print(f"Your score: {len(self.player.body)}")
                        self.score = 0
                        self.player.reset((10, 10))
                        break

                self.draw()
        except KeyboardInterrupt:
            pass
