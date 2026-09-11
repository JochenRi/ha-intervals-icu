"""Constants for the Intervals.icu integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "intervals_icu"

CONF_API_KEY = "api_key"
CONF_ATHLETE_ID = "athlete_id"

# Stage 1 uses plain polling. From stage 5 on, Intervals.icu webhooks push
# activity uploads and calendar changes, and this interval becomes a fallback.
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

# Wellness rows are filled in over the course of a day and can be corrected
# days later, so a window is both cheaper and safer than a single day. Thirty
# days is also the window used to decide which sensors are enabled by default:
# fields that carry no value at all in a month are created disabled.
WELLNESS_LOOKBACK_DAYS = 30

# Calendar window fetched on every refresh.
EVENTS_PAST_DAYS = 30
EVENTS_FUTURE_DAYS = 60

# Archive maintenance.
RECENT_DAYS = 30                  # window re-checked on every routine sync
HISTORY_START_FALLBACK_DAYS = 730  # used when the athlete has no activation date
DFA_BATCH_SIZE = 25               # stream fetches per routine sync
ARCHIVE_SYNC_INTERVAL = timedelta(hours=6)

MANUFACTURER = "Intervals.icu"

# Sidebar panel. PANEL_VERSION is appended to the module URL so browsers pick
# up a new build instead of serving the cached one.
PANEL_URL_PATH = DOMAIN
PANEL_STATIC_PATH = f"/{DOMAIN}_panel"
PANEL_COMPONENT = "intervals-icu-panel"
PANEL_FILE = "intervals-panel.js"
PANEL_TITLE = "Intervals"
PANEL_ICON = "mdi:chart-timeline-variant"
PANEL_VERSION = "0.10.0"
