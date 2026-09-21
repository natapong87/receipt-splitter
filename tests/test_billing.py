from decimal import Decimal
from billing import calculate_bill, split_amount


def test_same_menu_two_orders_different_people():
    instances = [
        {'name': 'กะเพรา', 'label': 'กะเพรา #1', 'price': 100, 'people': ['A', 'B']},
        {'name': 'กะเพรา', 'label': 'กะเพรา #2', 'price': 100, 'people': ['C']},
    ]
    r = calculate_bill(instances, ['A', 'B', 'C'])
    assert r['totals']['A'] == Decimal('50.00')
    assert r['totals']['B'] == Decimal('50.00')
    assert r['totals']['C'] == Decimal('100.00')


def test_rounding_preserves_total():
    shares = split_amount(Decimal('100.00'), ['A', 'B', 'C'])
    assert sum(shares.values()) == Decimal('100.00')


def test_service_vat_discount_preserve_total():
    instances = [
        {'name': 'x', 'label': 'x', 'price': 100, 'people': ['A']},
        {'name': 'y', 'label': 'y', 'price': 200, 'people': ['B']},
    ]
    r = calculate_bill(instances, ['A', 'B'], service_charge=30, vat=21, discount=15)
    assert sum(r['totals'].values()) == Decimal('336.00')
