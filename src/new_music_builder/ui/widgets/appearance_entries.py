from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from new_music_builder.domain.models import AppearanceKind, AppearanceSelection, MediaKind
from new_music_builder.services.asset_catalog import AssetEntry

PreviewMode = Literal['inventory', 'world']

TAB_KINDS: tuple[tuple[AppearanceKind, str], ...] = (
    ('cassette', 'Cassette'),
    ('vinyl', 'Vinyl'),
    ('cd', 'CD'),
    ('case', 'Case'),
    ('jacket', 'Jacket'),
    ('cd_cover', 'CD Case'),
)

DUAL_SPRITE_KINDS: frozenset[AppearanceKind] = frozenset({'case', 'jacket', 'cd_cover'})
MEDIA_TO_APPEARANCE_TABS: dict[MediaKind, tuple[AppearanceKind, AppearanceKind]] = {
    'cassette': ('cassette', 'case'),
    'vinyl': ('vinyl', 'jacket'),
    'cd': ('cd', 'cd_cover'),
}
BUILT_IN_DUAL_PAIRS: dict[str, str] = {
    'jacket:18': 'jacket:18_empty',
    'jacket:19': 'jacket:19_empty',
    'jacket:20': 'jacket:20_empty',
    'jacket:21': 'jacket:21_empty',
    'jacket:_Zomboid': 'jacket:_Zomboid_Empty',
    'cd_cover:_Blank': 'cd_cover:_Empty',
}
BUILT_IN_DUAL_EMPTY_TO_FULL: dict[str, str] = {empty_key: full_key for full_key, empty_key in BUILT_IN_DUAL_PAIRS.items()}


@dataclass(slots=True)
class AppearanceGridEntry:
    key: str
    label: str
    inventory_path: str
    world_path: str
    sprite_mode: str
    kind: AppearanceKind
    is_custom: bool = False
    is_generated: bool = False
    is_dual: bool = False
    inventory_empty_path: str = ''
    world_empty_path: str = ''

    def displayed_inventory_path(self, *, show_empty: bool) -> str:
        if self.is_dual and show_empty and self.inventory_empty_path:
            return self.inventory_empty_path
        return self.inventory_path

    def displayed_world_path(self, *, show_empty: bool) -> str:
        if self.is_dual and show_empty and self.world_empty_path:
            return self.world_empty_path
        return self.world_path

    def displayed_path(self, mode: PreviewMode, *, show_empty: bool) -> str:
        if mode == 'world':
            return self.displayed_world_path(show_empty=show_empty)
        return self.displayed_inventory_path(show_empty=show_empty)


def appearance_tab_order() -> tuple[tuple[AppearanceKind, str], ...]:
    return TAB_KINDS


def should_show_dual_sprite_controls(kind: AppearanceKind) -> bool:
    return kind in DUAL_SPRITE_KINDS


def visible_tab_kinds_for_enabled_media(enabled_media: dict[MediaKind, bool]) -> tuple[AppearanceKind, ...]:
    visible: list[AppearanceKind] = []
    for kind, _label in TAB_KINDS:
        for media_kind, mapped_tabs in MEDIA_TO_APPEARANCE_TABS.items():
            if kind in mapped_tabs and enabled_media.get(media_kind, False):
                visible.append(kind)
                break
    return tuple(visible)


def can_commit_single_custom(staged: dict[str, str]) -> bool:
    return bool(staged.get('inventory_full') and staged.get('world_full'))


def can_commit_dual_custom(staged: dict[str, str]) -> bool:
    return bool(
        staged.get('inventory_full')
        and staged.get('world_full')
        and staged.get('inventory_empty')
        and staged.get('world_empty')
    )


def merge_appearance_grid_entries(
    kind: AppearanceKind,
    defaults: list[AssetEntry],
    generated_entries: list[AppearanceGridEntry],
    custom_assets: list[dict[str, str]],
) -> list[AppearanceGridEntry]:
    merged: list[AppearanceGridEntry] = []
    defaults_by_key = {entry.key: entry for entry in defaults}
    consumed_default_keys: set[str] = set()
    for entry in defaults:
        if entry.key in consumed_default_keys:
            continue
        empty_pair_key = BUILT_IN_DUAL_PAIRS.get(entry.key)
        if empty_pair_key and empty_pair_key in defaults_by_key:
            empty_entry = defaults_by_key[empty_pair_key]
            merged.append(
                AppearanceGridEntry(
                    key=entry.key,
                    label=entry.label,
                    inventory_path=entry.inventory_path,
                    world_path=entry.world_path,
                    sprite_mode='dual',
                    kind=kind,
                    is_custom=False,
                    is_dual=True,
                    inventory_empty_path=empty_entry.inventory_path,
                    world_empty_path=empty_entry.world_path,
                )
            )
            consumed_default_keys.add(entry.key)
            consumed_default_keys.add(empty_pair_key)
            continue
        if entry.key in BUILT_IN_DUAL_EMPTY_TO_FULL:
            consumed_default_keys.add(entry.key)
            continue
        merged.append(
            AppearanceGridEntry(
                key=entry.key,
                label=entry.label,
                inventory_path=entry.inventory_path,
                world_path=entry.world_path,
                sprite_mode=entry.sprite_mode,
                kind=kind,
                is_custom=False,
            )
        )
    merged.extend(generated_entries)
    for index, asset in enumerate(custom_assets):
        inventory_path = asset.get('inventory_full', '')
        world_path = asset.get('world_full', '')
        key = asset.get('key', f'custom:{kind}:{index + 1}')
        label = asset.get('label') or inventory_path.rsplit('/', 1)[-1].rsplit('\\', 1)[-1] or f'Custom {index + 1}'
        sprite_mode = asset.get('sprite_mode', 'single') or 'single'
        is_dual = sprite_mode == 'dual' and bool(asset.get('inventory_empty') and asset.get('world_empty'))
        merged.append(
            AppearanceGridEntry(
                key=key,
                label=label,
                inventory_path=inventory_path,
                world_path=world_path,
                sprite_mode=sprite_mode,
                kind=kind,
                is_custom=True,
                is_dual=is_dual,
                inventory_empty_path=asset.get('inventory_empty', ''),
                world_empty_path=asset.get('world_empty', ''),
            )
        )
    return merged


def fallback_selected_asset_key_after_delete(
    entries: list[AppearanceGridEntry],
    *,
    deleted_key: str,
    selected_key: str,
) -> str:
    if selected_key != deleted_key:
        return selected_key
    return entries[0].key if entries else ''


def apply_selection_from_grid_entry(selection: AppearanceSelection, entry: AppearanceGridEntry) -> None:
    selection.selected_asset_key = entry.key
    selection.sprite_mode = entry.sprite_mode if should_show_dual_sprite_controls(entry.kind) else 'single'
    if entry.is_custom or entry.is_generated:
        selection.source = 'custom'
        selection.inventory_full = entry.inventory_path
        selection.world_full = entry.world_path
        selection.inventory_empty = entry.inventory_empty_path if entry.is_dual else ''
        selection.world_empty = entry.world_empty_path if entry.is_dual else ''
    else:
        selection.source = 'default'
        selection.inventory_full = ''
        selection.world_full = ''
        selection.inventory_empty = ''
        selection.world_empty = ''


def entry_for_selected_key(entries: list[AppearanceGridEntry], selected_key: str) -> AppearanceGridEntry | None:
    if not entries:
        return None
    return next((entry for entry in entries if entry.key == selected_key), entries[0])
