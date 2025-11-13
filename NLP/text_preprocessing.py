import re
import string
from time import time

import pymorphy3
from bs4 import BeautifulSoup
from emoji import replace_emoji
from memory_profiler import profile
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Инициализация морфологического анализатора
morph = pymorphy3.MorphAnalyzer()
lemmatizator = WordNetLemmatizer()


def lemma(word):
    return morph.parse(word)[0].normal_form


# @profile
def token(text):
    text = BeautifulSoup(text, "html.parser").get_text()

    # Приведение к нижнему регистру
    text = text.lower()

    # Удаление ссылок
    text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)

    # амена различных кавычек на стандартные ASCII
    for i in "“”‘’«»":
        text = text.replace(i, '"')

    # Удаление цифр
    # Удаление знаков препинания
    # Удаление лишних символов
    text = re.sub(r"\d+|[@#$%^&*-]|" + f"[{string.punctuation}]", " ", text)

    # Замена эмодзи на специальный токен <EMOJI>
    text = replace_emoji(text, "")

    # Удаление лишних пробелов
    text = re.sub(r"\s+", " ", text).strip()
    # Удаление стоп-слов
    stop_words = set(stopwords.words("russian")) | set(stopwords.words("english"))

    # Лемматизация
    new_text = []
    chars = set(string.ascii_lowercase)
    for word in text.split():
        if word in stop_words:
            continue
        if set(word) & chars:
            word = lemmatizator.lemmatize(word)
        else:
            word = lemma(word)
        new_text.append(word)
    text = " ".join(new_text)

    # Удаление отдельно стоящих сммволов
    text = re.sub(" .{,2} ", " ", text)

    tokens = word_tokenize(text, language="russian")
    return text, set(tokens)


def main():
    for i in range(1, 5):
        with open(f"./Текст_{i}.txt", encoding="utf-8") as f:
            data = f.read()
        t = time()
        text, tokens = token(text=data)
        print(f"{'-' * 100}\nText {i}\n{'-' * 100}")
        print()
        print(f"time: {time() - t}")
        print("tokens:", len(tokens))
        print(text)
        print('-'*100)
        print(tokens)


if __name__ == "__main__":
    main()
