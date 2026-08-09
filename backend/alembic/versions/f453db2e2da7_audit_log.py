"""audit log

Revision ID: f453db2e2da7
Revises: 3ec5081bde0b
Create Date: 2026-08-08 22:53:05.480514
"""

from collections.abc import Sequence

from alembic import op


revision: str = 'f453db2e2da7'
down_revision: str | None = '3ec5081bde0b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = """
CREATE TABLE audit_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id      UUID,
    actor_email   VARCHAR(320),
    action        VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id   VARCHAR(128) NOT NULL,
    before        JSONB,
    after         JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_audit_logs_keyset ON audit_logs (created_at DESC, id DESC);
CREATE INDEX ix_audit_logs_actor ON audit_logs (actor_id, created_at DESC);
CREATE INDEX ix_audit_logs_resource ON audit_logs (resource_type, resource_id, created_at DESC);
"""

DOWNGRADE = """
DROP TABLE IF EXISTS audit_logs;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
