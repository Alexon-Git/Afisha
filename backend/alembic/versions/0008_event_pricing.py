"""Add exact event pricing; preserve legacy price and all event rows."""
from alembic import op
import sqlalchemy as sa
import re

revision = '0008_event_pricing'
down_revision = '0007_event_end_at'
branch_labels = None
depends_on = None

# Frozen SQL contract, independent of future application changes.
SHAPE = "price_kind IS NOT NULL AND (\n(price_kind IN ('unknown','free','by_request') AND price_amount IS NULL AND price_max IS NULL AND currency IS NULL)\nOR (price_kind IN ('fixed','from','range') AND price_amount IS NOT NULL AND price_amount > 0\nAND price_amount < 100000000000000 AND currency IS NOT NULL AND currency IN ('AED','AFN','ALL','AMD','AOA','ARS','AUD','AWG','AZN','BAM','BBD','BDT','BHD','BIF','BMD','BND','BOB','BOV','BRL','BSD','BTN','BWP','BYN','BZD','CAD','CDF','CHE','CHF','CHW','CLF','CLP','CNY','COP','COU','CRC','CUP','CVE','CZK','DJF','DKK','DOP','DZD','EGP','ERN','ETB','EUR','FJD','FKP','GBP','GEL','GHS','GIP','GMD','GNF','GTQ','GYD','HKD','HNL','HTG','HUF','IDR','ILS','INR','IQD','IRR','ISK','JMD','JOD','JPY','KES','KGS','KHR','KMF','KPW','KRW','KWD','KYD','KZT','LAK','LBP','LKR','LRD','LSL','LYD','MAD','MDL','MGA','MKD','MMK','MNT','MOP','MRU','MUR','MVR','MWK','MXN','MXV','MYR','MZN','NAD','NGN','NIO','NOK','NPR','NZD','OMR','PAB','PEN','PGK','PHP','PKR','PLN','PYG','QAR','RON','RSD','RUB','RWF','SAR','SBD','SCR','SDG','SEK','SGD','SHP','SLE','SOS','SRD','SSP','STN','SVC','SYP','SZL','THB','TJS','TMT','TND','TOP','TRY','TTD','TWD','TZS','UAH','UGX','USD','USN','UYI','UYU','UYW','UZS','VED','VES','VND','VUV','WST','XAD','XAF','XAG','XAU','XBA','XBB','XBC','XBD','XCD','XCG','XDR','XOF','XPD','XPF','XPT','XSU','XTS','XUA','XXX','YER','ZAR','ZMW','ZWG')\nAND ((price_kind IN ('fixed','from') AND price_max IS NULL)\nOR (price_kind='range' AND price_max IS NOT NULL AND price_max >= price_amount AND price_max < 100000000000000))))"
SQLITE_SHAPE = "(price_kind IS NOT NULL AND (\n(price_kind IN ('unknown','free','by_request') AND price_amount IS NULL AND price_max IS NULL AND currency IS NULL)\nOR (price_kind IN ('fixed','from','range') AND price_amount IS NOT NULL AND price_amount > '00000000000000.0000'\nAND length(price_amount)=19 AND currency IS NOT NULL AND currency IN ('AED','AFN','ALL','AMD','AOA','ARS','AUD','AWG','AZN','BAM','BBD','BDT','BHD','BIF','BMD','BND','BOB','BOV','BRL','BSD','BTN','BWP','BYN','BZD','CAD','CDF','CHE','CHF','CHW','CLF','CLP','CNY','COP','COU','CRC','CUP','CVE','CZK','DJF','DKK','DOP','DZD','EGP','ERN','ETB','EUR','FJD','FKP','GBP','GEL','GHS','GIP','GMD','GNF','GTQ','GYD','HKD','HNL','HTG','HUF','IDR','ILS','INR','IQD','IRR','ISK','JMD','JOD','JPY','KES','KGS','KHR','KMF','KPW','KRW','KWD','KYD','KZT','LAK','LBP','LKR','LRD','LSL','LYD','MAD','MDL','MGA','MKD','MMK','MNT','MOP','MRU','MUR','MVR','MWK','MXN','MXV','MYR','MZN','NAD','NGN','NIO','NOK','NPR','NZD','OMR','PAB','PEN','PGK','PHP','PKR','PLN','PYG','QAR','RON','RSD','RUB','RWF','SAR','SBD','SCR','SDG','SEK','SGD','SHP','SLE','SOS','SRD','SSP','STN','SVC','SYP','SZL','THB','TJS','TMT','TND','TOP','TRY','TTD','TWD','TZS','UAH','UGX','USD','USN','UYI','UYU','UYW','UZS','VED','VES','VND','VUV','WST','XAD','XAF','XAG','XAU','XBA','XBB','XBC','XBD','XCD','XCG','XDR','XOF','XPD','XPF','XPT','XSU','XTS','XUA','XXX','YER','ZAR','ZMW','ZWG')\nAND ((price_kind IN ('fixed','from') AND price_max IS NULL)\nOR (price_kind='range' AND price_max IS NOT NULL AND price_max >= price_amount AND length(price_max)=19)))) AND (price_amount IS NULL OR (price_amount NOT GLOB '*[^0-9.]*' AND substr(price_amount,15,1)='.' AND length(replace(price_amount,'.',''))=18)) AND (price_max IS NULL OR (price_max NOT GLOB '*[^0-9.]*' AND substr(price_max,15,1)='.' AND length(replace(price_max,'.',''))=18)))"
SQLITE_COMPAT = "(\n(price_kind='free' AND price IS NOT NULL AND price=0)\nOR (price_kind='fixed' AND currency='RUB' AND CAST(price_amount AS NUMERIC)=CAST(CAST(price_amount AS NUMERIC) AS BIGINT)\nAND CAST(price_amount AS NUMERIC)<=2147483647 AND price IS NOT NULL AND price=CAST(price_amount AS NUMERIC))\nOR (price IS NULL AND (price_kind IN ('unknown','from','range','by_request')\nOR (price_kind='fixed' AND (currency<>'RUB' OR CAST(price_amount AS NUMERIC)<>CAST(CAST(price_amount AS NUMERIC) AS BIGINT) OR CAST(price_amount AS NUMERIC)>2147483647)))))"
COMPAT = "(\n(price_kind='free' AND price IS NOT NULL AND price=0)\nOR (price_kind='fixed' AND currency='RUB' AND price_amount=CAST(price_amount AS BIGINT)\nAND price_amount<=2147483647 AND price IS NOT NULL AND price=price_amount)\nOR (price IS NULL AND (price_kind IN ('unknown','from','range','by_request')\nOR (price_kind='fixed' AND (currency<>'RUB' OR price_amount<>CAST(price_amount AS BIGINT) OR price_amount>2147483647)))))"


