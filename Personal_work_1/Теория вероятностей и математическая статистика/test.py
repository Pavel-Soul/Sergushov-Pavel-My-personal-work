def f(x, y):
    if x == 0 and y > 0:
        return 0
    if y > 0 and x > 0:
        return f(x-1, y-1)
    if x > 0 and y == 0:
        return x

# def f(x, y):
#     match x, y:
#         case 1, 1:
#             return 0
#         case 0, 1:
#             return 0
#         case 1, 0:
#             return 1
#     if y > 1:
#         return f(f(x, y-1), 1)
#     return f(x-1, f(y, 1))


print(f(12, 7))
print(f(7, 12))
