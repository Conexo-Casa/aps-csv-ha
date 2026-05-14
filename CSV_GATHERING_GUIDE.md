# APS CSV Data Gathering Guide

This guide will help you use your browser's Developer Tools to capture the technical details required to automate your APS CSV power usage data download.

We need to understand the **specific HTTP request** your browser makes when you click the "usage" or CSV download link on the APS dashboard.

### Prerequisites

*   A web browser with Developer Tools (Chrome, Firefox, or Edge).
*   Your APS.com login credentials.

---

### Part 1: Setting up Developer Tools

1.  Open your browser and navigate to the APS.com login page. **Do not log in yet.**
2.  Open the **Developer Tools**:
    *   **Keyboard Shortcut (Windows/Linux):** `F12` or `Ctrl` + `Shift` + `I`
    *   **Keyboard Shortcut (macOS):** `Cmd` + `Option` + `I`
    *   **Menu Navigation:** Usually in the menu under "More Tools" -> "Developer Tools" or similar.
3.  In the Developer Tools pane that opens, find and click on the **Network** tab.
4.  Ensure that **Preserve log** is **checked** and that the recording button is **red** (active).
5.  Click the **Clear** button (a circle with a slash through it) to remove any existing logs.

---

### Part 2: Recording the CSV Download Request

1.  **Log into your APS account.** The Network tab will start populating with requests. This is normal.
2.  Navigate to your account dashboard and find the section for your usage data or the link that downloads the CSV file. You mentioned: `https://www.aps.com/en/Residential/Account/Overview/Dashboard?origin=usage#`.
3.  Once you are on the page with the CSV download link, look at the Developer Tools' Network tab.
    *   Ensure **Preserve log** is still checked.
    *   Find the **Filter** box (often at the top-left of the pane) and type **`csv`** to help you narrow down the results later.
4.  Now, **click the link or button that initiates the CSV file download.** Your browser should download the file.
5.  Immediately return to the Developer Tools and click the **recording button** (top-left) to **stop recording** (it should turn grey).

---

### Part 3: Extracting the Required Details

This is the critical step. We need to find the specific request that resulted in the CSV download and get its details.

1.  In the Network tab, with your `csv` filter active, look for the request.
    *   The **Method** will likely be **`GET`** or **`POST`**.
    *   The **Type** might be **`text/csv`** or **`fetch`**.
    *   The **File** (or Name) will likely end in `.csv`.
    *   A successful request should have a **Status** of **`200 OK`**.
2.  **Click on that successful request.** This will open a detailed view with several tabs.
3.  Find the **Headers** tab. Look for the "General" section. We need:
    *   **Request URL**
    *   **Request Method**
4.  Now, look for **Request Headers** (further down). We will need to see these, but **do not share your actual credentials, specific cookies, or auth tokens.** I'll show you what to mask in a moment.
5.  If the Request Method was `POST`, also look for a **Payload** or **Form Data** tab. We need everything listed in that tab, as well. Again, **mask any actual data values.**

### What to Provide

Please reply with the information in this format. I have provided an example of how to mask your sensitive data (replace secrets with `[MASKED]`).

**1. Request Details**
*   **Request URL:** `https://www.aps.com/api/Usage/DownloadUsageCsv?startDate=2023-01-01&endDate=2023-12-31&accountId=1234567`
*   **Request Method:** `GET`
*   **Is it a POST request?** No

**2. Request Headers (with actual values MASKED)**
```http
Accept: text/csv,application/json,text/plain,*/*
Accept-Encoding: gzip, deflate, br
Authorization: Bearer [MASKED_AUTH_TOKEN]
Cookie: ASP.NET_SessionId=[MASKED_SESSION_ID]; __RequestVerificationToken=[MASKED_TOKEN]; ... (mask all specific values)
Referer: https://www.aps.com/en/Residential/Account/Overview/Dashboard
User-Agent: Mozilla/5.0 ...
[Any other relevant custom headers like X-AccountId or X-CSRF-Token]
```

**3. Request Payload / Form Data (if Method was POST, with actual values MASKED)**
```json
{
  "startDate": "2023-01-01",
  "endDate": "2023-12-31",
  "accountId": "[MASKED_ACCOUNT_ID]",
  "includeWeather": true
}
```

This information is sufficient to build the automated integration. The masking prevents any security risks. Thank you for your help.
