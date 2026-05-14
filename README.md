# APS Usage — Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/release/conexocasa/aps-csv-ha.svg)](https://github.com/conexocasa/aps-csv-ha/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A custom Home Assistant integration for **Arizona Public Service (APS)** customers that provides real-time energy usage and billing sensors — no APS mobile app or CSV download required.

---

## Sensors

| Sensor | Entity ID | Unit | Description |
|--------|-----------|------|-------------|
| Yesterday kWh | `sensor.aps_yesterday_kwh` | kWh | Prior day's total electricity usage |
| Yesterday On-Peak kWh | `sensor.aps_yesterday_on_peak_kwh` | kWh | Prior day's on-peak (4–7 PM weekdays) usage |
| Yesterday Off-Peak kWh | `sensor.aps_yesterday_off_peak_kwh` | kWh | Prior day's off-peak usage |
| Current Billing Cycle kWh | `sensor.aps_current_billing_cycle_kwh` | kWh | Total kWh since current billing cycle started |
| 30-Day kWh | `sensor.aps_30_day_kwh` | kWh | Rolling 30-day energy total |
| Current Balance | `sensor.aps_current_balance` | USD | Outstanding bill amount |
| Bill Due Date | `sensor.aps_bill_due_date` | date | Next payment due date |
| Last Payment | `sensor.aps_last_payment` | USD | Most recent payment amount |

