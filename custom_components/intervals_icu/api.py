"""Async client for the Intervals.icu REST API.

Authentication (verified against the official API cookbook):
    HTTP basic auth, username is the literal string ``API_KEY``,
    password is the athlete's personal API key.
    Bearer tokens are NOT accepted for personal API keys.

Athlete IDs are strings and normally carry a leading ``i`` (``i297087``).
Only early Strava-registered athletes have a bare numeric ID, so the client
probes both spellings once and remembers what worked.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from typing import Any

from aiohttp import BasicAuth, ClientError, ClientResponse, ClientSession

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://intervals.icu/api/v1"
API_KEY_USERNAME = "API_KEY"

# Established third-party clients run a token bucket at 10 req/s. We stay well
# below that: this integration is never in a hurry, and a 429 costs more than
# the wait it saves.
MIN_REQUEST_INTERVAL = 0.2
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30


class IntervalsError(Exception):
    """Base error for all Intervals.icu API failures."""


class IntervalsAuthError(IntervalsError):
    """Raised on 401/403 - wrong API key, or wrong athlete ID for this key."""


class IntervalsRateLimitError(IntervalsError):
    """Raised when the API keeps returning 429 after all retries."""


class IntervalsClient:
    """Thin, throttled wrapper around the Intervals.icu REST API."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        athlete_id: str | None = None,
    ) -> None:
        """Store credentials. No network access happens here."""
        self._session = session
        self._auth = BasicAuth(API_KEY_USERNAME, api_key)
        self._athlete_id = athlete_id
        self._throttle_lock = asyncio.Lock()
        self._last_request = 0.0

    @property
    def athlete_id(self) -> str | None:
        """Return the athlete ID this client is bound to."""
        return self._athlete_id

    async def _throttle(self) -> None:
        """Keep a minimum gap between two requests."""
        async with self._throttle_lock:
            wait = MIN_REQUEST_INTERVAL - (time.monotonic() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    async def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform a GET request and return the decoded JSON body."""
        url = f"{API_BASE}{path}"

        for attempt in range(1, MAX_RETRIES + 1):
            await self._throttle()
            try:
                response: ClientResponse = await self._session.get(
                    url,
                    params=params,
                    auth=self._auth,
                    timeout=REQUEST_TIMEOUT,
                )
            except (ClientError, asyncio.TimeoutError) as err:
                if attempt == MAX_RETRIES:
                    raise IntervalsError(f"connection to {url} failed: {err}") from err
                await asyncio.sleep(2**attempt)
                continue

            async with response:
                if response.status in (401, 403):
                    raise IntervalsAuthError(
                        f"authentication rejected for {path} (HTTP {response.status})"
                    )

                if response.status == 429:
                    # The API sends Retry-After; honour it instead of guessing.
                    retry_after = float(response.headers.get("Retry-After", 2**attempt))
                    if attempt == MAX_RETRIES:
                        raise IntervalsRateLimitError(
                            f"rate limited on {path}, giving up after {attempt} tries"
                        )
                    _LOGGER.debug("429 on %s, waiting %.1fs", path, retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                if response.status >= 500:
                    if attempt == MAX_RETRIES:
                        raise IntervalsError(
                            f"server error {response.status} on {path}"
                        )
                    await asyncio.sleep(2**attempt)
                    continue

                if response.status >= 400:
                    body = await response.text()
                    raise IntervalsError(
                        f"HTTP {response.status} on {path}: {body[:200]}"
                    )

                return await response.json()

        raise IntervalsError(f"request to {path} failed after {MAX_RETRIES} attempts")

    async def async_resolve_athlete(self) -> dict[str, Any]:
        """Find the athlete this API key belongs to and return their profile.

        Tries, in order: the ID as entered, the same ID with a leading ``i``,
        and finally ``0``, which some clients use to mean "the authenticated
        athlete". The first spelling that answers wins and is stored.
        """
        candidates: list[str] = []
        raw = (self._athlete_id or "").strip()

        if raw:
            candidates.append(raw)
            if not raw.lower().startswith("i"):
                candidates.append(f"i{raw}")
        candidates.append("0")

        last_error: Exception | None = None
        for candidate in candidates:
            try:
                profile = await self._request(f"/athlete/{candidate}")
            except IntervalsAuthError as err:
                last_error = err
                continue

            # Prefer the ID the API reports over the one the user typed.
            resolved = str(profile.get("id") or candidate)
            self._athlete_id = resolved
            _LOGGER.debug("resolved athlete id %s (tried %s)", resolved, candidate)
            return profile

        raise IntervalsAuthError(
            "no athlete could be resolved with this API key"
        ) from last_error

    async def async_get_athlete(self) -> dict[str, Any]:
        """Return the athlete profile (FTP, LTHR, sport settings, ...)."""
        return await self._request(f"/athlete/{self._athlete_id}")

    async def async_get_wellness(
        self,
        oldest: date,
        newest: date,
    ) -> list[dict[str, Any]]:
        """Return the daily wellness rows in the given inclusive date range.

        One row per day, keyed by ``id`` (the ISO date). Fitness/fatigue live
        here as ``icu_ctl`` / ``icu_atl`` - the athlete endpoint does not carry
        usable values for them.
        """
        return await self._request(
            f"/athlete/{self._athlete_id}/wellness",
            params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
        )

    async def async_get_events(
        self,
        oldest: date,
        newest: date,
    ) -> list[dict[str, Any]]:
        """Return calendar events (planned workouts, races, notes) in a range."""
        return await self._request(
            f"/athlete/{self._athlete_id}/events",
            params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
        )

    async def async_get_activities(
        self,
        oldest: date,
        newest: date,
        fields: tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Return activity summaries in a range, newest first.

        ``fields`` is passed straight to the API, which trims the payload
        server side - a full season then fits into a single request.
        """
        params: dict[str, Any] = {
            "oldest": oldest.isoformat(),
            "newest": newest.isoformat(),
        }
        if fields:
            params["fields"] = ",".join(fields)
        return await self._request(f"/athlete/{self._athlete_id}/activities", params=params)

    async def async_get_streams(
        self,
        activity_id: str,
        types: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        """Return per-second streams for one activity.

        The endpoint needs the .json suffix and returns a list of stream
        objects, not a mapping.
        """
        return await self._request(
            f"/activity/{activity_id}/streams.json",
            params={"types": ",".join(types)},
        )

