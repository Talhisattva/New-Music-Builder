from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_SEARCH_URL = "https://api.spotify.com/v1/search"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_MIN_PER_ARTIST = 1
_DEFAULT_MAX_PER_ARTIST = 3
_DEFAULT_RETRY_COUNT = 3
_REQUEST_PAUSE_SECONDS = 0.02
_DEFAULT_PROGRESS_EVERY = 25
_DEFAULT_MAX_NEW_LOOKUPS = 100
_TITLE_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_BRACKETED_TEXT_RE = re.compile(r"\s*[\(\[].*?[\)\]]")
_FEAT_SPLIT_RE = re.compile(r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE)


@dataclass(slots=True)
class TrackRow:
    index: int
    display_label: str
    artist: str
    title: str
    duration: str
    source_path: str
    raw: dict[str, Any]


@dataclass(slots=True)
class SpotifyMatch:
    spotify_id: str = ""
    spotify_name: str = ""
    spotify_artists: str = ""
    popularity: int = -1
    url: str = ""
    match_score: float = 0.0
    matched: bool = False
    note: str = ""


@dataclass(slots=True)
class RankedTrack:
    row: TrackRow
    match: SpotifyMatch
    keep_for_lf: bool = False
    keep_reason: str = ""
    artist_rank: int = 0


class LookupLimitReached(Exception):
    pass


