"""Initial relational schema.

Revision ID: 001
"""
from alembic import op
from migrations.schema_001 import db
revision='001'
down_revision=None
branch_labels=None
depends_on=None

def upgrade(): db.metadata.create_all(bind=op.get_bind())
def downgrade(): db.metadata.drop_all(bind=op.get_bind())
