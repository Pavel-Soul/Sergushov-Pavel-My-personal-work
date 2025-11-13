import pygame as pg


pg.init()


class Game:
    def __init__(self, background, winsize=[800, 600], FPS=60):
        # Настраиваем окно игры
        self.FPS = FPS
        self.window = pg.display.set_mode(winsize)
        pg.display.set_caption("Игра v1.0")
        self.clock = pg.time.Clock()

        # Задаем изначальные значения фона
        self.config = {
            "background_speed": 0,
            "background_shift": 0,
        }
        background_image = pg.image.load(background)
        self.background_image = pg.transform.scale(background_image, winsize)

    def mainloop(self):
        while True:
            # Проходим по всем событиям
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return

                # При нажатии стрелок начинаем двигать фон
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_LEFT:
                        self.config["background_speed"] = 5
                    elif event.key == pg.K_RIGHT:
                        self.config["background_speed"] = -5
                # При отпускании кнопки останавливаем фон
                elif event.type == pg.KEYUP:
                    self.config["background_speed"] = 0

            # Обновляем экран, делаем задержку, переходим к слудующей итерации
            self.update()
            self.clock.tick(self.FPS)

    def update(self):
        # Определяем новый сдвиг фона
        self.config["background_shift"] = (
            self.config["background_shift"] + self.config["background_speed"]
        ) % self.window.get_width()
        # Рисуем фон со сдвигом
        self.window.blit(self.background_image, (self.config["background_shift"], 0))
        # Заполняем пустую часть фона
        self.window.blit(
            self.background_image,
            (self.config["background_shift"] - self.window.get_width(), 0),
        )
        # Обновляем экран
        pg.display.update()

    def run(self):
        self.mainloop()


def main():
    game = Game("./background.png")
    game.run()


if __name__ == "__main__":
    main()
