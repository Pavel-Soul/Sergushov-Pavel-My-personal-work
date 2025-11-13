chars = 'КайУгвейШеньШифу'.lower()


def test(word):
    for c in set(word):
        if not word.count(c) <= chars.count(c):
            return False
    return True


with open("./litw-win.txt") as f:
    for word in f:
        word = word.split()[-1]
        if test(word) and len(word) > 3:
            print(word, end=', ')
