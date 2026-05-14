"""Constants for the APS Usage integration."""

DOMAIN = "aps_usage"

# Update interval: every hour (APS data refreshes daily, not real-time)
UPDATE_INTERVAL_SECONDS = 3600

# Days of daily usage history to fetch (60 gives ~2 billing cycles)
DAYS_OF_HISTORY = 60
