from pathlib import Path

from new_music_builder.services.asset_catalog import AssetCatalog


ASSETS_ROOT = Path(__file__).resolve().parents[1] / 'assets'


def test_asset_catalog_finds_expected_families() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()

    assert catalog['cassette']
    assert catalog['vinyl']
    assert catalog['cd']
    assert catalog['case']
    assert catalog['jacket']
    assert catalog['cd_cover']

    jacket_keys = {entry.key for entry in catalog['jacket']}
    assert 'jacket:19' in jacket_keys


def test_asset_catalog_places_preferred_cassette_and_case_entries_first() -> None:
    catalog = AssetCatalog(ASSETS_ROOT).scan()

    assert catalog['cassette'][0].key == 'cassette:7'
    assert catalog['case'][0].key == 'case:4'
