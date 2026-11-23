"""Preserved focused migration check. Use only a fresh isolated PG17.

Requires AFISHA_PR8_TEST_DATABASE_URL; creates new pr8_* schemas, never deletes
schemas/databases/volumes. No production URL is accepted by this harness.
"""
import os
from pathlib import Path
import secrets
import shutil
import tempfile
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config import settings

url = make_url(os.environ['AFISHA_PR8_TEST_DATABASE_URL'])
assert url.host == 'pr8db' and url.database == 'afisha_pr8' and url.username == 'pr8_test'
base = create_engine(url)
with base.connect() as connection:
    assert connection.execute(text('SHOW server_version_num')).scalar().startswith('17')

with tempfile.TemporaryDirectory() as temporary:
    scripts = Path(temporary) / 'alembic'
    shutil.copytree('/app/alembic', scripts)
    config = Config('/app/alembic.ini')
    config.set_main_option('script_location', str(scripts))
    for zone in ('UTC', 'Asia/Novosibirsk', 'Europe/Moscow', 'America/Los_Angeles'):
        for populated in (False, True):
            schema = 'pr8_' + secrets.token_hex(8)
            with base.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA {schema}'))
            scoped = url.update_query_dict({'options': f'-csearch_path={schema} -cTimeZone={zone}'})
            settings.database_url = scoped.render_as_string(hide_password=False)
            engine = create_engine(scoped)
            command.upgrade(config, '0003_event_metadata')
            with engine.begin() as connection:
                connection.execute(text("INSERT INTO users (username,password_hash,is_admin) VALUES ('fixture','not-a-real-hash',false)"))
                connection.execute(text("INSERT INTO categories (name,slug,is_active) VALUES ('Fixture','fixture',true)"))
                if populated:
                    connection.execute(text("INSERT INTO events (title,datetime,location) VALUES ('Historical fixture','2026-11-12 12:34:56','Fixture')"))
            if populated:
                try:
                    command.upgrade(config, 'head')
                except RuntimeError as error:
                    assert 'existing event datetimes' in str(error)
                else:
                    raise AssertionError('Populated table was converted')
                with engine.connect() as connection:
                    assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar() == '0003_event_metadata'
                    assert not next(c for c in inspect(connection).get_columns('events') if c['name']=='datetime')['type'].timezone
                    assert connection.execute(text('SELECT datetime FROM events')).scalar() == datetime(2026,11,12,12,34,56)
            else:
                command.upgrade(config, 'head')
                with engine.begin() as connection:
                    assert next(c for c in inspect(connection).get_columns('events') if c['name']=='datetime')['type'].timezone
                    assert connection.execute(text('SELECT count(*) FROM users')).scalar() == 1
                    assert connection.execute(text('SELECT count(*) FROM categories')).scalar() == 1
                    assert any(i['name']=='ix_events_datetime' for i in inspect(connection).get_indexes('events'))
                    connection.execute(text("INSERT INTO events (title,datetime,location) VALUES ('Offset fixture','2026-11-12T12:00:00+07:00','Fixture')"))
                    assert connection.execute(text('SELECT datetime FROM events')).scalar().astimezone(timezone.utc) == datetime(2026,11,12,5,tzinfo=timezone.utc)
                try:
                    command.downgrade(config, '-1')
                except RuntimeError as error:
                    assert 'backup/export' in str(error)
                else:
                    raise AssertionError('Unsafe downgrade accepted')
            engine.dispose()
            print('PASS migration',zone,'populated refusal' if populated else 'empty upgrade / aware storage / downgrade refusal',flush=True)
base.dispose()
