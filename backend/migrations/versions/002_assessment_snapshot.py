"""Assessment-bound workflow snapshots (also upgrades pre-migration demo databases)."""
from alembic import op
from sqlalchemy import inspect, Column, JSON
revision='002'
down_revision='001'
branch_labels=None
depends_on=None

def upgrade():
    columns={c['name'] for c in inspect(op.get_bind()).get_columns('risk_assessments')}
    if 'workflow_snapshot' not in columns: op.add_column('risk_assessments',Column('workflow_snapshot',JSON,nullable=True))

def downgrade(): op.drop_column('risk_assessments','workflow_snapshot')
