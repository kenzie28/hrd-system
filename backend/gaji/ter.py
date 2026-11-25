"""Monthly PPh 21 TER brackets transcribed from TER PPH Simplified.xlsx.

Each row is (minimum, maximum, fraction). ``maximum`` is inclusive. A value
that sits on a shared boundary stays in the lower row. ``None`` means no ceiling.
The sheet stores the tarif as a fraction (0.0025 = 0.25%).
"""
from decimal import Decimal

TER_BRACKETS: dict[str, tuple[tuple[int, int | None, Decimal], ...]] = {
    'A': (
        (0, 5400000, Decimal('0')),
        (5400000, 5650000, Decimal('0.0025')),
        (5650000, 5950000, Decimal('0.005')),
        (5950000, 6300000, Decimal('0.0075')),
        (6300000, 6750000, Decimal('0.01')),
        (6750000, 7500000, Decimal('0.0125')),
        (7500000, 8550000, Decimal('0.015')),
        (8550000, 9650000, Decimal('0.0175')),
        (9650000, 10050000, Decimal('0.02')),
        (10050000, 10350000, Decimal('0.0225')),
        (10350000, 10700000, Decimal('0.025')),
        (10700000, 11050000, Decimal('0.03')),
        (11050000, 11600000, Decimal('0.035')),
        (11600000, 12500000, Decimal('0.04')),
        (12500000, 13750000, Decimal('0.05')),
        (13750000, 15100000, Decimal('0.06')),
        (15100000, 16950000, Decimal('0.07')),
        (16950000, 19750000, Decimal('0.08')),
        (19750000, 24150000, Decimal('0.09')),
        (24150000, 26450000, Decimal('0.1')),
        (26450000, 28000000, Decimal('0.11')),
        (28000000, 30050000, Decimal('0.12')),
        (30050000, 32400000, Decimal('0.13')),
        (32400000, 35400000, Decimal('0.14')),
        (35400000, 39100000, Decimal('0.15')),
        (39100000, 43850000, Decimal('0.16')),
        (43850000, 47800000, Decimal('0.17')),
        (47800000, 51400000, Decimal('0.18')),
        (51400000, 56300000, Decimal('0.19')),
        (56300000, 62200000, Decimal('0.2')),
        (62200000, 68600000, Decimal('0.21')),
        (68600000, 77500000, Decimal('0.22')),
        (77500000, 89000000, Decimal('0.23')),
        (89000000, 103000000, Decimal('0.24')),
        (103000000, 125000000, Decimal('0.25')),
        (125000000, 157000000, Decimal('0.26')),
        (157000000, 206000000, Decimal('0.27')),
        (206000000, 337000000, Decimal('0.28')),
        (337000000, 454000000, Decimal('0.29')),
        (454000000, 550000000, Decimal('0.3')),
        (550000000, 695000000, Decimal('0.31')),
        (695000000, 910000000, Decimal('0.32')),
        (910000000, 1400000000, Decimal('0.33')),
        (1400000000, None, Decimal('0.34')),
    ),
    'B': (
        (0, 6200000, Decimal('0')),
        (6200000, 6500000, Decimal('0.0025')),
        (6500000, 6850000, Decimal('0.005')),
        (6850000, 7300000, Decimal('0.0075')),
        (7300000, 9200000, Decimal('0.01')),
        (9200000, 10750000, Decimal('0.015')),
        (10750000, 11250000, Decimal('0.02')),
        (11250000, 11600000, Decimal('0.025')),
        (11600000, 12600000, Decimal('0.03')),
        (12600000, 13600000, Decimal('0.04')),
        (13600000, 14950000, Decimal('0.05')),
        (14950000, 16400000, Decimal('0.06')),
        (16400000, 18450000, Decimal('0.07')),
        (18450000, 21850000, Decimal('0.08')),
        (21850000, 26000000, Decimal('0.09')),
        (26000000, 27700000, Decimal('0.1')),
        (27700000, 29350000, Decimal('0.11')),
        (29350000, 31450000, Decimal('0.12')),
        (31450000, 33950000, Decimal('0.13')),
        (33950000, 37100000, Decimal('0.14')),
        (37100000, 41100000, Decimal('0.15')),
        (41100000, 45800000, Decimal('0.16')),
        (45800000, 49500000, Decimal('0.17')),
        (49500000, 53800000, Decimal('0.18')),
        (53800000, 58500000, Decimal('0.19')),
        (58500000, 64000000, Decimal('0.2')),
        (64000000, 71000000, Decimal('0.21')),
        (71000000, 80000000, Decimal('0.22')),
        (80000000, 93000000, Decimal('0.23')),
        (93000000, 109000000, Decimal('0.24')),
        (109000000, 129000000, Decimal('0.25')),
        (129000000, 163000000, Decimal('0.26')),
        (163000000, 211000000, Decimal('0.27')),
        (211000000, 374000000, Decimal('0.28')),
        (374000000, 459000000, Decimal('0.29')),
        (459000000, 555000000, Decimal('0.3')),
        (555000000, 704000000, Decimal('0.31')),
        (704000000, 957000000, Decimal('0.32')),
        (957000000, 1405000000, Decimal('0.33')),
        (1405000000, None, Decimal('0.34')),
    ),
    'C': (
        (0, 6600000, Decimal('0')),
        (6600000, 6950000, Decimal('0.0025')),
        (6950000, 7350000, Decimal('0.005')),
        (7350000, 7800000, Decimal('0.0075')),
        (7800000, 8850000, Decimal('0.01')),
        (8850000, 9800000, Decimal('0.0125')),
        (9800000, 10950000, Decimal('0.02')),
        (10950000, 11200000, Decimal('0.0175')),
        (11200000, 12050000, Decimal('0.02')),
        (12050000, 12950000, Decimal('0.03')),
        (12950000, 14150000, Decimal('0.04')),
        (14150000, 15550000, Decimal('0.05')),
        (15550000, 17050000, Decimal('0.06')),
        (17050000, 19500000, Decimal('0.07')),
        (19500000, 22700000, Decimal('0.08')),
        (22700000, 26600000, Decimal('0.09')),
        (26600000, 28100000, Decimal('0.1')),
        (28100000, 30100000, Decimal('0.11')),
        (30100000, 32600000, Decimal('0.12')),
        (32600000, 35400000, Decimal('0.13')),
        (35400000, 38900000, Decimal('0.14')),
        (38900000, 43000000, Decimal('0.15')),
        (43000000, 47400000, Decimal('0.16')),
        (47400000, 51200000, Decimal('0.17')),
        (51200000, 55800000, Decimal('0.18')),
        (55800000, 60400000, Decimal('0.19')),
        (60400000, 66700000, Decimal('0.2')),
        (66700000, 74500000, Decimal('0.21')),
        (74500000, 83200000, Decimal('0.22')),
        (83200000, 95600000, Decimal('0.23')),
        (95600000, 110000000, Decimal('0.24')),
        (110000000, 134000000, Decimal('0.25')),
        (134000000, 169000000, Decimal('0.26')),
        (169000000, 221000000, Decimal('0.27')),
        (221000000, 390000000, Decimal('0.28')),
        (390000000, 463000000, Decimal('0.29')),
        (463000000, 561000000, Decimal('0.3')),
        (561000000, 709000000, Decimal('0.31')),
        (709000000, 965000000, Decimal('0.32')),
        (965000000, 1419000000, Decimal('0.33')),
        (1419000000, None, Decimal('0.34')),
    ),
}


def ter_fraction(category: str, net: Decimal | int) -> Decimal:
    """Withholding fraction for this TER category and net income.

    Blank category, an unknown category, and net income at or below zero use 0.
    A fractional rupiah is compared as-is, so income just above a boundary uses
    the higher bracket.
    """
    amount = Decimal(net)
    if amount <= 0 or not category:
        return Decimal('0')
    brackets = TER_BRACKETS.get(category)
    if not brackets:
        return Decimal('0')
    for minimum, maximum, rate in brackets:
        if maximum is None:
            if amount > minimum:
                return rate
            continue
        if minimum == 0:
            if amount <= maximum:
                return rate
            continue
        if minimum < amount <= maximum:
            return rate
    return Decimal('0')
