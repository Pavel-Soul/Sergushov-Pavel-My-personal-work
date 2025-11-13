import numpy as np


class Bot:
    def __init__(self) -> None:
        self.field = np.zeros((10, 10), int)
        self.last_shoot = []

    def is_empty(self, y, x):
        return self.field[y, x] == 0

    def get_shoot(self):
        while not self.is_empty(*(cords := np.random.randint(0, 10, 2))):
            ...
        self.last_shoot = cords
        return cords

    def result(self, res):
        if res == 0:
            self.field[*self.last_shoot] = 1

        elif res in (2, 3):
            self.field[*self.last_shoot] = 2
            y, x = self.last_shoot

            for row in range(max([y - 1, 0]), min([y + 2, 10])):
                for col in range(max([x - 1, 0]), min([x + 2, 10])):
                    if row != y and col != x:
                        self.field[row, col] = 1

        if res == 3:
            self.__set_empty_around(*self.last_shoot)

    def __set_empty_around(self, y, x):
        self.field[y, x] = 3
        for row in range(max([y - 1, 0]), min([y + 2, 10])):
            for col in range(max([x - 1, 0]), min([x + 2, 10])):
                if self.field[row, col] == 0:
                    self.field[row, col] = 1
                elif self.field[row, col] == 2:
                    self.__set_empty_around(row, col)

    def __str__(self) -> str:
        d = "    0 1 2 3 4 5 6 7 8 9"
        d += "\n" + "-" * len(d)
        for n, row in enumerate(self.field):
            d += f"\n{n} | " + " ".join([" .ox"[c] for c in row])
        return d + "\n"


# from backend import Field

# np.random.seed(1223)

# field = Field()
# field.auto_fill()
# field.start_game()
# bot = Bot()

# count = 0
# while True:
#     count += 1
#     y, x = bot.get_shoot()
#     res = field.shoot(y, x)
#     bot.result(res)
#     if res == 4:
#         break
#     if res == 3:
#         print(bot)
# print(field)
# print(count)
