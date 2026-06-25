from __future__ import annotations

from new_music_builder.domain.models import MediaRow


_PREFERRED_DEFAULT_ASSET_KEYS: dict[str, str] = {
    'cassette': 'cassette:7',
    'case': 'case:4',
}


def preferred_default_asset_key(kind: str, available_keys: set[str]) -> str:
    preferred_key = _PREFERRED_DEFAULT_ASSET_KEYS.get(kind, '')
    if preferred_key and preferred_key in available_keys:
        return preferred_key
    return ''


def apply_preferred_row_defaults(row: MediaRow) -> None:
    row.ensure_appearances()
    for kind, preferred_key in _PREFERRED_DEFAULT_ASSET_KEYS.items():
        selection = row.appearances[kind]
        if selection.selected_asset_key:
            continue
        selection.selected_asset_key = preferred_key
        selection.source = 'default'
        selection.sprite_mode = 'single'
