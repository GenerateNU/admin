"""rbac

Revision ID: ce8c0c720681
Revises: f453db2e2da7
Create Date: 2026-08-08 22:53:34.662744
"""

from collections.abc import Sequence

from alembic import op

revision: str = "ce8c0c720681"
down_revision: str | None = "f453db2e2da7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE = """
CREATE TABLE permissions (
    key         VARCHAR(128) PRIMARY KEY,
    description VARCHAR(255) NOT NULL
);

CREATE TABLE roles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key        VARCHAR(64) NOT NULL UNIQUE,
    name       VARCHAR(120) NOT NULL,
    is_system  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE role_permissions (
    role_id        UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_key VARCHAR(128) NOT NULL REFERENCES permissions(key) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_key)
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entra_object_id UUID NOT NULL UNIQUE,
    email           VARCHAR(320) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    status          VARCHAR(64) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended')),
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_users_email ON users (email);

CREATE TABLE user_roles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id    UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id) ON DELETE SET NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    UNIQUE (user_id, role_id)
);

CREATE INDEX ix_user_roles_user_id ON user_roles (user_id);

CREATE TABLE invitations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(320) NOT NULL,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,
    invited_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_invitations_email ON invitations (email);

CREATE UNIQUE INDEX uq_invitations_open_email ON invitations (email)
    WHERE accepted_at IS NULL AND revoked_at IS NULL;

CREATE TABLE access_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) NOT NULL,
    entra_object_id UUID NOT NULL,
    name            VARCHAR(200) NOT NULL,
    message         VARCHAR(1000),
    status          VARCHAR(64) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'denied')),
    reviewed_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at     TIMESTAMPTZ,
    decision_note   VARCHAR(1000),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_access_requests_email ON access_requests (email);

CREATE UNIQUE INDEX uq_access_requests_open_email ON access_requests (email)
    WHERE status = 'pending';

ALTER TABLE audit_logs
    ADD CONSTRAINT fk_audit_logs_actor
    FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL;

CREATE TRIGGER trg_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_invitations_updated_at BEFORE UPDATE ON invitations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_access_requests_updated_at BEFORE UPDATE ON access_requests
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
"""

DOWNGRADE = """
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS fk_audit_logs_actor;
DROP TABLE IF EXISTS access_requests;
DROP TABLE IF EXISTS invitations;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS permissions;
"""


def upgrade() -> None:
    op.execute(UPGRADE)


def downgrade() -> None:
    op.execute(DOWNGRADE)
