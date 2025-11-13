import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


from Objects import Model


x = pd.read_csv(
    "https://raw.githubusercontent.com/koroteevmv/ML_course/main/ML1.1_sgd/data/x.csv",
    index_col=0,
)["0"]
y = pd.read_csv(
    "https://raw.githubusercontent.com/koroteevmv/ML_course/main/ML1.1_sgd/data/y.csv",
    index_col=0,
)["0"]


x = np.array(
    [
        1.09123,
        9.092348,
        2.49873194,
        -3.14920871,
        0.91284721,
        4.194827921,
        -2.918247921847,
        4.2140987921,
        -2.1982734094,
        -8.3472984324,
        3.3492874984,
        3.53928759823,
        -3.3897498274,
    ]
)
y = np.array(
    [
        -9.238947239874,
        -2.48327648,
        -3.98127491874,
        9.91823498742,
        -2.19234781892,
        -1.32847928374,
        6.9384729847924,
        -2.128736823716,
        3.21836827416,
        2.4326524,
        -5.3287468237642,
        -0.871246812746,
        4.981274981724,
    ]
)


x = np.array([2.78, 2.96, 2.64, 2.73, 2.79, 2.60, 2.47, 2.44, 2.86, 2.81, 2.68, 2.87])
y = np.array([7.3, 7.9, 8.0, 8.4, 9.0, 9.4, 10.1, 10.4, 10.3, 10.3, 9.8, 9.2])


plt.figure()
plt.scatter(x, y)
plt.show()


# Создаем и обучаем модель
hyp = Model()
print(hyp.fit(x, y, 0.00001))

hyp.draw_grap_errors()
