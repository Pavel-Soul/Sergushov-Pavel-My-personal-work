import pygame as pg


pg.init()


class Player(pg.sprite.Sprite):
    def __init__(self, filename, hero_x=100, hero_y=25, width=100):
        # Запускаем родительский init
        super().__init__()
        # Загружаем изображение и конвертируем в альфа канал
        self.image = pg.image.load(filename).convert_alpha()
        # Считаем новую высоту изображения
        height = width / self.image.get_width() * self.image.get_height()
        # Изменяем размеры изображения
        self.image = pg.transform.scale(self.image, (width, height))
        # Получаем рамку изображения
        self.rect = self.image.get_rect()
        # Задаем положение спрайта
        self.rect.x = hero_x
        self.rect.y = hero_y
        self.speed = [0, 0]
        self.dir = "right"

    def flip(self, dir):
        if dir != self.dir:
            self.image = pg.transform.flip(self.image, True, False)
            self.dir = dir


class Game:
    def __init__(self, background, winsize=[800, 600], FPS=60):
        # Настраиваем окно игры
        self.FPS = FPS
        self.window = pg.display.set_mode(winsize)
        pg.display.set_caption("Игра v1.0")
        self.clock = pg.time.Clock()

        # Задаем изначальные значения фона
        self.config = {
            "background_shift": 0,
        }
        background_image = pg.image.load(background)
        self.background_image = pg.transform.scale(background_image, winsize)

        self.player = Player("tank.png", hero_y=400)

    def mainloop(self):
        while True:
            # Проходим по всем событиям
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return

                # При нажатии стрелок начинаем двигать игрока
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_LEFT:
                        self.player.speed[0] = 5
                        self.player.flip("left")
                    elif event.key == pg.K_RIGHT:
                        self.player.speed[0] = -5
                        self.player.flip("right")

                    elif event.key == pg.K_UP:
                        self.player.speed[1] = 5
                    elif event.key == pg.K_DOWN:
                        self.player.speed[1] = -5

                # При отпускании кнопки останавливаем фон
                elif event.type == pg.KEYUP:
                    self.player.speed[0] = 0
                    self.player.speed[1] = 0

            # Обновляем экран, делаем задержку, переходим к слудующей итерации
            self.update()
            self.clock.tick(self.FPS)

    def update(self):
        # Если игрок не выходит за экран, двигаеам его
        if not (
            (self.player.rect.left <= 0 + 150 and self.player.speed[0] > 0)
            or self.player.rect.right >= self.window.get_width() - 150
            and self.player.speed[0] < 0
        ):
            self.player.rect.x -= self.player.speed[0]
            # Если игрок не уперся вверх или вниз, сдвигаем по вертикали
            if (self.player.speed[1] > 0 and self.player.rect.top > 0) or (
                self.player.speed[1] < 0 and self.player.rect.bottom < 510
            ):
                self.player.rect.y -= self.player.speed[1]
        # Иначе двигаем фон
        else:
            self.config["background_shift"] = (
                self.config["background_shift"] + self.player.speed[0]
            ) % self.window.get_width()
        # Рисуем фон со сдвигом
        self.window.blit(self.background_image, (self.config["background_shift"], 0))
        # Заполняем пустую часть фона
        self.window.blit(
            self.background_image,
            (self.config["background_shift"] - self.window.get_width(), 0),
        )
        self.window.blit(self.player.image, self.player.rect)
        # Обновляем экран
        pg.display.update()

    def run(self):
        self.mainloop()


def main():
    game = Game("./background.png")
    game.run()


if __name__ == "__main__":
    main()
