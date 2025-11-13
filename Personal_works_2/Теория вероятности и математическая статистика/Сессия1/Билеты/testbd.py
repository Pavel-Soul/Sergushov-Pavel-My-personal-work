from dataclasses import dataclass, asdict
import json


@dataclass
class User:
    # Аналогично твоему созданию класса
    id: int
    uid: int
    money: int
    power: int


def save_bd(users, path="data.json"):
    # Преобразуем все объекты в словари
    lines = [asdict(user) for user in users]
    # Сохраняем пользователей в файл
    with open(path, "w", encoding="utf-8") as file:
        json.dump(lines, file, ensure_ascii=False)


def read_bd(path="data.json"):
    # Читаем файл
    with open(path, "r", encoding="utf-8") as file:
        lines = json.load(file)

    # Из каждой строки создаем объект пользователя
    users = [User(**line) for line in lines]
    return users


# Пример использования
if __name__ == "__main__":
    # Создаем список пользователей
    users = [
        User(1111, 1, 1000, 100),
        User(2222, 2, 3000, 200),
        User(3333, 3, 500, 1000),
    ]
    # Сохраняем
    save_bd(users)
    # Читаем
    data = read_bd()
    print(data)
