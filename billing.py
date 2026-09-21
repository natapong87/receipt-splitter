from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


TWOPLACES = Decimal('0.01')


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def split_amount(amount: Decimal, people: list[str]) -> dict[str, Decimal]:
    """Split money exactly to satang; any rounding remainder goes to earlier names."""
    if not people:
        return {}
    amount = money(amount)
    n = len(people)
    base = (amount / n).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    shares = {p: base for p in people}
    diff = amount - sum(shares.values(), Decimal('0.00'))
    cents = int((diff / TWOPLACES).to_integral_value())
    step = TWOPLACES if cents > 0 else -TWOPLACES
    for p in people[:abs(cents)]:
        shares[p] += step
    return shares


def allocate_proportionally(amount: Decimal, weights: dict[str, Decimal]) -> dict[str, Decimal]:
    amount = money(amount)
    if amount == 0 or not weights:
        return {p: Decimal('0.00') for p in weights}
    total = sum(weights.values(), Decimal('0.00'))
    if total <= 0:
        return split_amount(amount, list(weights))

    raw = {p: (amount * w / total) for p, w in weights.items()}
    rounded = {p: v.quantize(TWOPLACES, rounding=ROUND_HALF_UP) for p, v in raw.items()}
    diff = amount - sum(rounded.values(), Decimal('0.00'))
    cents = int((diff / TWOPLACES).to_integral_value())
    order = sorted(weights, key=lambda p: (raw[p] - rounded[p]), reverse=(cents > 0))
    step = TWOPLACES if cents > 0 else -TWOPLACES
    for p in order[:abs(cents)]:
        rounded[p] += step
    return rounded


def calculate_bill(instances: Iterable[dict], people: list[str], service_charge=0, vat=0, discount=0):
    food = {p: Decimal('0.00') for p in people}
    details = {p: [] for p in people}
    unassigned = []

    for item in instances:
        consumers = [p for p in item.get('people', []) if p in food]
        price = money(item.get('price', 0))
        if not consumers:
            unassigned.append(item)
            continue
        shares = split_amount(price, consumers)
        for person, share in shares.items():
            food[person] += share
            details[person].append({
                'item': item.get('label') or item.get('name', 'รายการ'),
                'amount': share,
            })

    service_alloc = allocate_proportionally(money(service_charge), food)
    vat_alloc = allocate_proportionally(money(vat), food)
    discount_alloc = allocate_proportionally(money(discount), food)

    totals = {}
    for p in people:
        totals[p] = money(food[p] + service_alloc[p] + vat_alloc[p] - discount_alloc[p])

    return {
        'food': food,
        'service': service_alloc,
        'vat': vat_alloc,
        'discount': discount_alloc,
        'totals': totals,
        'details': details,
        'unassigned': unassigned,
    }
