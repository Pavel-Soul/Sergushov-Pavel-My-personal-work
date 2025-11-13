import numpy as np


class Ship:
    def __init__(self, coords) -> None:
        self.coords = coords
        self.len = len(coords)
        self.shoots = 0

    def shoot(self):
        self.shoots += 1
        # Сбит
        if self.shoots == self.len:
            return 3
        return 2


class Field:
    def __init__(self) -> None:
        self.__game_state = 0
        self.field = np.zeros((10, 10), int)
        self.ships = []

    def __str__(self) -> str:
        d = "    0 1 2 3 4 5 6 7 8 9"
        d += "\n" + "-" * len(d)
        for n, row in enumerate(self.field):
            d += f"\n{n} | " + " ".join([" .ox"[c] for c in row])
        return d + "\n"

    def start_game(self):
        # Проверка на готовность поля
        if not sum(self.needs_ships.values()):
            self.__game_state = 1

    def check_cell(self, y, x):
        for row in range(max([y - 1, 0]), min([y + 2, 10])):
            for col in range(max([x - 1, 0]), min([x + 2, 10])):
                if self.field[row, col] != 0:
                    return False
        return True

    @property
    def needs_ships(self):
        ships = {1: 4, 2: 3, 3: 2, 4: 1}
        for ship in self.ships:
            ships[ship.len] -= 1
        return ships

    def add_ship(self, y, x, d, le):
        coords = [[y, x]]
        for _ in range(le - 1):
            coords.append(coords[-1].copy())
            coords[-1][d] += 1

        if self.__game_state != 0:
            return False

        # Проверка что корабль в пределах карты
        if np.max(coords) > 9 or np.min(coords) < 0:
            return False

        # Проверка что не хватает кораблей это длинны
        if self.needs_ships.get(le, 0) == 0:
            return False

        # Проверка что клетки пустые
        for row, col in coords:
            if not self.check_cell(row, col):
                return False

        self.ships.append(Ship(coords))
        for row, col in coords:
            self.field[row, col] = 2
        return True

    def remove_ship(self, y, x):
        for ship in self.ships:
            if ([y, x] in ship.coords) or y < 0:
                for row, col in ship.coords:
                    self.field[row, col] = 0
                self.ships.remove(ship)
                return True

    def remove_all_ships(self):
        for ship in self.ships:
            for row, col in ship.coords:
                self.field[row, col] = 0
        self.ships = []

    def auto_fill(self):
        def random_ship(le):
            return [*np.random.randint(0, 10, 2), np.random.randint(0, 2), le]

        # Удаляем все корабли
        self.remove_all_ships()
        for le in [1, 2, 3, 4]:
            for _ in range(1, 6 - le):
                while not self.add_ship(*random_ship(le)):
                    ...

    def shoot(self, y, x):
        if self.__game_state != 1:
            return
        match self.field[y, x]:
            # Если пусто
            case 0:
                self.field[y, x] = 1
                return 0
            # Если есть не сбитый корабль
            case 2:
                self.field[y, x] = 3
                # Если нет больше кораблей, игра завершена
                if 2 not in self.field:
                    self.__game_state = 2
                    return 4
                for ship in self.ships:
                    if [y, x] in ship.coords:
                        return ship.shoot()
        # Если уже стреляли по этим координатам
        return 1


# np.random.seed(1223)

# field = Field()
# field.auto_fill()
# field.auto_fill()
# print(field)
# field.auto_fill()
# print(field)
# field.start_game()
# print(field)
# for y in range(10):
#     for x in range(10):
#         r = field.shoot(y, x)
#         if r == 4:
#             break
#     else:
#         continue
#     break
# print(field)

# Корабль определяется следующими параметрами
# Координаты начала (y, x)
# Направление (0 - вертикально, 1 - горизонтально)
# Длинна (1 - 4)

# Поле
# 0 - Пусто
# 1 - Выстрел мимо
# 2 - Корабль
# 3 - Раненный корабль

# Результаты стрельбы
# 0 - Мимо
# 1 - Повторный выстрел
# 2 - Ранел
# 3 - Сбил
# 4 - Конец игры
