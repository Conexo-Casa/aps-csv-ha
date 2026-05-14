"""API Client for APS Usage."""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

_LOGGER = logging.getLogger(__name__)

# Discovered from aps-apscom.js bundle — RSA-2048 public key used by JSEncrypt
APS_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAgUhnZn9KwG21odw0+4Jf
Ie/pdOd+Ry8sdxn4tnmkfZJZ8/5xV31Zi6QqIxoiOQrdROyJaDBtbv0KGS68Yfim
gqOpD9873Yp+PhN+VhurJsVX8a2UibdvrPIDOhe5+9Z/BPd5TeEhMK59Hvm7Z+pn
lFObF9DMGxfbUDUCU37lHkkz3rJONaPMXdUSJFGL+6VwFNCkj7tmusgQsLLzCOsx
miMgGOI+Wk1Nx9vCDOu9f9TaznrqTc9sFk/2dOQULDg7VQoeFoF8PjrZG3eEVZG
XFRaJBG+4mX4Vercms2J8u1NIeFdFeTjuo+nAiDsc0z4J9g3gVPC+k2080EBkqHw
ycwIDAQAB
-----END PUBLIC KEY-----"""

# Discovered from aps-apscom.js bundle
OCP_APIM_KEY = "d2e9aafca6d546cd9097a3e3072cd7a5"

# Must match a real browser to pass Imperva/Incapsula WAF
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

LOGIN_URL = "https://www.aps.com/api/sitecore/SitecoreReactApi/UserAuthentication"
USER_DETAILS_URL = "https://www.aps.com/api/sitecore/sitecorereactapi/GetAllUserDetails"
USAGE_URL = "https://mobi.aps.com/customeraccountservices/v1/getsimpleusagedata"


def _encrypt_password(password: str) -> str:
    """Encrypt the password using the APS RSA public key (PKCS#1 v1.5).

    APS uses JSEncrypt in the browser which performs RSA PKCS#1 v1.5
    encryption. The public key and algorithm are hardcoded in aps-apscom.js.
    """
    public_key = serialization.load_pem_public_key(APS_PUBLIC_KEY.encode("utf-8"))
    assert isinstance(public_key, RSAPublicKey)
    encrypted = public_key.encrypt(password.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(encrypted).decode("utf-8")


class APSAuthError(Exception):
    """Raised when authentication fails."""


class APSUsageAPI:
    """APS Usage API Client with full Sitecore/B2C authentication support."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._username = username
        self._password = password
        self._b2c_access_token: str | None = None
        self._account_id: str | None = None
        self._token_expiry: datetime | None = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Perform the full APS login and populate the B2C access token.

        Reverse-engineered from aps-apscom.js (_readSessionInfo,
        LoginPageOverlay.js authenticateUser):

        1. POST /api/sitecore/SitecoreReactApi/UserAuthentication
           with RSA-PKCS1v15-encrypted password.
           → Sets session cookies (.AspNet.Cookies, ASP.NET_SessionId,
             DomainSet, etc.) and returns {isLoginSuccess, redirectUrl}.

        2. GET the redirectUrl (the account dashboard) so the server can
           fully initialize the session and set remaining cookies.

        3. GET /api/sitecore/sitecorereactapi/GetAllUserDetails
           → Returns {Details: {profileData: {B2C_AccessToken, AccountID, …},
                                UserDetails: {AccountsList: […]}}}
           The B2C_AccessToken here is what all mobi.aps.com calls need.
        """
        encrypted_pw = _encrypt_password(self._password)

        _LOGGER.debug("APS: Authenticating user %s", self._username)

        # Step 1 — POST credentials (password encrypted with APS RSA key)
        async with self._session.post(
            LOGIN_URL,
            json={"username": self._username, "password": encrypted_pw},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.aps.com",
                "Referer": "https://www.aps.com/en/Authorization/Login",
                "User-Agent": _USER_AGENT,
            },
        ) as resp:
            raw = await resp.text()
            if resp.status != 200 or not raw.strip().startswith("{"):
                # WAF block returns HTML; credentials issue returns JSON error
                _LOGGER.error(
                    "APS: Login HTTP %s, body preview: %s",
                    resp.status,
                    raw[:200],
                )
                raise APSAuthError(
                    f"Login request blocked or failed (HTTP {resp.status}). "
                    "APS may be rate-limiting. Try again in a few minutes."
                )
            import json as _json

            data: dict[str, Any] = _json.loads(raw)

        if not data.get("isLoginSuccess"):
            error = data.get("error", "unknown")
            _LOGGER.error("APS: Login rejected — error=%s", error)
            raise APSAuthError(f"APS credentials rejected: {error}")

        redirect_url: str = data.get("redirectUrl", "")
        _LOGGER.debug("APS: Login OK, following redirect: %s", redirect_url)

        # Step 2 — GET dashboard to fully initialise the server-side session
        dashboard_url = (
            redirect_url
            or "https://www.aps.com/en/Residential/Account/Overview/Dashboard"
        )
        async with self._session.get(
            dashboard_url,
            headers={
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
                "Referer": "https://www.aps.com/en/Authorization/Login",
                "User-Agent": _USER_AGENT,
            },
            allow_redirects=True,
        ) as resp:
            _LOGGER.debug("APS: Dashboard GET → HTTP %s", resp.status)

        # Step 3 — GET all user details; contains B2C_AccessToken + AccountID
        await self._fetch_user_details()

    async def _fetch_user_details(self) -> None:
        """Call GetAllUserDetails and extract token + account ID.

        Response shape (from _readSessionInfo / populateSessionInfo in JS):
            {
              "Details": {
                "profileData": {
                  "B2C_AccessToken": "Bearer eyJ...",
                  "AccountID": "0539389128",
                  ...
                },
                "UserDetails": {
                  "getUserDetailResponse": {
                    "AccountsList": [{"AccountID": "0539389128", ...}]
                  }
                }
              }
            }
        """
        async with self._session.get(
            USER_DETAILS_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.aps.com/en/Residential/Account/Overview/Dashboard",
                "User-Agent": _USER_AGENT,
            },
        ) as resp:
            raw = await resp.text()
            _LOGGER.debug(
                "APS: GetAllUserDetails HTTP %s, len=%d", resp.status, len(raw)
            )

        if not raw or not raw.strip():
            raise APSAuthError(
                "GetAllUserDetails returned empty response. "
                "The session cookie may not have been established correctly."
            )

        import json as _json

        try:
            full: dict[str, Any] = _json.loads(raw.lstrip("\ufeff"))
        except _json.JSONDecodeError as err:
            raise APSAuthError(
                f"GetAllUserDetails response is not JSON: {raw[:200]}"
            ) from err

        details = full.get("Details", {})
        profile = details.get("profileData", {})

        _LOGGER.debug(
            "APS: GetAllUserDetails — Details keys=%s, profileData keys=%s",
            list(details.keys()),
            list(profile.keys()) if profile else "EMPTY",
        )

        if not profile:
            _LOGGER.debug("APS: GetAllUserDetails full response: %s", str(full)[:500])
            raise APSAuthError(
                "profileData missing from GetAllUserDetails response. "
                "Session may not be authenticated. Keys: " + str(list(details.keys()))
            )

        # B2C_AccessToken may already include the "Bearer " prefix
        token: str = profile.get("B2C_AccessToken", "")
        if not token:
            raise APSAuthError(
                "B2C_AccessToken not found in profileData. "
                "Keys: " + str(list(profile.keys()))
            )

        # Strip "Bearer " prefix if present — we add it ourselves
        if token.lower().startswith("bearer "):
            token = token[7:]

        self._b2c_access_token = token
        self._token_expiry = datetime.now() + timedelta(minutes=55)

        # Also grab account ID while we have the data
        if not self._account_id:
            account_id = profile.get("AccountID")
            if not account_id:
                # Fall back to AccountsList
                accounts = (
                    details.get("UserDetails", {})
                    .get("getUserDetailResponse", {})
                    .get("AccountsList", [])
                )
                account_id = accounts[0].get("AccountID") if accounts else None
            self._account_id = account_id
            _LOGGER.debug("APS: account_id=%s", self._account_id)

        _LOGGER.debug("APS: B2C_AccessToken obtained successfully.")

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid, unexpired token."""
        if self._b2c_access_token is None:
            await self.authenticate()
            return
        if self._token_expiry and datetime.now() >= self._token_expiry:
            _LOGGER.debug("APS: Token expired — refreshing.")
            try:
                await self._fetch_user_details()
            except APSAuthError:
                _LOGGER.warning("APS: Token refresh failed — re-authenticating.")
                await self.authenticate()

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    async def get_usage_data(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
    ) -> dict:
        """Fetch energy usage data from mobi.aps.com.

        Args:
            account_id: The APS account ID (e.g. "0539389128").
            start_date: Start date string in format "MM/DD/YYYY".
            end_date: End date string in format "MM/DD/YYYY".

        Returns:
            Parsed JSON response dict from the APS mobile API.
        """
        await self._ensure_authenticated()

        headers = {
            "Host": "mobi.aps.com",
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "Ocp-Apim-Subscription-Key": OCP_APIM_KEY,
            "Authorization": f"Bearer {self._b2c_access_token}",
            "Origin": "https://www.aps.com",
            "Referer": "https://www.aps.com/",
        }

        payload = {
            "getSimpleUsageDataRequest": {
                "getSimpleUsageDataReq": {
                    "accountId": account_id,
                    "startDate": start_date,
                    "endDate": end_date,
                },
                "cssUser": "APSCOM",
            }
        }

        _LOGGER.debug(
            "APS: mobi POST account_id=%s dates=%s→%s",
            account_id,
            start_date,
            end_date,
        )

        try:
            async with self._session.post(
                USAGE_URL, headers=headers, json=payload
            ) as response:
                if response.status == 401:
                    _LOGGER.warning("APS: 401 on usage call — re-authenticating.")
                    await self.authenticate()
                    headers["Authorization"] = f"Bearer {self._b2c_access_token}"
                    async with self._session.post(
                        USAGE_URL, headers=headers, json=payload
                    ) as retry:
                        retry_body = await retry.text()
                        _LOGGER.debug(
                            "APS: mobi retry HTTP %s: %s",
                            retry.status,
                            retry_body[:500],
                        )
                        retry.raise_for_status()
                        return await retry.json(content_type=None)
                # Log non-2xx responses before raising
                if response.status >= 400:
                    err_body = await response.text()
                    _LOGGER.error(
                        "APS: mobi HTTP %s body: %s | account_id=%s | token_prefix=%s",
                        response.status,
                        err_body[:500],
                        account_id,
                        (self._b2c_access_token or "")[:30] + "...",
                    )
                    response.raise_for_status()
                return await response.json(content_type=None)
        except aiohttp.ClientError as err:
            raise Exception(f"Error fetching usage data: {err}") from err

    async def get_account_id(self) -> str | None:
        """Return the account ID discovered during authentication."""
        if self._account_id is None:
            await self._ensure_authenticated()
        return self._account_id
