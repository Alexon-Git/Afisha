"""Extract bounded factual Event records, never description/image/contact/HTML."""
from datetime import datetime
from decimal import Decimal
from html.parser import HTMLParser
import json
import re
import unicodedata
from urllib.parse import urljoin

from ..utils.event_time import as_utc
from .pricing import normalized_price
from .policy import ImportFailure, digest, safe_url

VERSION = 'jsonld-2'
TYPES = {'Event','BusinessEvent','ConferenceEvent','EducationEvent','SocialEvent'}


def clean(value, limit):
    if not isinstance(value,str):
        return None
    value = re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value)).strip()
    # Text-only facts; don't transfer markup into an Event.
    if '<' in value or '>' in value or len(value) > limit:
        return None
    return value or None


def key(value):
    return (value or '').casefold().replace('ё','е')


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.current = None
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type','').lower() == 'application/ld+json':
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.current is not None:
            self.scripts.append(''.join(self.current))
            self.current = None


def extract(body, content_type, source_url):
    if len(body) > 1_048_576:
        raise ImportFailure('response_too_large')
    try:
        text = body.decode('utf-8', errors='strict')
        if 'application/ld+json' in content_type or 'application/json' in content_type:
            scripts = [text]
        elif 'text/html' in content_type:
            parser = Scripts()
            parser.feed(text)
            scripts = parser.scripts
        else:
            raise ImportFailure('unsupported_content_type')
        result = []
        def walk(value, depth=0):
            if depth > 16:
                raise ImportFailure('jsonld_depth')
            if isinstance(value,list):
                if len(value) > 100:
                    raise ImportFailure('record_limit')
                for item in value:
                    walk(item, depth+1)
            elif isinstance(value,dict):
                types = value.get('@type',[])
                types = [types] if isinstance(types,str) else types
                if isinstance(types,list) and any(t in TYPES for t in types if isinstance(t,str)):
                    result.append(normalize(value,source_url))
                if '@graph' in value:
                    walk(value['@graph'],depth+1)
            if len(result) > 50:
                raise ImportFailure('record_limit')
        for script in scripts[:20]:
            walk(json.loads(script, parse_float=Decimal))
        if not result:
            raise ImportFailure('no_events')
        return result
    except (UnicodeError, ValueError, RecursionError):
        raise ImportFailure('invalid_jsonld') from None


def normalize(raw, source_url):
    warnings = []
    def url(value):
        if not isinstance(value,str):
            return None
        try:
            return safe_url(urljoin(source_url,value))
        except ImportFailure:
            warnings.append('invalid_url')
            return None
    title = clean(raw.get('name'),512)
    original = clean(raw.get('startDate'),255)
    start = None
    if original:
        try:
            start = as_utc(datetime.fromisoformat(original.replace('Z','+00:00')))
        except (ValueError, OverflowError):
            pass
    if raw.get('eventSchedule') is not None:
        start = None
        warnings.append('schedule_requires_review')
    if not start:
        warnings.append('ambiguous_time')
    end = None
    if raw.get('endDate') is not None:
        try:
            end = as_utc(datetime.fromisoformat(str(raw['endDate']).replace('Z','+00:00')))
            if start and end < start:
                raise ValueError()
        except (ValueError, OverflowError):
            end = None
            warnings.append('end_time_requires_review')
    location = raw.get('location')
    location = location if isinstance(location,dict) else {}
    address = location.get('address')
    address = address if isinstance(address,dict) else {}
    city = clean(address.get('addressLocality'),255)
    normalized_city = 'новосибирск' if key(city) in {'новосибирск','novosibirsk','г. новосибирск'} else None
    if not normalized_city:
        warnings.append('city_requires_review')
    organizer = raw.get('organizer')
    organizer = organizer if isinstance(organizer,dict) else {}
    price_kind, price, price_max, currency = normalized_price(raw, warnings)
    event_url = url(raw.get('url'))
    identity = url(raw.get('@id')) or event_url
    source_item_key = digest(identity or {'title':key(title),'start':original})
    data = dict(title=title, normalized_title=key(title), official_event_url=event_url,
        start_at=start, end_at=end, original_start=original, time_zone='UTC' if start else None,
        time_resolution='explicit_offset' if start else 'ambiguous',
        time_evidence={'kind':'explicit_offset' if start else 'unresolved'},
        city=city,normalized_city=normalized_city,venue_name=clean(location.get('name'),512),
        address=clean(address.get('streetAddress'),1024),organizer_name=clean(organizer.get('name'),255),
        organizer_url=url(organizer.get('url')),price_kind=price_kind,price_amount=price,price_max=price_max,currency=currency,
        proposed_event_status={'EventCancelled':'cancelled','EventPostponed':'postponed','EventScheduled':'scheduled'}.get(
            str(raw.get('eventStatus','')).rsplit('/',1)[-1]), warnings=warnings)
    if not title:
        warnings.append('missing_title')
    data['neutral_description'] = 'Деловое мероприятие. Сведения о времени и месте требуют редакторской проверки; регистрация — на сайте организатора.'
    data['field_provenance'] = {'adapter':VERSION,'url':source_url,'fields':['name','startDate','location','offers','organizer']}
    return dict(source_item_key=source_item_key, facts=data, fingerprint=digest(data))
