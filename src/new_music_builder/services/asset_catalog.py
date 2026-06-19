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
    def __init__(self, assets_root: Path) -> None:
        self.assets_root = assets_root
        self.inventory_root = assets_root / 'Inventory'
        self.world_root = assets_root / 'World'

    def scan(self) -> dict[str, list[AssetEntry]]:
        categories = {
            'cassette': self._scan_pairs('Cassette', 'Item_NM_Cassette', 'Cassette', 'World_NM_Cassette', kind='cassette', zero_pad=True),
            'vinyl': self._scan_pairs('Vinyl', 'Item_NM_Vinyl', 'Vinyl', 'World_NM_Vinyl', kind='vinyl'),
            'cd': [self._single('CD', 'CD', 'Item_NM_CD.png', 'CD', 'World_NM_CD.png', kind='cd')],
            'case': self._scan_pairs('CassetteCase', 'Item_NM_Case', 'CassetteCase', 'World_NM_CassetteCover', kind='case'),
            'jacket': self._scan_jackets(),
            'cd_cover': self._scan_cd_covers(),
        }
        return categories

    def _single(self, label: str, inv_dir: str, inv_name: str, world_dir: str, world_name: str, kind: str) -> AssetEntry:
        return AssetEntry(
            key=label.lower(),
            label=label,
            inventory_path=str(self.inventory_root / inv_dir / inv_name),
            world_path=str(self.world_root / world_dir / world_name),
            kind=kind,
        )

    def _scan_pairs(
        self,
        inv_dir: str,
        inv_prefix: str,
        world_dir: str,
        world_prefix: str,
        *,
        kind: str,
        zero_pad: bool = False,
    ) -> list[AssetEntry]:
        entries: list[AssetEntry] = []
        inventory_dir = self.inventory_root / inv_dir
        world_dir_path = self.world_root / world_dir
        for inv_path in sorted(inventory_dir.glob(f'{inv_prefix}*.png')):
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
            world_path = world_dir_path / world_name
            if world_path.exists():
                entries.append(AssetEntry(key=f'{kind}:{stem}', label=label, inventory_path=str(inv_path), world_path=str(world_path), kind=kind))
        return entries

    def _scan_jackets(self) -> list[AssetEntry]:
        entries: list[AssetEntry] = []
        inventory_dir = self.inventory_root / 'VinylJacket'
        world_dir = self.world_root / 'VinylJacket'
        for inv_path in sorted(inventory_dir.glob('Item_NM_Jacket*.png')):
            stem = inv_path.stem.removeprefix('Item_NM_Jacket')
            if not stem:
                continue
            lowered = stem.lower()
            sprite_mode = 'dual' if 'empty' in lowered else 'single'
            if lowered == '_zomboid':
                world_name = 'World_NM_Zomboid_Vinyl.png'
                label = 'Zomboid'
            elif lowered == '_zomboid_empty':
                world_name = 'World_NM_Zomboid_Vinyl_Empty.png'
                label = 'Zomboid Empty'
            elif lowered.endswith('_empty'):
                number = stem[:-6]
                world_name = f'World_NM_Cover{number}_Vinyl_Empty.png'
                label = f'{number} Empty'
            else:
                world_name = f'World_NM_Cover{stem}.png'
                vinyl_world_name = f'World_NM_Cover{stem}_Vinyl.png'
                label = stem
                if (world_dir / vinyl_world_name).exists():
                    world_name = vinyl_world_name
                    sprite_mode = 'dual'
            world_path = world_dir / world_name
            if world_path.exists():
                entries.append(AssetEntry(key=f'jacket:{stem}', label=label, inventory_path=str(inv_path), world_path=str(world_path), sprite_mode=sprite_mode, kind='jacket'))
        return entries

    def _scan_cd_covers(self) -> list[AssetEntry]:
        entries: list[AssetEntry] = []
        inventory_dir = self.inventory_root / 'CDCover'
        world_dir = self.world_root / 'CDCover'
        for inv_path in sorted(inventory_dir.glob('Item_NM_CDCover*.png')):
            stem = inv_path.stem.removeprefix('Item_NM_CDCover')
            if not stem:
                continue
            if stem == '_Blank':
                world_name = 'World_NM_CDCover_Blank.png'
                label = 'Blank'
            elif stem == '_Empty':
                world_name = 'World_NM_CDCover_Empty.png'
                label = 'Empty'
            elif stem == '_Zomboid':
                world_name = 'World_NM_CDCover_Zomboid.png'
                label = 'Zomboid'
            else:
                world_name = f'World_NM_CDCover{stem}.png'
                label = stem
            world_path = world_dir / world_name
            if world_path.exists():
                entries.append(AssetEntry(key=f'cd_cover:{stem}', label=label, inventory_path=str(inv_path), world_path=str(world_path), kind='cd_cover'))
        return entries
