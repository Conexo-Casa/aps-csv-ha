"""Constants for the APS Usage integration."""

DOMAIN = "aps_usage"

# Config entry keys
CONF_ACCOUNT_ID = "account_id"

# Update interval (seconds)
UPDATE_INTERVAL_SECONDS = 3600  # 1 hour — APS data is not real-time

# Days of history to fetch on each update
DAYS_OF_HISTORY = 30
