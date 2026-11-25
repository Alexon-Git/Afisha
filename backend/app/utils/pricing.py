"""One pricing contract for API, ORM and import writers; no currency conversion."""
from decimal import Decimal, InvalidOperation
from sqlalchemy import Numeric, String
from sqlalchemy.types import TypeDecorator
from .currencies import CURRENCIES

NEW_FIELDS = {'price_kind', 'price_amount', 'price_max', 'currency'}
FIELDS = NEW_FIELDS | {'price'}
KINDS = {'unknown', 'free', 'fixed', 'from', 'range', 'by_request'}
LIMIT = Decimal('100000000000000')


def amount(value):
    if value is None:
        return None
    if isinstance(value, (float, bool)):
        raise ValueError('Money must be an exact decimal string, not a float')
    try:
        value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError('Invalid decimal amount') from exc
    if not value.is_finite() or value <= 0 or value >= LIMIT or value.as_tuple().exponent < -4:
        raise ValueError('Amount must be positive, below 100000000000000, with at most four decimals')
    return value


def legacy_price(values):
    if values['price_kind'] == 'free':
        return 0
    value = values['price_amount']
    if values['price_kind'] == 'fixed' and values['currency'] == 'RUB' and value == value.to_integral_value() and value <= 2147483647:
        return int(value)
    return None


def from_legacy(price):
    if price is None:
        return dict(price_kind='unknown', price_amount=None, price_max=None, currency=None)
    if isinstance(price, bool) or not isinstance(price, int) or not 0 <= price <= 2147483647:
        raise ValueError('Legacy price must be an integer between 0 and 2147483647')
    return dict(price_kind='free' if price == 0 else 'fixed', price_amount=Decimal(price) if price else None,
                price_max=None, currency='RUB' if price else None)


def normalize_pricing(patch, current=None):
    current = current or {**from_legacy(None), 'price': None}
    explicit = NEW_FIELDS.intersection(patch)
    if not explicit:
        if 'price' not in patch or patch['price'] == current['price']:
            return {name: current[name] for name in FIELDS}
        if current['price_kind'] in {'from', 'range', 'by_request'} or (
            current['price_kind'] == 'fixed' and current['price'] is None):
            raise ValueError('Use the pricing fields to replace a complex price; legacy price would lose data')
        values = from_legacy(patch['price'])
    else:
        # Changing kind is an explicit reset; never inherit hidden amounts/currency.
        values = {name: current[name] for name in NEW_FIELDS}
        if 'price_kind' in patch and patch['price_kind'] != current['price_kind']:
            values = dict(price_kind=patch['price_kind'], price_amount=None, price_max=None, currency=None)
        values.update({key: patch[key] for key in explicit})
    if values['price_kind'] not in KINDS:
        raise ValueError('Invalid price_kind')
    values['price_amount'] = amount(values['price_amount'])
    values['price_max'] = amount(values['price_max'])
    kind, low, high, currency = (values[k] for k in ('price_kind','price_amount','price_max','currency'))
    if kind in {'unknown','free','by_request'}:
        if low is not None or high is not None or currency is not None:
            raise ValueError('This price_kind requires null amounts and currency')
    elif low is None or currency not in CURRENCIES or (kind != 'range' and high is not None) or (kind == 'range' and (high is None or high < low)):
        raise ValueError('Price requires a positive amount, ISO 4217 currency and a valid range')
    result = {**values, 'price': legacy_price(values)}
    if explicit and 'price' in patch and patch['price'] != result['price']:
        raise ValueError('Conflicting legacy and structured prices')
    return result


# Reused by SQLAlchemy metadata and the additive migration. SQL CHECK expressions
# use explicit NULL tests so SQL three-valued logic cannot accept incomplete prices.
SHAPE_SQL = """price_kind IS NOT NULL AND (
(price_kind IN ('unknown','free','by_request') AND price_amount IS NULL AND price_max IS NULL AND currency IS NULL)
OR (price_kind IN ('fixed','from','range') AND price_amount IS NOT NULL AND price_amount > 0
AND price_amount < 100000000000000 AND currency IS NOT NULL AND currency IN (%s)
AND ((price_kind IN ('fixed','from') AND price_max IS NULL)
OR (price_kind='range' AND price_max IS NOT NULL AND price_max >= price_amount AND price_max < 100000000000000))))""" % ','.join("'%s'" % code for code in sorted(CURRENCIES))
COMPAT_SQL = """(
(price_kind='free' AND price IS NOT NULL AND price=0)
OR (price_kind='fixed' AND currency='RUB' AND price_amount=CAST(price_amount AS BIGINT)
AND price_amount<=2147483647 AND price IS NOT NULL AND price=price_amount)
OR (price IS NULL AND (price_kind IN ('unknown','from','range','by_request')
OR (price_kind='fixed' AND (currency<>'RUB' OR price_amount<>CAST(price_amount AS BIGINT) OR price_amount>2147483647)))))"""


def sqlite_compat(sql):
    # Trigger NEW values have no column affinity; compare projection numerically.
    import re
    return re.sub(r'\bprice_amount\b', 'CAST(price_amount AS NUMERIC)', sql)


def sqlite_shape(sql):
    # SQLite stores fixed-width exact decimal text; lexicographic range comparison
    # is exact even beyond IEEE-754 precision. PostgreSQL keeps native Numeric.
    sql = sql.replace('price_amount > 0', "price_amount > '00000000000000.0000'")
    sql = sql.replace('price_amount < 100000000000000', 'length(price_amount)=19')
    sql = sql.replace('price_max < 100000000000000', 'length(price_max)=19')
    for name in ('price_amount', 'price_max'):
        sql += f" AND ({name} IS NULL OR ({name} NOT GLOB '*[^0-9.]*' AND substr({name},15,1)='.' AND length(replace({name},'.',''))=18))"
    return '(' + sql + ')'


class ExactMoney(TypeDecorator):
    """Numeric(18,4) on PostgreSQL; exact sortable decimal text on SQLite."""
    impl = Numeric(18, 4)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(String(19) if dialect.name == 'sqlite' else Numeric(18,4))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = amount(value)
        return f'{value:019.4f}' if dialect.name == 'sqlite' else value

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


class CandidateMoney(TypeDecorator):
    """Keep the existing candidate schema; fail rather than round SQLite facts."""
    impl = Numeric(18,4)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = Decimal(str(value))
        if not value.is_finite() or value.as_tuple().exponent < -4:
            raise ValueError('Invalid candidate decimal precision')
        if dialect.name == 'sqlite' and Decimal(format(float(value), '.4f')) != value:
            raise ValueError('Exact candidate amount requires PostgreSQL; SQLite Numeric would round it')
        return value
