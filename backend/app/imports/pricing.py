"""Conservative JSON-LD offer facts: ambiguous tariffs require editorial review."""
from decimal import Decimal, InvalidOperation
from ..utils.currencies import CURRENCIES


def number(value):
    if isinstance(value, (bool, dict, list)):
        raise ValueError()
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError() from exc
    if not result.is_finite() or result < 0 or result >= Decimal('100000000000000') or result.as_tuple().exponent < -4:
        raise ValueError()
    return result


def offer_price(offers):
    if isinstance(offers, list):
        if not offers or len(offers) > 100 or not all(isinstance(offer, dict) for offer in offers):
            raise ValueError()
        parsed = [offer_price(offer) for offer in offers]
        if all(p[0] == 'free' for p in parsed):
            return 'free', Decimal(0), None, None
        if not all(p[0] == 'fixed' for p in parsed) or len({p[3] for p in parsed}) != 1:
            raise ValueError()
        low, high = min(p[1] for p in parsed), max(p[1] for p in parsed)
        return ('fixed', low, None, parsed[0][3]) if low == high else ('range', low, high, parsed[0][3])
    if not isinstance(offers, dict):
        raise ValueError()
    spec = offers.get('priceSpecification', offers)
    if not isinstance(spec, dict):
        raise ValueError()
    if 'priceSpecification' in offers and any(k in offers for k in ('price','lowPrice','highPrice','minPrice','maxPrice')):
        raise ValueError()  # Conflicting representations require an editor.
    if spec.get('priceCurrency') and offers.get('priceCurrency') and spec['priceCurrency'] != offers['priceCurrency']:
        raise ValueError()
    currency = spec.get('priceCurrency', offers.get('priceCurrency'))
    if currency is not None and currency not in CURRENCIES:
        raise ValueError()
    if 'price' in spec:
        if any(k in spec for k in ('lowPrice','highPrice','minPrice','maxPrice')):
            raise ValueError()
        low = number(spec['price'])
        if low == 0:
            return 'free', low, None, currency
        if currency is None:
            raise ValueError()
        return 'fixed', low, None, currency
    low = number(spec.get('lowPrice', spec.get('minPrice')))
    high_value = spec.get('highPrice', spec.get('maxPrice'))
    if low <= 0 or currency is None:
        raise ValueError()
    if high_value is None:
        return 'from', low, None, currency
    high = number(high_value)
    if high < low:
        raise ValueError()
    return 'range', low, high, currency


def normalized_price(raw, warnings):
    if 'offers' not in raw:
        return ('free', Decimal(0), None, None) if raw.get('isAccessibleForFree') is True else ('unknown', None, None, None)
    try:
        result = offer_price(raw['offers'])
        if (raw.get('isAccessibleForFree') is True and result[0] != 'free') or (raw.get('isAccessibleForFree') is False and result[0] == 'free'):
            raise ValueError()
        return result
    except (ValueError, TypeError):
        warnings.append('price_requires_review')
        return 'unknown', None, None, None
