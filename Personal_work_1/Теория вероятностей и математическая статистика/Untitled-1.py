def Atbash(key):

    lower = "".join([chr(i) for i in range(97, 97+26)])
    upper = "".join([chr(i) for i in range(65, 65+26)])
    symbols = "".join([chr(i) for i in range(35, 65)])
    # Л 26
    result = ""
    for i in key:
        if i in lower:
            for symbol in range(len(lower)):
                if lower[symbol] == i:
                    result += (lower[::-1])[symbol]
        elif i in upper:
            for symbol in range(len(upper)):
                if upper[symbol] == i:
                    result += (upper[::-1])[symbol]
        elif i in symbols:
            for symbol in range(len(symbols)):
                if symbols[symbol] == i:
                    result += (symbols[::-1])[symbol]
    return result


# 'sggkh)44ddd5blfgfyv5xln4dzgxs$e&Vgoi6g*AHbR'
print(Atbash('sggkh)44ddd5blfgfyv5xln4dzgxs$e&Vgoi6g*AHbR'))
# print(Atbash('ghbkj_tybtnht_etnj_hf_jnrbbyajhvfwbbgjdnjhbntgjgsnre'))
#
