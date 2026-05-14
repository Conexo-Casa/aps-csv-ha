# APS Usage for Home Assistant

A custom integration for Home Assistant to retrieve and display power usage data from Arizona Public Service (APS).

This integration leverages the APS mobile API (`mobi.aps.com`) to fetch deterministic usage data on a scheduled basis, allowing it to be presented in Home Assistant dashboards and the Energy Panel.

## Current State: Pre-Alpha / Under Development

**Important:** This integration is currently under active development. The files in this repository represent the necessary file structure (scaffold) and initial API request logic (`api.py`) based on technical details gathered from browser developer tools.

It consists of **functional stubs** and placeholders. **You cannot yet install or configure this as a working sensor.**

### Current Features (Stubs)

*   [Completed] Basic file structure for a Home Assistant custom component.
*   [Completed] `manifest.json` with metadata.
*   [Completed] Initial implementation of the `POST` request to the APS mobile API endpoint in `api.py`.
*   [Completed] Basic config flow placeholder in `config_flow.py` for future credential input.
*   [Completed] Placeholder `sensor.py` and `__init__.py` ready for final logic implementation.

### Key Discoveries & Implementation Plan

*   **Platform:** The standard `https://www.aps.com` dashboard uses Sitecore. The API requests, however, go to a mobile-optimized subdomain at `https://mobi.aps.com`.
*   **Data Retrieval:** Usage data is retrieved via a deterministic `POST` request to `https://mobi.aps.com//customeraccountservices/v1/getsimpleusagedata`. This request requires:
    *   An `Ocp-Apim-Subscription-Key`.
    *   An `Authorization` header containing a valid JWT (JSON Web Token).
    *   A JSON payload defining the account, premise, and date range.
*   **Next Development Step:** Implement a robust mechanism within Home Assistant to automate the login process on `aps.com` to obtain a fresh `auth_token` (JWT) for the API client, securely storing the user's credentials using the built-in Home Assistant config flow and password storage.

## Security Warning

**DO NOT SHARE YOUR LIVE AUTHENTICATION TOKENS.**

The authentication token (JWT) used by the APS mobile API contains sensitive personal information (such as your username and email) and provides access to your account. When gathering data using browser developer tools, always mask your actual tokens before sharing information.

## Roadmap

*   [Pending] Implement automated authentication logic to retrieve the JWT token.
*   [Pending] Connect the config flow to the authentication logic.
*   [Pending] Implement robust parsing of the JSON response from the APS API.
*   [Pending] Create functional `SensorEntity` instances in `sensor.py` with correct device classes and state classes.
*   [Pending] Implement Long-Term Statistics support so data can be viewed in the Home Assistant Energy panel.
*   [Pending] Final verification of a full end-to-end implementation (setup, deterministic verification, report).