class SpotifyQuotaExceeded(Exception):
    pass


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = ""
        self._access_token_expiry = 0.0

    def search_track(self, artist: str, title: str) -> SpotifyMatch:
        query = f'track:"{title}" artist:"{artist}"'
        payload = self._get_json(
            _SEARCH_URL,
            query={
                "q": query,
                "type": "track",
                "limit": "10",
                "market": "US",
            },
            use_bearer=True,
        )
        candidates = payload.get("tracks", {}).get("items", [])
        if not candidates:
            return SpotifyMatch(note="no_spotify_match")

        best = self._pick_best_match(artist=artist, title=title, candidates=candidates)
        if best is None:
            return SpotifyMatch(note="no_ranked_match")
        return best

    def _pick_best_match(self, *, artist: str, title: str, candidates: list[dict[str, Any]]) -> SpotifyMatch | None:
        wanted_artist = _normalize_artist(artist)
        wanted_title = _normalize_title(title)
        best: SpotifyMatch | None = None
        best_score = -1.0
        for candidate in candidates:
            spotify_name = str(candidate.get("name", "")).strip()
            spotify_artists = [str(item.get("name", "")).strip() for item in candidate.get("artists", [])]
            normalized_title = _normalize_title(spotify_name)
            normalized_artists = [_normalize_artist(name) for name in spotify_artists]
            title_score = _string_similarity(wanted_title, normalized_title)
            artist_score = max((_string_similarity(wanted_artist, name) for name in normalized_artists), default=0.0)
            score = (title_score * 0.75) + (artist_score * 0.25)
            if score > best_score:
                best_score = score
                best = SpotifyMatch(
                    spotify_id=str(candidate.get("id", "")).strip(),
                    spotify_name=spotify_name,
                    spotify_artists="; ".join(spotify_artists),
                    popularity=int(candidate.get("popularity", -1) or -1),
                    url=str(candidate.get("external_urls", {}).get("spotify", "")).strip(),
                    match_score=round(score, 4),
                    matched=score >= 0.55,
                    note="matched" if score >= 0.55 else "low_confidence_match",
                )
        return best

    def _get_json(
        self,
        url: str,
        *,
        query: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
        use_bearer: bool,
    ) -> dict[str, Any]:
        target = url
        if query:
            target = f"{url}?{urllib.parse.urlencode(query)}"

        data: bytes | None = None
        headers: dict[str, str] = {}
        if form is not None:
            data = urllib.parse.urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        if use_bearer:
            headers["Authorization"] = f"Bearer {self._get_access_token()}"
        else:
            auth_bytes = f"{self._client_id}:{self._client_secret}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(auth_bytes).decode('ascii')}"

        request = urllib.request.Request(target, data=data, headers=headers, method="POST" if data else "GET")
        for attempt in range(1, _DEFAULT_RETRY_COUNT + 1):
            try:
                with urllib.request.urlopen(request, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < _DEFAULT_RETRY_COUNT:
                    retry_after = exc.headers.get("Retry-After")
                    delay = min(5.0, float(retry_after) if retry_after else 0.75)
                    time.sleep(delay)
                    continue
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and "QUOTA_EXCEEDED" in body:
                    raise SpotifyQuotaExceeded("Spotify API quota exceeded for this app.") from exc
                raise RuntimeError(f"Spotify API request failed: {exc.code} {body}") from exc
            except urllib.error.URLError as exc:
                if attempt < _DEFAULT_RETRY_COUNT:
                    time.sleep(0.5 * attempt)
                    continue
                raise RuntimeError(f"Spotify API request failed: {exc}") from exc
        raise RuntimeError("Spotify API request failed after retries")

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._access_token_expiry:
            return self._access_token
        payload = self._get_json(
            _TOKEN_URL,
            form={"grant_type": "client_credentials"},
            use_bearer=False,
        )
        self._access_token = str(payload.get("access_token", "")).strip()
        expires_in = int(payload.get("expires_in", 3600) or 3600)
        self._access_token_expiry = time.time() + max(60, expires_in - 60)
        if not self._access_token:
            raise RuntimeError("Spotify token response did not include an access token")
        return self._access_token


def _normalize_title(value: str) -> str:
    lowered = _FEAT_SPLIT_RE.split(value, maxsplit=1)[0]
    lowered = _BRACKETED_TEXT_RE.sub("", lowered).lower()
    return _TITLE_NORMALIZE_RE.sub("", lowered)


def _normalize_artist(value: str) -> str:
    lowered = _FEAT_SPLIT_RE.split(value, maxsplit=1)[0].lower()
    return _TITLE_NORMALIZE_RE.sub("", lowered)


def _string_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    max_len = max(len(left), len(right))
    if max_len == 0:
        return 1.0
    overlap = _longest_common_subsequence_length(left, right)
    return overlap / max_len


def _longest_common_subsequence_length(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = [0] * (len(right) + 1)
    for left_char in left:
        current = [0]
        for index, right_char in enumerate(right, start=1):
            if left_char == right_char:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def _read_tracks(project_path: Path) -> tuple[dict[str, Any], list[TrackRow]]:
    payload = json.loads(project_path.read_text(encoding="utf-8-sig"))
    row = payload["media_rows"][0]
    tracks: list[TrackRow] = []
    for index, track in enumerate(row.get("tracks_a", []), start=1):
        label = str(track.get("display_label", "")).strip()
        artist, title = _split_artist_and_title(label)
        tracks.append(
            TrackRow(
                index=index,
                display_label=label,
                artist=artist,
                title=title,
                duration=str(track.get("duration", "")).strip(),
                source_path=str(track.get("source_path", "")).strip(),
                raw=track,
            )
        )
    return payload, tracks


def _split_artist_and_title(label: str) -> tuple[str, str]:
    if " - " in label:
        artist, title = label.split(" - ", 1)
        return artist.strip(), title.strip()
    return label.strip(), label.strip()


def _rank_tracks(
    tracks: list[TrackRow],
    *,
    min_per_artist: int,
    max_per_artist: int,
    spotify_client: SpotifyClient,
    cache_path: Path,
    progress_every: int,
    max_new_lookups: int,
) -> list[RankedTrack]:
    ranked: list[RankedTrack] = []
    tracks_by_artist: dict[str, list[TrackRow]] = {}
    for track in tracks:
        tracks_by_artist.setdefault(track.artist, []).append(track)

    cache = _load_cache(cache_path)
    total_tracks = len(tracks)
    processed = 0
    cache_hits = 0
    cache_writes_since_flush = 0
    matched_count = 0
    new_lookups = 0

    try:
        for artist, artist_tracks in tracks_by_artist.items():
            artist_ranked: list[RankedTrack] = []
            for track in artist_tracks:
                cache_key = _cache_key(track.artist, track.title)
                cached = cache.get(cache_key)
                if isinstance(cached, dict):
                    match = _spotify_match_from_dict(cached)
                    cache_hits += 1
                else:
                    if new_lookups >= max_new_lookups:
                        raise LookupLimitReached
                    match = spotify_client.search_track(track.artist, track.title)
                    cache[cache_key] = _spotify_match_to_dict(match)
                    cache_writes_since_flush += 1
                    new_lookups += 1
                    if cache_writes_since_flush >= progress_every:
                        _save_cache(cache_path, cache)
                        cache_writes_since_flush = 0
                artist_ranked.append(RankedTrack(row=track, match=match))
                processed += 1
                if match.matched:
                    matched_count += 1
                if processed % max(1, progress_every) == 0 or processed == total_tracks:
                    print(
                        f"[progress] {processed}/{total_tracks} tracks, cache_hits={cache_hits}, new_lookups={new_lookups}, matched={matched_count}",
                        flush=True,
                    )
                if cached is None:
                    time.sleep(_REQUEST_PAUSE_SECONDS)

            artist_ranked.sort(
                key=lambda item: (
                    item.match.popularity,
                    item.match.match_score,
                    item.row.title.lower(),
                ),
                reverse=True,
            )
            keep_count = _recommended_keep_count(
                artist_track_count=len(artist_ranked),
                min_per_artist=min_per_artist,
                max_per_artist=max_per_artist,
            )
            for index, item in enumerate(artist_ranked, start=1):
                item.artist_rank = index
                item.keep_for_lf = index <= keep_count
                item.keep_reason = "kept_by_artist_quota" if item.keep_for_lf else "trimmed_by_artist_quota"
                if not item.match.matched:
                    item.keep_reason = "kept_unmatched_fallback" if item.keep_for_lf else "trimmed_unmatched_fallback"
            ranked.extend(artist_ranked)
    finally:
        if cache_writes_since_flush:
            _save_cache(cache_path, cache)
    ranked.sort(key=lambda item: item.row.index)
    return ranked


def _cache_key(artist: str, title: str) -> str:
    return f"{_normalize_artist(artist)}::{_normalize_title(title)}"


def _load_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    if not cache_path.exists():
        return {}
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return {str(key): value for key, value in payload.items() if isinstance(value, dict)}
    except Exception:
        pass
    return {}


def _save_cache(cache_path: Path, cache: dict[str, dict[str, Any]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _spotify_match_to_dict(match: SpotifyMatch) -> dict[str, Any]:
    return {
        "spotify_id": match.spotify_id,
        "spotify_name": match.spotify_name,
        "spotify_artists": match.spotify_artists,
        "popularity": match.popularity,
        "url": match.url,
        "match_score": match.match_score,
        "matched": match.matched,
        "note": match.note,
    }


def _spotify_match_from_dict(data: dict[str, Any]) -> SpotifyMatch:
    return SpotifyMatch(
        spotify_id=str(data.get("spotify_id", "")),
        spotify_name=str(data.get("spotify_name", "")),
        spotify_artists=str(data.get("spotify_artists", "")),
        popularity=int(data.get("popularity", -1) or -1),
        url=str(data.get("url", "")),
        match_score=float(data.get("match_score", 0.0) or 0.0),
        matched=bool(data.get("matched", False)),
        note=str(data.get("note", "")),
    )


def _recommended_keep_count(*, artist_track_count: int, min_per_artist: int, max_per_artist: int) -> int:
    if artist_track_count <= min_per_artist:
        return artist_track_count
    if artist_track_count <= 2:
        return artist_track_count
    scaled = max(min_per_artist, round(artist_track_count ** 0.5))
    return min(artist_track_count, max_per_artist, scaled)


def _write_csv(csv_path: Path, ranked_tracks: list[RankedTrack]) -> None:
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "song_name",
                "artist",
                "part_or_variant",
                "spotify_match",
                "spotify_artists",
                "popularity",
                "match_score",
                "keep_for_lf",
                "keep_reason",
                "spotify_url",
            ],
        )
        writer.writeheader()
        for item in ranked_tracks:
            writer.writerow(
                {
                    "song_name": item.row.display_label,
                    "artist": item.row.artist,
                    "part_or_variant": "LF" if item.keep_for_lf else "CUT",
                    "spotify_match": item.match.spotify_name,
                    "spotify_artists": item.match.spotify_artists,
                    "popularity": item.match.popularity if item.match.popularity >= 0 else "",
                    "match_score": item.match.match_score,
                    "keep_for_lf": "yes" if item.keep_for_lf else "no",
                    "keep_reason": item.keep_reason,
                    "spotify_url": item.match.url,
                }
            )


def _write_low_fat_project(
    *,
    base_payload: dict[str, Any],
    ranked_tracks: list[RankedTrack],
    output_path: Path,
    mod_name_suffix: str,
    mod_id_suffix: str,
) -> None:
    payload = json.loads(json.dumps(base_payload))
    kept_tracks = [json.loads(json.dumps(item.row.raw)) for item in ranked_tracks if item.keep_for_lf]
    payload["mod_name"] = f"{str(payload.get('mod_name', '')).strip()} {mod_name_suffix}".strip()
    payload["mod_id"] = f"{str(payload.get('mod_id', '')).strip()}{mod_id_suffix}"
    payload["media_rows"][0]["tracks_a"] = kept_tracks
    payload["media_rows"][0]["tracks_b"] = []
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Spotify-ranked Low Fat companion project for the HS90 megapack."
    )
    parser.add_argument(
        "--project",
        default=r"C:\Users\chowl\Music\ogg\HikariSakai90.nmbproj.json",
        help="Path to the source megapack project JSON.",
    )
    parser.add_argument(
        "--csv-out",
        default=r"C:\Users\chowl\Music\ogg\HikariSakai90-LF-Ranking.csv",
        help="Path to the output ranking CSV.",
    )
    parser.add_argument(
        "--lf-project-out",
        default=r"C:\Users\chowl\Music\ogg\HikariSakai90-LF.nmbproj.json",
        help="Path to the generated Low Fat project JSON.",
    )
    parser.add_argument(
        "--cache-out",
        default=r"C:\Users\chowl\Music\ogg\HikariSakai90-SpotifyCache.json",
        help="Path to the local Spotify match cache JSON.",
    )
    parser.add_argument(
        "--spotify-client-id",
        default=os.getenv("SPOTIFY_CLIENT_ID", "").strip(),
        help="Spotify client ID. Defaults to SPOTIFY_CLIENT_ID.",
    )
    parser.add_argument(
        "--spotify-client-secret",
        default=os.getenv("SPOTIFY_CLIENT_SECRET", "").strip(),
        help="Spotify client secret. Defaults to SPOTIFY_CLIENT_SECRET.",
    )
    parser.add_argument(
        "--min-per-artist",
        type=int,
        default=_DEFAULT_MIN_PER_ARTIST,
        help="Minimum songs to keep per artist.",
    )
    parser.add_argument(
        "--max-per-artist",
        type=int,
        default=_DEFAULT_MAX_PER_ARTIST,
        help="Maximum songs to keep per artist.",
    )
    parser.add_argument(
        "--mod-name-suffix",
        default="Low Fat",
        help='Suffix appended to the generated LF project mod name, e.g. "Low Fat".',
    )
    parser.add_argument(
        "--mod-id-suffix",
        default="_LF",
        help='Suffix appended to the generated LF project mod ID, e.g. "_LF".',
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=_DEFAULT_PROGRESS_EVERY,
        help="Print progress every N processed tracks.",
    )
    parser.add_argument(
        "--max-new-lookups",
        type=int,
        default=_DEFAULT_MAX_NEW_LOOKUPS,
        help="Maximum uncached Spotify track searches to perform in one run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if not args.spotify_client_id or not args.spotify_client_secret:
        print(
            "Spotify client credentials are required. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET or pass them as flags.",
            file=sys.stderr,
            flush=True,
        )
        return 2
    if args.min_per_artist < 1:
        print("--min-per-artist must be at least 1.", file=sys.stderr, flush=True)
        return 2
    if args.max_per_artist < args.min_per_artist:
        print("--max-per-artist must be >= --min-per-artist.", file=sys.stderr, flush=True)
        return 2
    if args.max_new_lookups < 1:
        print("--max-new-lookups must be at least 1.", file=sys.stderr, flush=True)
        return 2

    project_path = Path(args.project)
    csv_path = Path(args.csv_out)
    lf_project_path = Path(args.lf_project_out)
    cache_path = Path(args.cache_out)

    print(f"Loading project: {project_path}", flush=True)
    base_payload, tracks = _read_tracks(project_path)
    print(f"Tracks found: {len(tracks)}", flush=True)
    print(f"Cache file: {cache_path}", flush=True)

    spotify_client = SpotifyClient(args.spotify_client_id, args.spotify_client_secret)
    try:
        ranked_tracks = _rank_tracks(
            tracks,
            min_per_artist=args.min_per_artist,
            max_per_artist=args.max_per_artist,
            spotify_client=spotify_client,
            cache_path=cache_path,
            progress_every=max(1, args.progress_every),
            max_new_lookups=args.max_new_lookups,
        )
    except LookupLimitReached:
        print(
            "Stopped after reaching the per-run Spotify lookup cap. Re-run the command to continue filling the cache.",
            flush=True,
        )
        return 0
    except SpotifyQuotaExceeded:
        print(
            "Spotify quota is currently exhausted for this app. Your cache has been kept, so just re-run later and it will resume from where it left off.",
            file=sys.stderr,
            flush=True,
        )
        return 1

    kept_count = sum(1 for item in ranked_tracks if item.keep_for_lf)
    matched_count = sum(1 for item in ranked_tracks if item.match.matched)
    print(f"Matched on Spotify: {matched_count}/{len(ranked_tracks)}", flush=True)
    print(f"Kept for LF: {kept_count}/{len(ranked_tracks)}", flush=True)

    _write_csv(csv_path, ranked_tracks)
    _write_low_fat_project(
        base_payload=base_payload,
        ranked_tracks=ranked_tracks,
        output_path=lf_project_path,
        mod_name_suffix=args.mod_name_suffix,
        mod_id_suffix=args.mod_id_suffix,
    )
    print(f"Wrote CSV: {csv_path}", flush=True)
    print(f"Wrote LF project: {lf_project_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
