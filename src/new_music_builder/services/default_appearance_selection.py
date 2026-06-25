from __future__ import annotations


_PREFERRED_DEFAULT_ASSET_KEYS: dict[str, str] = {
    'cassette': 'cassette:7',
    'case': 'case:4',
}


def preferred_default_asset_key(kind: str, available_keys: set[str]) -> str:
    preferred_key = _PREFERRED_DEFAULT_ASSET_KEYS.get(kind, '')
    if preferred_key and preferred_key in available_keys:
        return preferred_key
    return ''
