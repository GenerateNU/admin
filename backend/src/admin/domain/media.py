from dataclasses import dataclass

from admin.core.storage import MediaVisibility
from admin.domain.enums import MediaPurpose


@dataclass(frozen=True, slots=True)
class MediaPreset:
    max_edge: int
    max_bytes: int
    visibility: MediaVisibility
    mime_types: frozenset[str]


PRESETS: dict[MediaPurpose, MediaPreset] = {
    MediaPurpose.AVATAR: MediaPreset(
        max_edge=512,
        max_bytes=1_048_576,
        visibility=MediaVisibility.PUBLIC,
        mime_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
    ),
    MediaPurpose.BRANCH_ICON: MediaPreset(
        max_edge=256,
        max_bytes=262_144,
        visibility=MediaVisibility.PUBLIC,
        mime_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
    ),
}


def preset_for(purpose: MediaPurpose) -> MediaPreset:
    return PRESETS[purpose]
