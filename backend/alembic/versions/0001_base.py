"""shared helpers every table builds on

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Attach to any table with an updated_at column:
--   CREATE TRIGGER trg_<table>_updated_at BEFORE UPDATE ON <table>
--       FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

DOWNGRADE = """
DROP FUNCTION IF EXISTS set_updated_at();
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
