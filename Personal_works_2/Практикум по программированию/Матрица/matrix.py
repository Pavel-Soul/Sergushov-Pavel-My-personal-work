import tkinter as tk
from random import randint, choice, random
import numpy as np

app = tk.Tk()
width, height = 640, 480
canvas = tk.Canvas(width=width, height=height, bg="#0a0c03")
canvas.pack()
w = 30

symbols = list(
    "ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔ"
)


class Line:
    """
    Класс падающей строчки
    """

    def __init__(self, length, canvas, height, width, shift):
        # Позиция первого символа
        self.pos = -1
        # Длинна всей строчки
        self.len = length
        self.canvas = canvas
        # Отрисованные символы
        self.chars = []
        # Есть ли следующая строчка
        self.next = False
        # Характеристика холста
        self.height = height
        self.shift = shift
        self.width = width

    def update(self):
        self.pos += 1
        for n, char in enumerate(self.chars):
            if char is not None:
                self.canvas.itemconfigure(
                    char,
                    # DIS Мне очень не нравится как выглядят постоянно меняющиеся символы
                    text=choice(symbols),
                    # fill=f"#00{round(((n/self.len))*255):0>2x}00",
                    fill=f"#00{round(((n/len(self.chars))*0.8+0.2)*255):0>2x}00",
                )
        # Если голова еще не ушла с холста
        if self.pos - self.len < self.height:
            # Рисует новый символ и добавляет в начало строки
            te = self.canvas.create_text(
                # Сдвиг по X
                self.width / 1.5 + self.shift * self.width,
                # Сдвиг по Y
                self.width * self.pos + self.width / 1.5,
                text=choice(symbols),
                fill="#76ffa0",
                font=f"Arialblack {self.width}",
            )
            self.chars.append(te)
        # Иначе добавляет пустой символ
        else:
            self.chars.append(None)

        # Если символов больше, чем длинна, удаляем лишние
        if len(self.chars) > self.len:
            if t := self.chars.pop(0):
                self.canvas.delete(t)

    def adc(self, char):
        self.chars.append(char)


class Symcol:
    """
    Класс одной колонки на экране
    """

    def __init__(self, width, height, canvas, shift=0):
        # Отступ колонки слева
        self.shift = shift
        # Ширина колонки
        self.width = width
        # Высота колонки в символах
        self.heigth = height // width
        self.canvas = canvas

        # Строчки идущие по колонке
        self.lines = []
        # Создаем первую строчку
        self.create_line()

    def create_line(self):
        """
        Добавляет строку на колонку
        """
        self.lines.append(
            # Берет случайную высоту строчки от половины до полутора высоты холста
            Line(
                randint(self.heigth // 2, round(self.heigth * 1.5)),
                self.canvas,
                self.heigth,
                self.width,
                self.shift,
            )
        )

    def update(self):
        """
        Обновляет все строки на колонке
        """
        # Проходит по всем строкам
        self.draw()
        for line in self.lines:
            # Обновляет строку
            line.update()

    def draw(self):
        """
        Отрисовывает символы
        """

        # Строки которые будут удалены
        dlist = []
        # Проходит по строкам
        for line in self.lines:
            # Если хвост строки за холстом, добавляем строку в список на удаление
            if line.pos - line.len >= height // 18:
                dlist.append(line)

            # Если ...
            if (
                # .. у линии еще нет следующей
                not line.next
                # ... хвост уже на холсте
                and (k := line.pos - line.len) > 0
                # ... с вероятностью равной близости хвоста к концу холста
                and (1 - random() ** 3) < k / self.heigth
            ):
                # Создаем новую линию
                self.create_line()
                line.next = True

        # Удаляем все строки вышедшие за экран
        for line in dlist:
            self.lines.remove(line)


# Ширина одного столбца
wi = 18
# Делим ширину холста на ширину столбца и создаем нужное количество столбцов
# mas = [Symcol(wi, height, canvas, s) for s in range(1)]
mas = [Symcol(wi, height, canvas, s) for s in range(width // wi)]


def move():
    # Проходим по всем столбцам и обновляем их
    for column in mas:
        column.update()
    app.after(1, move)


move()
app.mainloop()
