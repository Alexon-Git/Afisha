"""Worker attempts and immutable run provenance; never changes Event data."""
from alembic import op
import sqlalchemy as sa

revision = '0006_import_worker_integrity'
down_revision = '0005_import_schema'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # Fail before changing schema when previously stored provenance is invalid.
    invalid = bind.execute(sa.text('''SELECT count(*) FROM event_candidates c
        JOIN import_runs f ON f.id=c.first_run_id JOIN import_runs l ON l.id=c.last_run_id
        WHERE c.source_id<>f.source_id OR c.source_id<>l.source_id''')).scalar()
    if invalid:
        raise RuntimeError('Import provenance must be reconciled before migration')
    op.add_column('import_runs', sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'))
    if bind.dialect.name == 'postgresql':
        op.execute('''CREATE FUNCTION import_provenance_guard() RETURNS trigger AS $$
        BEGIN
          IF TG_TABLE_NAME = 'import_runs' THEN
            IF NEW.source_id <> OLD.source_id THEN
              RAISE EXCEPTION 'ImportRun source is immutable' USING ERRCODE='23514';
            END IF;
          ELSE
            IF NOT EXISTS (SELECT 1 FROM import_runs WHERE id=NEW.first_run_id AND source_id=NEW.source_id)
            OR NOT EXISTS (SELECT 1 FROM import_runs WHERE id=NEW.last_run_id AND source_id=NEW.source_id) THEN
              RAISE EXCEPTION 'Inconsistent import provenance' USING ERRCODE='23514';
            END IF;
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql''')
        op.execute('CREATE TRIGGER import_run_source_guard BEFORE UPDATE OF source_id ON import_runs FOR EACH ROW EXECUTE FUNCTION import_provenance_guard()')
        op.execute('CREATE TRIGGER import_candidate_provenance_guard BEFORE INSERT OR UPDATE OF source_id,first_run_id,last_run_id ON event_candidates FOR EACH ROW EXECUTE FUNCTION import_provenance_guard()')
    else:
        op.execute('''CREATE TRIGGER import_run_source_guard BEFORE UPDATE OF source_id ON import_runs
          WHEN NEW.source_id<>OLD.source_id BEGIN SELECT RAISE(ABORT,'ImportRun source is immutable'); END''')
        for action in ('INSERT', 'UPDATE OF source_id,first_run_id,last_run_id'):
            name = 'insert' if action == 'INSERT' else 'update'
            op.execute(f'''CREATE TRIGGER import_candidate_provenance_{name} BEFORE {action} ON event_candidates
            WHEN NOT EXISTS (SELECT 1 FROM import_runs WHERE id=NEW.first_run_id AND source_id=NEW.source_id)
            OR NOT EXISTS (SELECT 1 FROM import_runs WHERE id=NEW.last_run_id AND source_id=NEW.source_id)
            BEGIN SELECT RAISE(ABORT,'Inconsistent import provenance'); END''')


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('DROP TRIGGER import_candidate_provenance_guard ON event_candidates')
        op.execute('DROP TRIGGER import_run_source_guard ON import_runs')
        op.execute('DROP FUNCTION import_provenance_guard()')
    else:
        for name in ('import_run_source_guard', 'import_candidate_provenance_insert', 'import_candidate_provenance_update'):
            op.execute(f'DROP TRIGGER {name}')
    op.drop_column('import_runs', 'attempt_count')