All sensors update **every hour**. Energy sensors (kWh) are compatible with the [HA Energy Dashboard](https://www.home-assistant.io/docs/energy/).

---

## Requirements

- Home Assistant **2023.1** or newer
- An active **APS.com account** (aps.com login credentials)
- The `cryptography` Python package (automatically installed by HA)

---

## Installation

### Option A — HACS (Recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** → click the **⋮ menu** (top right) → **Custom repositories**.
3. Enter the repository URL:
   ```
   https://github.com/conexocasa/aps-csv-ha
   ```
   Select **Integration** as the category and click **Add**.
4. Search for **APS Usage** in the HACS integrations list and click **Download**.
5. **Restart Home Assistant.**
6. Follow [Configuration](#configuration) below.

### Option B — Manual Installation

1. Download the latest release from the [Releases page](https://github.com/conexocasa/aps-csv-ha/releases) or clone this repository.
2. Copy the `custom_components/aps_usage/` folder into your Home Assistant config directory:
   ```
   config/
   └── custom_components/
       └── aps_usage/
           ├── __init__.py
           ├── api.py
           ├── config_flow.py
           ├── const.py
           ├── manifest.json
           └── sensor.py
   ```
3. **Restart Home Assistant.**
4. Follow [Configuration](#configuration) below.

> **Tip:** If you have SSH or terminal access to your HA host, you can install with two commands:
> ```bash
> mkdir -p /config/custom_components/aps_usage
> for f in __init__.py api.py config_flow.py const.py manifest.json sensor.py; do
>   curl -sL "https://raw.githubusercontent.com/conexocasa/aps-csv-ha/main/custom_components/aps_usage/$f" \
>     -o "/config/custom_components/aps_usage/$f"
> done
> ```
> Then restart HA.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **APS Usage** and click it.
3. Enter your **APS.com username** and **password** (the same credentials you use at [aps.com](https://www.aps.com) or the APS mobile app).
4. Click **Submit**.

The integration will authenticate, auto-detect your active service agreement, and create all sensors. No account ID or meter number is needed — these are discovered automatically from your account.

> **Multiple service addresses:** If you have more than one APS service address under a single account, the integration automatically selects the **currently active** service (the one with no end date). All sensors reflect that address. The `premise_address` attribute on each sensor shows which address is being used.

---

## Energy Dashboard

The energy kWh sensors are compatible with Home Assistant's built-in Energy Dashboard.

To add them:
1. Go to **Settings → Dashboards → Energy**.
2. Under **Electricity grid → Grid consumption**, click **Add consumption**.
3. Select `sensor.aps_current_billing_cycle_kwh` for billing-cycle tracking, or `sensor.aps_yesterday_kwh` for daily tracking.

---

## Sensor Attributes

### Energy Sensors (kWh)
All energy sensors carry these extra attributes:

| Attribute | Example | Description |
|-----------|---------|-------------|
| `account_id` | `0539389128` | APS account number |
| `premise_address` | `1049 N VILLA NUEVA DR...` | Service address |
| `latest_data_date` | `2026-05-13` | Date of most recent data |
| `bill_cycle_start` | `2026-04-09` | Start of current billing cycle |

`sensor.aps_current_billing_cycle_kwh` also includes:

| Attribute | Example | Description |
|-----------|---------|-------------|
| `rate_plan` | `R3-47` | APS rate plan code |

### Balance Sensor (`sensor.aps_current_balance`)

| Attribute | Example | Description |
|-----------|---------|-------------|
| `due_date` | `06-01-2026` | Payment due date |
| `new_charges` | `0` | New charges this period |
| `auto_pay` | `true` | AutoPay enrolled |
| `budget_billing` | `true` | Budget Billing enrolled |
| `last_payment_amount` | `303.52` | Most recent payment |
| `last_payment_date` | `04-30-2026` | Date of last payment |

### Last Payment Sensor (`sensor.aps_last_payment`)

| Attribute | Example | Description |
|-----------|---------|-------------|
| `last_payment_date` | `04-30-2026` | Date of last payment |
| `account_id` | `0539389128` | APS account number |

---

## Lovelace Cards

Here is a minimal Lovelace configuration to display your APS data:

```yaml
type: entities
title: APS Energy
entities:
  - entity: sensor.aps_yesterday_kwh
    name: Yesterday
  - entity: sensor.aps_current_billing_cycle_kwh
    name: This Billing Cycle
  - entity: sensor.aps_30_day_kwh
    name: Last 30 Days
  - entity: sensor.aps_yesterday_on_peak_kwh
    name: On-Peak (Yesterday)
  - entity: sensor.aps_yesterday_off_peak_kwh
    name: Off-Peak (Yesterday)
  - entity: sensor.aps_current_balance
    name: Current Balance
  - entity: sensor.aps_bill_due_date
    name: Due Date
  - entity: sensor.aps_last_payment
    name: Last Payment
```

---

## Update Frequency

The integration polls APS **once per hour**. APS updates usage data daily (not real-time), so energy readings reflect usage through the **previous day**. Balance and billing data reflects your current APS.com account balance at the time of the last poll.

---

## Troubleshooting

### "Invalid Auth" error during setup
- Verify your credentials work at [aps.com](https://www.aps.com/en/Authorization/Login).
- APS rate-limits login attempts. Wait 5–10 minutes and try again.
- Ensure you're using your **APS.com username** (not your email address or account number).

### Integration in "Setup Retry" / sensors unavailable
Check **Settings → System → Logs** and filter for `aps_usage`. Common causes:

| Error | Cause | Fix |
|-------|-------|-----|
| `Authentication failed` | Wrong password / rate limited | Re-check credentials; wait 10 min |
| `Connection error` | HA can't reach aps.com | Check HA network / DNS |
| `No active service agreement` | All SAs have end dates | Open a GitHub issue with your account type |
| `Login request blocked` | Imperva WAF challenge | Retry in 15 minutes (auto-recovers) |

### Enable debug logging
Add to `configuration.yaml` and restart:
```yaml
logger:
  default: warning
  logs:
    custom_components.aps_usage: debug
```
Then check **Settings → System → Logs** and filter for `aps_usage`.

---

## How It Works

This integration was reverse-engineered from the APS website (`aps.com`) and the Android mobile app (`com.aps.apsconsumerapp` v4.0.10, decompiled with jadx + hermes-dec).

### Authentication Flow
1. **Password encryption:** The password is encrypted with an RSA-2048 public key using PKCS#1 v1.5 (replicating the `JSEncrypt` library used by the APS website login form, key extracted from `aps-apscom.js`).
2. **Login:** `POST https://www.aps.com/api/sitecore/SitecoreReactApi/UserAuthentication` — returns `{isLoginSuccess: true, redirectUrl: "..."}`.
3. **Session establishment:** `GET {redirectUrl}` — establishes ASP.NET session cookies.
4. **Token retrieval:** `GET https://www.aps.com/api/sitecore/sitecorereactapi/GetAllUserDetails` — returns the Azure AD B2C access token (`B2C_AccessToken`), account details, and `getSASPListByAccountID` containing all service agreements with meter numbers.

### Usage Data
- Endpoint discovered in `Accounts/Dashboard.js` (loaded by the APS account dashboard page):
  ```
  GET https://mobi.aps.com/ccb-billing/v1/getdailyusagecharges
  ```
  Query parameters: `action=read`, `accountNumber`, `userName`, `emailAddress`, `sAID` (Service Agreement ID), `spId` (Service Point ID), `startDate`, `endDate`, `cSSUser=APSCOM`

- The **active service agreement** is identified from `getSASPListByAccountID` as the entry with an empty `sAEndDate` field.

- The response contains a `series` array (one entry per day) with `totalUsage`, `onPeakUsage`, `offPeakUsage`, temperature, and charge amounts, plus `billCycleDates` marking billing cycle boundaries.

### Financial Data
- Extracted directly from the `GetAllUserDetails` response — `getAccountFinancialDetails` contains `currentBalance`, `dueDt`, `lastPayAmt`, `lastPayDt`, and `newCharges`. No additional API call is needed.

---

## Privacy & Security

- Credentials are stored in **Home Assistant's encrypted config entry storage**. They are never logged or transmitted to any third party.
- All network requests go directly to `www.aps.com` and `mobi.aps.com`.
- The integration is **read-only** — it makes no changes to your APS account.
- The integration requires `cryptography>=41.0.0` (a standard Python security library) for RSA password encryption.

---

## Contributing

Pull requests are welcome! When reporting a bug, please include:
1. Your Home Assistant version (`Settings → About`)
2. The integration version
3. Relevant log entries (with **all credentials and account numbers redacted**)

---

## License

[MIT License](LICENSE)

---

## Disclaimer

This integration is not affiliated with, endorsed by, or supported by Arizona Public Service Company (APS). It uses undocumented private APIs that APS may change at any time. Use at your own risk.
