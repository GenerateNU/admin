"""branches

Revision ID: 87dd17a9cb8d
Revises: 4315ee2f32f5
Create Date: 2026-08-19 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "87dd17a9cb8d"
down_revision: str | None = "4315ee2f32f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = """
CREATE TABLE branch_drafts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT,
    icon_key    TEXT NOT NULL,
    color       TEXT NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_branch_drafts_position ON branch_drafts (position);

CREATE TABLE branches (
    id          UUID PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    icon_key    TEXT NOT NULL,
    color       TEXT NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_branches_position ON branches (position);
"""

DOWNGRADE = """
DROP TABLE IF EXISTS branches;
DROP TABLE IF EXISTS branch_drafts;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
