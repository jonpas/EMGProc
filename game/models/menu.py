import pygame


class MenuGame:
    def __init__(self):
        self.menu_font = pygame.font.Font("game/fonts/menu_font.ttf", 24)
        self.name_font = pygame.font.Font("game/fonts/name_font.ttf", 30)
        self.cre_by = pygame.font.Font("game/fonts/menu_font.ttf", 14)
        self.score_font = pygame.font.Font("game/fonts/menu_font.ttf", 12)

    def drawText(self, text, color, x, y, font, window):
        textobj = font.render(text, 1, color)
        textreact = textobj.get_rect()
        textreact.topleft = (x, y)
        window.blit(textobj, textreact)

    def draw(self, window):
        window.fill((255, 255, 255))
        self.drawText("SnaPy Myo", (0, 0, 0), 110, 50, self.name_font, window)
        self.drawText("Press SPACE to start", (0, 0, 0), 115, 200, self.menu_font, window)
        self.drawText("Move: WD / <-> / Myo", (0, 0, 0), 115, 250, self.menu_font, window)
        self.drawText("(P)ause / (Q)uit", (0, 0, 0), 140, 300, self.menu_font, window)
        self.drawText("Created by Wultes", (0, 0, 0), 330, 450, self.cre_by, window)
        self.drawText("Modified by Jonpas", (0, 0, 0), 330, 475, self.cre_by, window)
        pygame.display.update()
