"""media service

Revision ID: 4315ee2f32f5
Revises: ce8c0c720681
Create Date: 2026-08-14 21:54:24.487092
"""

from collections.abc import Sequence

from alembic import op

revision: str = "4315ee2f32f5"
down_revision: str | None = "ce8c0c720681"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = """
CREATE TABLE media (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id          UUID NOT NULL,
    s3_key            TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    mime_type         TEXT NOT NULL,
    size_bytes        BIGINT NOT NULL,
    purpose           TEXT NOT NULL,
    visibility        TEXT NOT NULL CHECK (visibility IN ('public', 'private')),
    status            TEXT NOT NULL,
    metadata          JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (id, visibility)
);

CREATE INDEX ix_media_owner ON media (owner_id, created_at DESC);

CREATE TABLE media_variants (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id     UUID NOT NULL,
    variant_type TEXT NOT NULL,
    s3_key       TEXT NOT NULL UNIQUE,
    mime_type    TEXT NOT NULL,
    size_bytes   BIGINT NOT NULL,
    visibility   TEXT NOT NULL,
    metadata     JSONB,
    status       TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    FOREIGN KEY (media_id, visibility) REFERENCES media (id, visibility) ON DELETE CASCADE,
    UNIQUE (media_id, variant_type)
);
"""

DOWNGRADE = """
DROP TABLE IF EXISTS media_variants;
DROP TABLE IF EXISTS media;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
