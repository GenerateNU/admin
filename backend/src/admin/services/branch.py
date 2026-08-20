import uuid

from admin.core.audit import AuditLog
from admin.core.errors import NotFoundError, ValidationError
from admin.core.storage import S3Storage
from admin.domain.enums import AuditAction
from admin.repositories.branch import BranchDraftRepository, BranchRepository
from admin.schemas.audit import AuditEntry
from admin.schemas.branch import (
    BranchDraftCreate,
    BranchDraftRead,
    BranchDraftRecord,
    BranchDraftUpdate,
    BranchPublishStatus,
    BranchRead,
    BranchRecord,
)
from admin.schemas.user import UserRead

RESOURCE_TYPE = "branch"

type BranchFingerprint = tuple[uuid.UUID, str, str | None, str, str]


class BranchService:
    def __init__(
        self,
        *,
        drafts: BranchDraftRepository,
        published: BranchRepository,
        storage: S3Storage,
        audit: AuditLog,
    ) -> None:
        self._drafts = drafts
        self._published = published
        self._storage = storage
        self._audit = audit

    async def list_drafts(self) -> list[BranchDraftRead]:
        return [self._to_draft_read(draft) for draft in await self._drafts.list_all()]

    async def list_published(self) -> list[BranchRead]:
        return [self._to_read(branch) for branch in await self._published.list_all()]

    async def create_draft(self, *, actor: UserRead, payload: BranchDraftCreate) -> BranchDraftRead:
        draft = await self._drafts.create(
            name=payload.name,
            description=payload.description,
            icon_key=payload.icon_key,
            color=payload.color,
            position=payload.position,
        )

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.BRANCH_DRAFT_CREATED,
                resource_type=RESOURCE_TYPE,
                resource_id=str(draft.id),
                after={"name": draft.name, "icon_key": draft.icon_key, "color": draft.color},
            )
        )
        return self._to_draft_read(draft)

    async def update_draft(
        self, *, actor: UserRead, branch_id: uuid.UUID, payload: BranchDraftUpdate
    ) -> BranchDraftRead:
        before = await self._require_draft(branch_id)

        updated = await self._drafts.update(
            branch_id,
            name=payload.name,
            description=payload.description,
            icon_key=payload.icon_key,
            color=payload.color,
            position=payload.position,
        )
        if updated is None:
            raise NotFoundError("branch draft does not exist")

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.BRANCH_DRAFT_UPDATED,
                resource_type=RESOURCE_TYPE,
                resource_id=str(branch_id),
                before={
                    "name": before.name,
                    "icon_key": before.icon_key,
                    "color": before.color,
                },
                after={
                    "name": updated.name,
                    "icon_key": updated.icon_key,
                    "color": updated.color,
                },
            )
        )
        return self._to_draft_read(updated)

    async def delete_draft(self, *, actor: UserRead, branch_id: uuid.UUID) -> None:
        before = await self._require_draft(branch_id)

        if not await self._drafts.delete(branch_id):
            raise NotFoundError("branch draft does not exist")

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.BRANCH_DRAFT_DELETED,
                resource_type=RESOURCE_TYPE,
                resource_id=str(branch_id),
                before={"name": before.name},
            )
        )

    async def reorder_drafts(
        self, *, actor: UserRead, ordered_ids: list[uuid.UUID]
    ) -> list[BranchDraftRead]:
        current_ids = {draft.id for draft in await self._drafts.list_all()}
        if len(ordered_ids) != len(current_ids) or set(ordered_ids) != current_ids:
            raise ValidationError(
                "reorder must include exactly the current set of branch drafts, no more, no less"
            )

        await self._drafts.reorder(ordered_ids)

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.BRANCH_DRAFTS_REORDERED,
                resource_type=RESOURCE_TYPE,
                resource_id="*",
                after={"order": [str(branch_id) for branch_id in ordered_ids]},
            )
        )
        return await self.list_drafts()

    async def publish_status(self) -> BranchPublishStatus:
        drafts = await self._drafts.list_all()
        published = await self._published.list_all()
        return BranchPublishStatus(
            is_dirty=self._fingerprint(drafts) != self._fingerprint(published),
            draft_count=len(drafts),
            published_count=len(published),
            last_published_at=await self._published.last_published_at(),
        )

    async def publish(self, *, actor: UserRead) -> list[BranchRead]:
        drafts = await self._drafts.list_all()
        before_count = len(await self._published.list_all())

        await self._published.replace_all(drafts)

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.BRANCHES_PUBLISHED,
                resource_type=RESOURCE_TYPE,
                resource_id="*",
                before={"count": before_count},
                after={"count": len(drafts)},
            )
        )
        return await self.list_published()

    async def discard_drafts(self, *, actor: UserRead) -> list[BranchDraftRead]:
        published = await self._published.list_all()
        before_count = len(await self._drafts.list_all())

        await self._drafts.replace_all(published)

        self._audit.add(
            AuditEntry(
                actor_id=actor.id,
                actor_email=actor.email,
                action=AuditAction.BRANCHES_DISCARDED,
                resource_type=RESOURCE_TYPE,
                resource_id="*",
                before={"count": before_count},
                after={"count": len(published)},
            )
        )
        return await self.list_drafts()

    async def _require_draft(self, branch_id: uuid.UUID) -> BranchDraftRecord:
        draft = await self._drafts.get_by_id(branch_id)
        if draft is None:
            raise NotFoundError("branch draft does not exist")
        return draft

    def _to_draft_read(self, record: BranchDraftRecord) -> BranchDraftRead:
        return BranchDraftRead(
            id=record.id,
            name=record.name,
            description=record.description,
            icon_key=record.icon_key,
            icon_url=self._storage.public_url(record.icon_key),
            color=record.color,
            position=record.position,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _to_read(self, record: BranchRecord) -> BranchRead:
        return BranchRead(
            id=record.id,
            name=record.name,
            description=record.description,
            icon_url=self._storage.public_url(record.icon_key),
            color=record.color,
            position=record.position,
        )

    @staticmethod
    def _fingerprint(
        items: list[BranchDraftRecord] | list[BranchRecord],
    ) -> list[BranchFingerprint]:
        return [(item.id, item.name, item.description, item.icon_key, item.color) for item in items]
