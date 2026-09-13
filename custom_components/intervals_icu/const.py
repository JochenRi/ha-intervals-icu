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
PANEL_VERSION = "0.39.0"

# --- thresholds shared by backend and panel -----------------------------------
# One definition per number, here, because the panel has to show several of them
# and a second copy in the frontend (or in a second module) is a second truth.
# The NAMES carry the question the number answers, not the place it is used.

DECOUPLING_GOOD = 5.0  # FRIEL - a coach's rule of thumb, NOT a study threshold

# Which sessions the durability tile may look at.
DURABILITY_MIN_MINUTES = 45      # below this a decoupling reading is not usable
DURABILITY_MAX_INTENSITY = 80    # interval sessions are a different question
DURABILITY_MAX_VI = 1.10         # variability index: only steady rides qualify
DURABILITY_EXCLUDED_TYPES = ("VirtualRide",)  # different environment, fixed load

# Where the tile splits. The AXIS (accumulated work) is what the literature
# supports; the NUMBER is a house setting - see docs/ausbau.md F1.
DURABILITY_SPLIT_KJ = 800.0

# Three minimum counts, three different questions. Collapsing them into one
# number would be the same error as the duplicated 5.0, only inverted.
MIN_SESSIONS_FOR_TILE = 8          # is there enough history for the tile at all?
MIN_SESSIONS_TO_CLAIM_GROUP = 5    # may a single group's value be asserted?
MIN_PEERS_TO_RANK_METRIC = 6       # may one metric be placed as a percentile?

# Comparison group (docs/ausbau.md C3): caliper widths as multiples of the
# athlete's own standard deviation, widened in steps until the metric has
# enough peers. Stops at 1.0 SD - wider is no longer a comparison group.
PEER_CALIPER_STAGES = (0.2, 0.4, 0.6, 0.8, 1.0)
