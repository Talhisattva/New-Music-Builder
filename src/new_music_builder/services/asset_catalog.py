from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class AssetEntry:
    key: str
    label: str
    inventory_path: str
    world_path: str
    sprite_mode: str = 'single'
    kind: str = ''


class AssetCatalog:
    def __init__(self, base_mod_root: Path) -> None:
        self.base_mod_root = base_mod_root
        self.textures_root = base_mod_root / 'Contents' / 'mods' / 'Talis New Music' / 'common' / 'media' / 'textures'

    def scan(self) -> dict[str, list[AssetEntry]]:
        categories = {
            'cassette': self._scan_pairs('Item_NM_Cassette', 'WorldItems/Cassette/World_NM_Cassette', kind='cassette', zero_pad=True),
            'vinyl': self._scan_pairs('Item_NM_Vinyl', 'WorldItems/Vinyl/World_NM_Vinyl', kind='vinyl'),
            'cd': [self._single('CD', 'Item_NM_CD.png', 'WorldItems/CD/World_NM_CD.png', kind='cd')],
            'case': self._scan_pairs('Item_NM_Case', 'WorldItems/Cassette/World_NM_CassetteCover', kind='case'),
            'jacket': self._scan_jackets(),
            'cd_cover': self._scan_cd_covers(),
        }
        return categories

    def _single(self, label: str, inv_rel: str, world_rel: str, kind: str) -> AssetEntry:
        return AssetEntry(
            key=label.lower(),
            label=label,
            inventory_path=str(self.textures_root / inv_rel),
            world_path=str(self.textures_root / world_rel),
            kind=kind,
        )

    def _scan_pairs(self, inv_prefix: str, world_prefix: str, *, kind: str, zero_pad: bool = False) -> list[AssetEntry]:
        entries: list[AssetEntry] = []
        for inv_path in sorted(self.textures_root.glob(f'{inv_prefix}*.png')):
            stem = inv_path.stem.removeprefix(inv_prefix)
            if not stem or stem.startswith('_'):
                continue
            if stem.lower() == 'zomboid':
                world_name = f'{world_prefix}_Zomboid.png'
                label = 'Zomboid'
            else:
                normalized = stem.zfill(2) if zero_pad and stem.isdigit() else stem
                world_name = f'{world_prefix}{normalized}.png'
                label = stem
            world_path = self.textures_root / world_name
            if world_path.exists():
                entries.append(AssetEntry(key=f'{kind}:{stem}', label=label, inventory_path=str(inv_path), world_path=str(world_path), kind=kind))
        return entries

    def _scan_jackets(self) -> list[AssetEntry]:
        entries: list[AssetEntry] = []
        for inv_path in sorted(self.textures_root.glob('Item_NM_Jacket*.png')):
            stem = inv_path.stem.removeprefix('Item_NM_Jacket')
            if not stem:
                continue
            lowered = stem.lower()
            sprite_mode = 'dual' if 'empty' in lowered else 'single'
            if lowered == '_zomboid':
                world_name = 'WorldItems/Vinyl/World_NM_Zomboid_Vinyl.png'
                label = 'Zomboid'
            elif lowered == '_zomboid_empty':
                world_name = 'WorldItems/Vinyl/World_NM_Zomboid_Vinyl_Empty.png'
                label = 'Zomboid Empty'
            elif lowered.endswith('_empty'):
                number = stem[:-6]
                world_name = f'WorldItems/Vinyl/World_NM_Cover{number}_Vinyl_Empty.png'
                label = f'{number} Empty'
            else:
                world_name = f'WorldItems/Vinyl/World_NM_Cover{stem}.png'
                vinyl_world_name = f'WorldItems/Vinyl/World_NM_Cover{stem}_Vinyl.png'
                label = stem
                if (self.textures_root / vinyl_world_name).exists():
                    world_name = vinyl_world_name
                    sprite_mode = 'dual'
            world_path = self.textures_root / world_name
            if world_path.exists():
                entries.append(AssetEntry(key=f'jacket:{stem}', label=label, inventory_path=str(inv_path), world_path=str(world_path), sprite_mode=sprite_mode, kind='jacket'))
        return entries

    def _scan_cd_covers(self) -> list[AssetEntry]:
        entries: list[AssetEntry] = []
        for inv_path in sorted(self.textures_root.glob('Item_NM_CDCover*.png')):
            stem = inv_path.stem.removeprefix('Item_NM_CDCover')
            if not stem:
                continue
            if stem == '_Blank':
                world_name = 'WorldItems/CD/World_NM_CDCover_Blank.png'
                label = 'Blank'
            elif stem == '_Empty':
                world_name = 'WorldItems/CD/World_NM_CDCover_Empty.png'
                label = 'Empty'
            elif stem == '_Zomboid':
                world_name = 'WorldItems/CD/World_NM_CDCover_Zomboid.png'
                label = 'Zomboid'
            else:
                world_name = f'WorldItems/CD/World_NM_CDCover{stem}.png'
                label = stem
            world_path = self.textures_root / world_name
            if world_path.exists():
                entries.append(AssetEntry(key=f'cd_cover:{stem}', label=label, inventory_path=str(inv_path), world_path=str(world_path), kind='cd_cover'))
        return entries