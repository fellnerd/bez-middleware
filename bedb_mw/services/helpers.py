from decimal import Decimal

def dec(num):
    a = Decimal(str(num))
    b = a.quantize(Decimal('1.00'))
    return b