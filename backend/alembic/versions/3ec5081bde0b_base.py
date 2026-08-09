"""base

Revision ID: 3ec5081bde0b
Revises: 
Create Date: 2026-08-08 22:51:50.576882
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '3ec5081bde0b'
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