def upgrade():
    db = op.get_bind()
    if db.dialect.name == 'postgresql':
        db.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
        db.execute(sa.text('LOCK TABLE events IN ACCESS EXCLUSIVE MODE'))
    elif db.dialect.name == 'sqlite' and not db.connection.driver_connection.in_transaction:
        db.exec_driver_sql('BEGIN IMMEDIATE')
    if db.execute(sa.text('SELECT count(*) FROM events WHERE price < 0 OR price > 2147483647')).scalar():
        raise RuntimeError('Invalid legacy prices; review manually before migration')
    if db.dialect.name == 'sqlite' and db.execute(sa.text("SELECT count(*) FROM events WHERE price IS NOT NULL AND typeof(price)<>'integer'")).scalar():
        raise RuntimeError('Non-integer legacy price; review manually before migration')
    money = sa.String(19) if db.dialect.name == 'sqlite' else sa.Numeric(18,4)
    op.add_column('events', sa.Column('price_amount', money, nullable=True))
    op.add_column('events', sa.Column('price_max', money, nullable=True))
    op.add_column('events', sa.Column('currency', sa.String(3), nullable=True))
    # Inline shape CHECK permits additive SQLite DDL, without rebuilding events.
    op.add_column('events', sa.Column('price_kind', sa.String(16), sa.CheckConstraint(SQLITE_SHAPE if db.dialect.name == 'sqlite' else SHAPE, name='ck_events_pricing_shape'),
                                    nullable=False, server_default='unknown'))
    amount = "printf('%014d.0000',price)" if db.dialect.name == 'sqlite' else 'price'
    db.execute(sa.text(f"""UPDATE events SET price_kind=CASE WHEN price IS NULL THEN 'unknown'
      WHEN price=0 THEN 'free' ELSE 'fixed' END,
      price_amount=CASE WHEN price>0 THEN {amount} ELSE NULL END,
      currency=CASE WHEN price>0 THEN 'RUB' ELSE NULL END"""))
    if db.dialect.name == 'postgresql':
        op.create_check_constraint('ck_events_pricing_compat', 'events', COMPAT)
    else:
        # SQLite cannot ALTER ADD table CHECK. Equivalent aborting triggers avoid
        # a table rebuild (and preserve incoming FKs/import history).
        expression = re.sub(r'\b(price_kind|price_amount|price_max|currency|price)\b', lambda m: 'NEW.'+m[0], SQLITE_COMPAT)
        for action in ('INSERT','UPDATE'):
            db.exec_driver_sql(f"CREATE TRIGGER ck_events_pricing_compat_{action.lower()} BEFORE {action} ON events "
                               f"WHEN NOT ({expression}) BEGIN SELECT RAISE(ABORT,'Conflicting event prices'); END")


def downgrade():
    db = op.get_bind()
    if db.dialect.name == 'postgresql':
        op.drop_constraint('ck_events_pricing_compat', 'events', type_='check')
    else:
        for action in ('insert','update'):
            db.exec_driver_sql(f'DROP TRIGGER ck_events_pricing_compat_{action}')
    # Destructive for structured prices; requires a separately approved backup.
    for column in ('price_kind','currency','price_max','price_amount'):
        op.drop_column('events', column)
