import pygame as pg
from math import pi, tan
from icecream import ic

pg.init()


class Enemy(pg.sprite.Sprite):
    def __init__(
        self, window, filename, hero_x=100, hero_y=25, width=100, speed=[0, 0]
    ):
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
        self.speed = speed
        if self.speed[0] < 0:
            self.image = pg.transform.flip(self.image, True, False)
        self.window = window

    def update(self):
        self.rect.x += self.speed[0]
        # self.rect.y += self.speed[1]
        if self.rect.left > self.window.get_width():
            self.rect.right = 0
        if self.rect.right < 0:
            self.rect.right = self.window.get_width()
        self.window.blit(self.image, self.rect)


class Bullet(pg.sprite.Sprite):
    """
    Объект снаряда
    """

    def __init__(self, window, image, pos, speed, width=10, angle=0):
        super().__init__()
        # Загружаем настройки, изображение, задаем параметры
        self.pos = pos
        self.speed = speed
        self.image = pg.image.load(image).convert_alpha()
        height = width / self.image.get_width() * self.image.get_height()
        self.image = pg.transform.scale(self.image, (width, height))
        self.image = pg.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect()
        self.rect.x = pos[0] + width / 2
        self.rect.y = pos[1] + height / 2
        self.window = window

    def update(self):
        # Перемещаем снаряд
        self.rect.x += self.speed[0]
        self.rect.y += self.speed[1]
        self.window.blit(self.image, self.rect)
        # Если он вышел за пределы экрана, удаляем
        if not (
            0 < self.rect.right and self.rect.left < self.window.get_width()
        ) or not (0 < self.rect.bottom and self.rect.top < self.window.get_height()):
            self.kill()


class Player(pg.sprite.Sprite):
    def __init__(self, window, filename, hero_x=100, hero_y=25, width=100):
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
        self.window = window

    def flip(self, dir):
        # Отражения игрока при езде в другую сторону
        if dir != self.dir:
            self.image = pg.transform.flip(self.image, True, False)
            self.dir = dir

    def fire(self):
        """
        Выстрел игрока

        Returns:
            Bullet: возвращает объект снаряда
        """
        # Вычисляем координаты создания снаряда
        _dir = (self.dir == "right") * 2 - 1
        angle = 35
        if _dir < 0:
            angle = 180 - angle
        speed = 10
        # Создаем снаряд
        return Bullet(
            self.window,
            "./bullet.png",
            pos=[self.rect.x + _dir * 50, self.rect.y - 30],
            speed=[_dir * speed, -speed * tan(angle)],
            width=50,
            angle=angle,
        )


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
        self.enemies = pg.sprite.Group()
        self.preset()

    def preset(self):
        """
        Предварительные настрокйки игры
        """
        self.player = Player(self.window, "tank.png", hero_y=400)
        self.bullets = pg.sprite.Group()

        self.enemies.add(Enemy(self.window, "enemy.png", 100, 100, 110, speed=[10, 0]))
        self.enemies.add(Enemy(self.window, "enemy.png", 100, 120, 150, speed=[-5, 0]))

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
                    elif event.key == pg.K_SPACE:
                        self.bullets.add(self.player.fire())

                # При отпускании кнопки останавливаем фон
                elif event.type == pg.KEYUP:
                    self.player.speed[0] = 0
                    self.player.speed[1] = 0
            # Обновляем экран, делаем задержку, переходим к слудующей итерации
            self.update_all()
            self.clock.tick(self.FPS)

    def update_all(self):
        # Проверка, выходит ли игрок за границы окна
        if not (
            (self.player.rect.left <= 0 and self.player.speed[0] > 0)
            or self.player.rect.right >= self.window.get_width()
            and self.player.speed[0] < 0
        ):
            self.player.rect.x -= self.player.speed[0]
            # Если игрок не уперся вверх или вниз, сдвигаем по вертикали
            if (self.player.speed[1] > 0 and self.player.rect.top > 0) or (
                self.player.speed[1] < 0 and self.player.rect.bottom < 510
            ):
                self.player.rect.y -= self.player.speed[1]
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
        # Проходим по снарядам и если какой-то попал, удаляем врага
        for bullet in self.bullets:
            pg.sprite.spritecollide(bullet, self.enemies, True)
        self.enemies.update()
        self.player.update()
        # Нормально сдвинуть пулю, чтобы создавалась из центраы
        self.bullets.update()
        # Обновляем экран
        pg.display.update()

    def run(self):
        self.mainloop()


def main():
    game = Game("./background.png")
    game.run()


if __name__ == "__main__":
    main()
