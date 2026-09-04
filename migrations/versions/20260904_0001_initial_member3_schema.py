"""Create the initial privacy-safe Member 3 schema."""

from alembic import op
from asd_backend.db.models import Base

revision = "20260904_0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=True)
