"""Add CRM journal and preserve existing demo tickets."""
from alembic import op
import sqlalchemy as sa

revision = 'a43bdc721e02'
down_revision = '2e28b5ac0a11'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('customers', sa.Column('loyalty_points', sa.Integer(), nullable=True))
    op.add_column('support_tickets', sa.Column('version', sa.Integer(), nullable=False, server_default='0'))
    op.create_table(
        'ticket_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('support_tickets.id'), nullable=False),
        sa.Column('operator_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('previous_status', sa.String(20)),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('ticket_version', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(36)),
        sa.Column('occurred_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('operator_id', 'request_id', name='ticket_event_request'),
        sa.UniqueConstraint('ticket_id', 'ticket_version', name='ticket_event_version'),
    )
    op.execute("""
        INSERT INTO ticket_events (ticket_id, operator_id, kind, status, ticket_version)
        SELECT id, operator_id, 'fixture', status, version FROM support_tickets
    """)
    op.execute("""
        UPDATE customers SET loyalty_points = 1250
        WHERE fictional = 1 AND demo_code = 'DEMO-CUSTOMER-005'
    """)


def downgrade():
    op.drop_table('ticket_events')
    op.drop_column('support_tickets', 'version')
    op.drop_column('customers', 'loyalty_points')
