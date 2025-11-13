class Fraction:
    def __init__(self, numerator: int | float | str, denominator=None):
        # Если передано только одно значение
        if not denominator:
            match numerator:
                # Если передано целое число
                case int():
                    denominator = 1
                # Если передана строка как деление 125/3
                case str() if '/' in numerator:
                    numerator, denominator = numerator.split('/')
                # Если передана строка как число '123.45'
                case str():
                    ...
                case float(num):
                    numerator, denominator = self.float_to_fraction(num)

        if denominator == 0:
            raise ZeroDivisionError('Denominator is 0')

        self.numerator = int(numerator)
        self.denominator = int(denominator)

    @staticmethod
    def float_to_fraction(num):
        ...

    def __float__(self):
        return self.numerator / self.denominator

    def __sum__(self, other):
        ...

    def __sum_r__(self, other):
        ...
