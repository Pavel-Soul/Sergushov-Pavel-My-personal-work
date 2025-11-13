import random as rand
import matplotlib.pyplot as plt


def graph(func, test_count=1_000_000, seed=1223):
    if seed:
        rand.seed(seed)

    results = [0]

    for _ in range(test_count):
        results.append(bool(func()) + results[-1])

    results = [el / (n+1) for n, el in enumerate(results[1:])]

    mean = sum(results)/test_count
    s = results[test_count//50:]
    k = max(s) - min(s)
    plt.ylim(mean-k, mean+k)

    real_mean = sum(results[test_count//20:]) / (test_count//20*19)

    plt.plot(results)
    plt.plot([0, test_count], [real_mean, real_mean])

    return real_mean
