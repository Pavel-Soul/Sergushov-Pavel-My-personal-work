import tkinter as tk
from random import randint, random, sample

"""
Простой кликер с появляющимеся кругами
Цель - нажать на круг пока он не исчез
Как только 5 раз нажато мимо или 5 кругов исчезло, игра завершается
Есть запись рекорда (в пределах сессии)
"""

width = 640
height = 480
settings = default_settings = {
    "ups": 10,  # Обновлений в секунду
    "prob": 0.07,  # Вероятность появления нового круга
    "flag": 10,
    "limit": 5,
    # Минимальный и максимальный размер круга
    "min_circle": min(width, height) // 9,
    "max_circle": min(width, height) // 3,
}

app = tk.Tk()
app.resizable(False, False)

info = tk.Frame()
clicks = tk.IntVar()
record = tk.IntVar()
hits = tk.IntVar()
miss = tk.StringVar(value=f"0/{settings['limit']}")

canvas = tk.Canvas(height=height, width=width, bg="#ccc")
tk.Label(info, text="Нажатия").pack(side="left")
tk.Label(info, textvariable=clicks).pack(side="left")
tk.Label(info, text="Попадания").pack(side="left")
tk.Label(info, textvariable=hits).pack(side="left")
tk.Label(info, text="Промахи").pack(side="left")
tk.Label(info, textvariable=miss).pack(side="left")
tk.Label(info, text="Рекорд").pack(side="left")
tk.Label(info, textvariable=record).pack(side="left")

info.pack()
canvas.pack()


def miss_label_update():
    # Обновление строки с промахами
    miss.set(f"{clicks.get()-hits.get()}/{settings['limit']}")


def onclick(circle):
    """
    Нажатие на круг
    """
    bubbles.remove(circle)
    hits.set(hits.get() + 1)
    record.set(max(record.get(), hits.get()))
    # Каждые 10 попаданий
    if hits.get() >= settings["flag"]:
        settings["flag"] += 10
        # Увеличиваем скорость
        settings["ups"] += 1
        # Увеличиваем количество доступных промахов
        settings["limit"] += 2


def late(circle):
    # Если круг слишком уменьшился, он исчезает
    bubbles.remove(circle)
    clicks.set(clicks.get() + 1)


def random_color():
    mas = randint(0, 86), randint(86, 171), randint(171, 255)
    return "#{:0<2x}{:0<2x}{:0<2x}".format(*sample(mas, 3))


class Bubble:
    def __init__(self, x, y, size, canvas):
        self.size = size + 1
        self.x = x
        self.y = y
        self.canvas = canvas
        self.circle = 0
        self.color = random_color()
        self.update()

    def update(self):
        # Уменьшаем круг
        # 20 - число шагов за которые он сойдет до 0
        self.size -= self.size / 20
        self.canvas.delete(self.circle)
        self.circle = self.canvas.create_oval(
            self.x - self.size,
            self.y - self.size,
            self.x + self.size,
            self.y + self.size,
            outline=self.color,
            fill=self.color,
        )
        # Обновляем функцию его нажатия
        myid = id(self)
        self.canvas.tag_bind(self.circle, "<Button-1>", lambda _: onclick(myid))

        # Если размер круга меньше 3 - удаляем
        if self.size < 3:
            late(id(self))

    def __del__(self):
        # При удалении чистим круг с холста
        self.canvas.delete(self.circle)


class Field:
    # Хранилище кругов по id объекта
    def __init__(self) -> None:
        self.mas = {}

    def add(self, bubble):
        self.mas[id(bubble)] = bubble

    def remove(self, ind):
        if ind in self.mas:
            del self.mas[ind]

    def __iter__(self):
        return iter(list(self.mas.values()))

    def clear(self):
        self.mas.clear()


bubbles = Field()


def create_bubble():
    """
    Добавление нового круга
    """
    size = randint(settings["min_circle"], settings["max_circle"])
    bubbles.add(
        Bubble(
            random() * (width - size * 2) + size,
            random() * (height - size * 2) + size,
            size,
            canvas,
        )
    )


def canvas_click(*_):
    """
    Любое нажатие на холст
    """
    clicks.set(clicks.get() + 1)
    miss_label_update()


def start():
    """
    Сброс всех значений кроме рекорда
    """
    global settings
    settings = default_settings.copy()
    canvas.delete("all")
    clicks.set(0)
    hits.set(0)
    miss_label_update()
    canvas.bind("<Button-1>", canvas_click)
    loop()


def loop():
    """
    Один круг программы
    """
    # Обновляем все круги
    for b in bubbles:
        b.update()

    # Если еще не привысили лимит промахов
    if clicks.get() - hits.get() < settings["limit"]:
        # Создаем круг с веротностью 0.07 (по умолчанию)
        if random() < settings["prob"]:
            create_bubble()
        # Запускаем эту функцию повторно
        app.after(1000 // settings["ups"], loop)
    else:
        # Иначе удаляем все круги
        bubbles.clear()
        # Пишем "Конец игры"
        canvas.create_text(
            width / 2,
            height / 2 - 30,
            text="Конец игры",
            font="Arial 24",
            fill="red",
        )
        canvas.create_text(
            width / 2,
            height / 2,
            text="Нажмите чтобы начать заново",
            font="Arial 12",
            fill="red",
        )
        # Привязываем к холсту функцию начала игры
        canvas.bind("<Button-1>", lambda _: start())


start()
app.mainloop()
