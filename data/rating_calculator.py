def rating_calculation(first, second, result):
    e = 1 / (1 + 10 ** ((second - first) / 400))
    k = 20
    return int(first + k * (result - e))
