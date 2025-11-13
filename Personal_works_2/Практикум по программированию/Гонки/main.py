import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
from cmath import polar, rect, pi


class App(tk.Tk):
    def run(self):
        self.mainloop()

    def __init__(self):
        # Размеры холста
        self.shape = 600, 400
        # Ширина дороги
        self.road_width = 70
        # Цвета
        self.colors = {"bg": "white", "road": "gray"}
        super().__init__()
        # Создаем холст
        self.canvas = tk.Canvas(
            width=self.shape[0], height=self.shape[1], bg=self.colors["bg"]
        )
        # Помещаем холст в окно
        self.canvas.pack()
        # Отрисовываем дорогу
        self.add_road()
        # Отрисовываем машинку
        self.add_car()
        # Запускаем машинку
        self.next_pos()

    def add_road(self):
        thick = self.road_width
        # Левая дуга
        self.canvas.create_arc(
            # Определяем координаты прямоугольника в котороый вписываем дугу
            thick,
            thick,
            self.shape[1] - thick,
            self.shape[1] - thick,
            # Определяем начало и конец дуги
            start=90,
            extent=180,
            # Ширина дуги
            width=thick,
            style="arc",
            outline=self.colors["road"],
        )
        # Правая дуга
        self.canvas.create_arc(
            self.shape[0] - (self.shape[1] - thick),
            thick,
            self.shape[0] - thick,
            self.shape[1] - thick,
            start=-90,
            extent=180,
            width=thick,
            style="arc",
            outline=self.colors["road"],
        )
        # Верхний прямоугльник
        self.canvas.create_rectangle(
            self.shape[1] / 2,
            thick / 2,
            self.shape[0] - self.shape[1] / 2,
            thick * 1.5,
            fill=self.colors["road"],
            outline=self.colors["road"],
        )
        # Нижний прямоугльник
        self.canvas.create_rectangle(
            self.shape[1] / 2,
            self.shape[1] - thick / 2,
            self.shape[0] - self.shape[1] / 2,
            self.shape[1] - thick * 1.5,
            fill=self.colors["road"],
            outline=self.colors["road"],
        )

    def add_car(self):
        # Загружаем изображение
        self.raw_image_car = Image.open("./car.png")

        # Определяем во сколько раз машинка шире дороги
        scale = self.raw_image_car.height / self.road_width

        # Меняем размер под ширину дороги
        self.raw_image_car = self.raw_image_car.resize(
            (np.array(self.raw_image_car.size) / scale).astype(int)
        )

        # Преобразуем в изображение для отрисовки
        self._image_car = ImageTk.PhotoImage(self.raw_image_car)

        # Отрисовываем в верхней точке дороги
        self.car = self.canvas.create_image(
            self.shape[0] / 2, self.road_width, image=self._image_car
        )

    def next_pos(self):
        # Получаем координаты машинки
        x, y = self.canvas.coords(self.car)

        # Если едем по прямой (не заехали на дугу)
        if self.shape[1] / 2 < x < self.shape[0] - self.shape[1] / 2:
            # Определяем в каком направлении двигаться
            shift = (y < self.shape[1] / 2) * 2 - 1
            # Смещаем машинку
            self.canvas.move(self.car, shift / 4, 0)
        else:
            # Если поворачиваем (едем по дуге)
            l = pi * self.shape[1]
            # Вычисляем координаты относительно цента ближайшего круга
            yc = self.shape[1] / 2
            if x > self.shape[0] / 2:
                xc = self.shape[0] - self.shape[1] / 2
            else:
                xc = self.shape[1] / 2
            x = x - xc
            y = y - yc
            # Переводим в полярные координаты
            r, phi = polar(complex(x, y))
            p = phi
            # Вычисляем сколько проехали (в долях)
            part = phi / pi
            # Увеличиваем проеханную часть и переводим в радианы
            phi = (l * part + 5) / l * pi
            # Переводим в декартовы координаты
            co = rect(r, phi)

            # Получаем новое изображение картинки (повернутое)
            self._image_car = ImageTk.PhotoImage(
                self.raw_image_car.rotate(-90 - (p * 180 / pi))
            )
            # Отрисовываем заново машинку
            self.car = self.canvas.create_image(x + xc, y + yc, image=self._image_car)
            # Сдвигаем машинку на новые координаты
            self.canvas.move(self.car, co.real - x, co.imag - y)

        # Через 10 мс снова запускаем эту функцию
        self.after(1, self.next_pos)


app = App()
app.run()
