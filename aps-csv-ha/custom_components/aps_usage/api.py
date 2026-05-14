"""API Client for APS Usage."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import base64

import aiohttp
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

_LOGGER = logging.getLogger(__name__)

# Discovered from aps-apscom.js bundle
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

LOGIN_URL = "https://www.aps.com/api/sitecore/SitecoreReactApi/UserAuthentication"
REFRESH_TOKEN_URL = (
    "https://www.aps.com/api/sitecore/sitecorereactapi/GenerateRefreshTokenDetails"
)
REFRESH_PROFILE_URL = "https://www.aps.com/authorization/refreshprofile"
USAGE_URL = "https://mobi.aps.com/customeraccountservices/v1/getsimpleusagedata"


def _encrypt_password(password: str) -> str:
    """Encrypt the password using the APS RSA public key (PKCS1 v1.5).

    APS uses JSEncrypt in the browser, which performs RSA PKCS#1 v1.5
    encryption. We replicate that here using the cryptography library.
    """
    public_key = serialization.load_pem_public_key(APS_PUBLIC_KEY.encode("utf-8"))
    assert isinstance(public_key, RSAPublicKey)
    encrypted = public_key.encrypt(
        password.encode("utf-8"),
        padding.PKCS1v15(),
    )
    return base64.b64encode(encrypted).decode("utf-8")


class APSAuthError(Exception):
    """Raised when authentication fails."""


class APSUsageAPI:
    """APS Usage API Client with full authentication support."""

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
        self._token_expiry: datetime | None = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Perform full login flow and store the B2C access token.

        Flow (discovered from LoginPageOverlay.js + aps-apscom.js):
        1. POST /api/sitecore/SitecoreReactApi/UserAuthentication
           with RSA-encrypted password.
        2. If successful, the response contains isLoginSuccess=True,
           redirectUrl, and Claims dict.
        3. POST the Claims as a form to /authorization/refreshprofile —
           this sets the session cookies containing the B2C token.
        4. GET /api/sitecore/sitecorereactapi/GenerateRefreshTokenDetails
           to obtain the B2C_AccessToken we can use for mobi.aps.com.
        """
        encrypted_pw = _encrypt_password(self._password)

        # Step 1: Authenticate
        login_payload = {
            "username": self._username,
            "password": encrypted_pw,
        }
        login_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.aps.com",
            "Referer": "https://www.aps.com/en/Authorization/Login",
            "User-Agent": ("Mozilla/5.0 (compatible; HomeAssistant/APSUsage)"),
        }
        _LOGGER.debug("APS: Sending login request for user %s", self._username)
        async with self._session.post(
            LOGIN_URL,
            json=login_payload,
            headers=login_headers,
        ) as resp:
            if resp.status != 200:
                raise APSAuthError(f"Login request failed with HTTP {resp.status}")
            data: dict[str, Any] = await resp.json(content_type=None)

        if not data.get("isLoginSuccess"):
            error = data.get("error", "unknown")
            raise APSAuthError(f"APS login rejected: {error}")

        redirect_url: str = data.get("redirectUrl", "")
        claims: dict[str, Any] = data.get("Claims", {})

        _LOGGER.debug("APS: Login succeeded. Posting Claims to refreshprofile.")

        # Step 2: POST Claims as form to /authorization/refreshprofile
        # This mirrors what the browser does: Aps.Util.postCall(redirectUrl, Claims)
        profile_url = redirect_url if redirect_url else REFRESH_PROFILE_URL
        async with self._session.post(
            profile_url,
            data=claims,  # form-encoded
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.aps.com",
                "Referer": "https://www.aps.com/en/Authorization/Login",
            },
            allow_redirects=True,
        ) as resp:
            _LOGGER.debug("APS: refreshprofile responded with HTTP %s", resp.status)

        # Step 3: Get the B2C access token from the now-established session
        await self._refresh_token()

    async def _refresh_token(self) -> None:
        """Fetch a fresh B2C_AccessToken from the session."""
        async with self._session.get(
            REFRESH_TOKEN_URL,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.aps.com/en/Residential/Account/Overview/Dashboard",
            },
        ) as resp:
            if resp.status != 200:
                raise APSAuthError(f"Token refresh failed with HTTP {resp.status}")
            token_data: dict[str, Any] = await resp.json(content_type=None)

        token = token_data.get("B2C_AccessToken") or token_data.get("access_token")
        if not token:
            _LOGGER.debug("Token refresh raw response: %s", token_data)
            raise APSAuthError(
                "Could not find B2C_AccessToken in refresh response. "
                "Response keys: " + str(list(token_data.keys()))
            )

        self._b2c_access_token = token
        # Tokens typically expire in 1 hour; refresh 5 min early
        self._token_expiry = datetime.now() + timedelta(minutes=55)
        _LOGGER.debug("APS: B2C_AccessToken obtained/refreshed.")

    async def _ensure_authenticated(self) -> None:
        """Make sure we have a valid token, refreshing if needed."""
        if self._b2c_access_token is None:
            await self.authenticate()
            return
        if self._token_expiry and datetime.now() >= self._token_expiry:
            _LOGGER.debug("APS: Token expired, refreshing.")
            try:
                await self._refresh_token()
            except APSAuthError:
                _LOGGER.warning("APS: Token refresh failed, re-authenticating.")
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
        """Fetch usage data from mobi.aps.com.

        Args:
            account_id: The APS account ID (e.g. "1234567890").
            start_date: Start date string in format "MM/DD/YYYY".
            end_date: End date string in format "MM/DD/YYYY".

        Returns:
            Parsed JSON response dict from the APS usage API.
        """
        await self._ensure_authenticated()

        headers = {
            "Host": "mobi.aps.com",
            "User-Agent": "Mozilla/5.0 (compatible; HomeAssistant/APSUsage)",
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

        try:
            async with self._session.post(
                USAGE_URL, headers=headers, json=payload
            ) as response:
                if response.status == 401:
                    # Token rejected — re-auth once and retry
                    _LOGGER.warning("APS: 401 on usage call, re-authenticating.")
                    await self.authenticate()
                    headers["Authorization"] = f"Bearer {self._b2c_access_token}"
                    async with self._session.post(
                        USAGE_URL, headers=headers, json=payload
                    ) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.json(content_type=None)
                response.raise_for_status()
                return await response.json(content_type=None)
        except aiohttp.ClientError as err:
            raise Exception(f"Error fetching usage data: {err}") from err

    async def get_account_id(self) -> str | None:
        """Retrieve the account ID from the established session.

        After login the session contains UserInfo with AccountID.
        This calls the sitecore API to get it.
        """
        await self._ensure_authenticated()
        try:
            async with self._session.get(
                "https://www.aps.com/api/sitecore/sitecorereactapi/GetUserInfo",
                headers={"Accept": "application/json"},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    return data.get("AccountID") or data.get("accountId")
        except aiohttp.ClientError as err:
            _LOGGER.warning("APS: Failed to fetch account ID: %s", err)
        return None
