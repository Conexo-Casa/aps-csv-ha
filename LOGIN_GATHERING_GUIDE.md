# APS Login Data Gathering Guide

We need to understand the **specific HTTP request** your browser makes when you **log into** your account on APS.com.

---

### Part 1: Setting up Developer Tools

1.  Open your browser and navigate to the APS.com login page. **Do not log in yet.**
2.  Open the **Developer Tools**:
    *   **Keyboard Shortcut (Windows/Linux):** `F12` or `Ctrl` + `Shift` + `I`
    *   **Keyboard Shortcut (macOS):** `Cmd` + `Option` + `I`
3.  In the Developer Tools pane that opens, find and click on the **Network** tab.
4.  Ensure that **Preserve log** is **checked** and that the recording button is **red** (active).
5.  Click the **Clear** button (a circle with a slash through it) to remove any existing logs.

---

### Part 2: Recording the Login Request

1.  Enter your username and password into the APS login form.
2.  **Click the "Log In" (or equivalent) button.**
3.  Immediately return to the Developer Tools pane and look at the Network tab.
    *   The recording button should still be red.
    *   Find the **Filter** box and type **`login`**. If nothing comes up, try filtering by **`auth`** or leave it blank and look for a `POST` request that was made right after you clicked the button.
4.  Once you find the request (it should be a `POST` request with a status like `200` or `302`), **click the recording button** (top-left) to **stop recording** (it should turn grey).

---

### Part 3: Extracting the Required Details

This is the critical step. We need to find the specific request that was your login attempt.

1.  In the Network tab, look for that specific `POST` request. Success may be indicated by a status `200`, but often it's a `302 Redirect`.
2.  **Click on that successful/redirect request.** This will open a detailed view with several tabs.
3.  Find the **Headers** tab. Look for the "General" section. We need:
    *   **Request URL**
    *   **Request Method** (Should be `POST`)
4.  Find the **Request Payload** (or **Form Data**, often at the very bottom of the Headers tab, or in a separate "Payload" tab).

### What to Provide

Please reply with the information in this format. **Do not share your actual credentials.** Use `[USERNAME]` and `[PASSWORD]` as placeholders.

**1. Login Request Details**
*   **Request URL:** `[Paste the login URL here]`
*   **Request Method:** `POST`

**2. Request Payload / Form Data (MASKED)**
```json
{
  "username": "[USERNAME]",
  "password": "[PASSWORD]",
  ... (rest of the payload, masking any other identifiers)
}
```

This information is sufﬁcient to build the automated login logic. The masking prevents any security risks. Thank you for your help.
