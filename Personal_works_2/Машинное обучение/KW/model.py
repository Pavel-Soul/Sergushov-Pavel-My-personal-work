import matplotlib.pyplot as plt
import numpy as np



class Model:

    def __init__(self):
        # Коэффиценты регрессии
        self.coef_ = []
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
        return self.coef_[0] + sum([x[n]*co for n, co in enumerate(self.coef_[1:])])

    def fit(self, X, Y, accuracy=0.01, min_steps=0, alpha=0.001):
        X = np.X
        Y = np.Y
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
