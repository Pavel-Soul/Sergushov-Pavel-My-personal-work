import matplotlib.pyplot as plt
import numpy as np


class Model:
    """Модель парной линейной регрессии"""

    def __init__(self):
        # Коэффиценты регрессии
        self.b0 = 0
        self.b1 = 0
        # Была ли модель обучена
        self.is_educated = False
        # Пограшности при обучении
        self.errors = []

    def predict(self, x: float | int) -> float | int:
        """
        Предсказывание y на основе модели
        """
        return self.b0 + self.b1 * x

    def error(self, x: int | float, y: int | float) -> int | float:
        """
        Погрешность предсказаний

        Args:
            x (float | int): Введенный x
            y (float | int): Ожидаемый y

        Returns:
            float | int: Погрешность
        """
        return sum(((self.predict(x) - y) ** 2) / (2 * len(x)))

    def fit(self, X, Y, accuracy=0.01, min_steps=0, alpha=0.001):
        self.is_educated = True
        self.X = X
        self.Y = Y
        # alpha = 0.001
        b0 = []
        b1 = []
        steps = 0
        errors = []
        while (
            (len(errors) < 2)
            or (errors[-2] - errors[-1] > accuracy)
            or steps < min_steps
        ):
            dJ0 = (self.predict(X) - Y).mean()
            dJ1 = ((self.predict(X) - Y) * X).mean()
            self.b0 -= alpha * dJ0
            self.b1 -= alpha * dJ1
            b0.append(self.b0)
            b1.append(self.b1)
            steps += 1
            errors.append(self.error(X, Y))
        self.errors = errors
        return b0, b1

    def draw_grapj_errors(self):
        """
        Отрисовка графика ошибок
        """
        if not self.is_educated:
            return
        plt.plot(self.errors)
        plt.show()


class Model2:
    """Модель парной линейной регрессии"""

    def __init__(self):
        # Коэффиценты регрессии
        self.b0 = 0
        self.b1 = 0
        # Была ли модель обучена
        self.is_educated = False
        # Пограшности при обучении
        self.errors = []

    def predict(self, x: float | int) -> float | int:
        """
        Предсказывание y на основе модели
        """
        return self.b0 + self.b1 * x

    def error(self, x: int | float, y: int | float) -> int | float:
        """
        Погрешность предсказаний

        Args:
            x (float | int): Введенный x
            y (float | int): Ожидаемый y

        Returns:
            float | int: Погрешность
        """
        return sum(((self.predict(x) - y) ** 2) / (2 * len(x)))

    def fit(self, X, Y, accuracy=0.01, min_steps=0, alpha=0.001):
        self.is_educated = True
        for i in range(10):
            print(self._b1_error(X, Y))
            self.b1 += 0.1

    def _b1_error(self, x, y):
        errors = self.predict(x) - y
        # print(errors.mean() - errors)
        return abs(errors.mean() - errors).mean()

    def draw_grap_errors(self):
        """
        Отрисовка графика ошибок
        """
        if not self.is_educated:
            return
        plt.plot(self.errors)
        plt.show()
