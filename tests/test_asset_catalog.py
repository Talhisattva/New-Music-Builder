from pathlib import Path

from new_music_builder.services.asset_catalog import AssetCatalog


BASE_MOD = Path(r'C:\Users\chowl\Zomboid\Workshop\Talis New Music')


def test_asset_catalog_finds_expected_families() -> None:
    catalog = AssetCatalog(BASE_MOD).scan()

    assert catalog['cassette']
    assert catalog['vinyl']
    assert catalog['cd']
    assert catalog['case']
    assert catalog['jacket']
    assert catalog['cd_cover']

    jacket_keys = {entry.key for entry in catalog['jacket']}
    assert 'jacket:19' in jacket_keys