"""Reject published answer keys without a verified source; retire invalidated keys."""
from alembic import op

revision = '2e28b5ac0a11'
down_revision = '1ac65be8494f'
branch_labels = None
depends_on = None

def upgrade():
    for action in ('INSERT','UPDATE'):
        op.execute(f"""CREATE TRIGGER question_source_guard_{action.lower()}
        BEFORE {action} ON questions
        WHEN NEW.review_status = 'published'
        BEGIN
          SELECT CASE WHEN NOT EXISTS (
            SELECT 1 FROM verified_facts f JOIN source_documents d ON f.source_id=d.id
            WHERE f.id=NEW.fact_id AND f.status='verified'
              AND f.needs_trainer_confirmation=0 AND length(trim(f.locator))>0
              AND length(trim(d.filename))>0
          ) OR length(trim(NEW.explanation))=0 OR NEW.correct_answer IN ('null','{{}}')
          THEN RAISE(ABORT, 'Published questions require verified source and answer key') END;
        END""")
    op.execute("""CREATE TRIGGER retire_invalidated_questions
    AFTER UPDATE OF status, needs_trainer_confirmation ON verified_facts
    WHEN NEW.status != 'verified' OR NEW.needs_trainer_confirmation != 0
    BEGIN
      UPDATE questions SET review_status='retired'
      WHERE fact_id=NEW.id AND review_status='published';
    END""")

def downgrade():
    op.execute('DROP TRIGGER retire_invalidated_questions')
    op.execute('DROP TRIGGER question_source_guard_update')
    op.execute('DROP TRIGGER question_source_guard_insert')
