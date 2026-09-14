"""Talk to the Xiaomi cloud to look up a device token.

The login protocol here follows Piotr Machowski's Xiaomi-cloud-tokens-extractor
(https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor, MIT licensed).
It is reimplemented on aiohttp so it runs on the event loop like the rest of
Home Assistant, and on a local RC4 so no crypto dependency has to be added.
"""
# pylint: disable=import-error
import asyncio
import base64
import hashlib
import json
import logging
import os
import random
import time
from typing import Any, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

SERVER_COUNTRIES = ["cn", "de", "us", "ru", "tw", "sg", "in", "i2"]
DEFAULT_COUNTRY = "de"

LOGIN_URL = "https://account.xiaomi.com/longPolling/loginUrl"

# How long a single long-poll request waits before it is retried.
_POLL_TIMEOUT = 30


class XiaomiCloudException(Exception):
    """Raised when the cloud cannot be reached or refuses the request."""


def _rc4_drop1024(key: bytes, data: bytes) -> bytes:
    """RC4 with the first 1024 keystream bytes discarded.

    Xiaomi uses this to obfuscate request parameters and responses. It is not
    a security boundary here -- the transport is HTTPS -- so a small local
    implementation is preferable to depending on a cipher that cryptography
    has already moved to hazmat.decrepit and announced for removal.
    """
    state = list(range(256))
    j = 0
    for i in range(256):
        j = (j + state[i] + key[i % len(key)]) & 0xFF
        state[i], state[j] = state[j], state[i]

    out = bytearray(len(data) + 1024)
    i = j = 0
    for n in range(len(out)):
        i = (i + 1) & 0xFF
        j = (j + state[i]) & 0xFF
        state[i], state[j] = state[j], state[i]
        keystream = state[(state[i] + state[j]) & 0xFF]
        out[n] = keystream if n < 1024 else data[n - 1024] ^ keystream

    return bytes(out[1024:])


def _encrypt_rc4(password: str, payload: str) -> str:
    return base64.b64encode(
        _rc4_drop1024(base64.b64decode(password), payload.encode())
    ).decode()


def _decrypt_rc4(password: str, payload: str) -> bytes:
    return _rc4_drop1024(base64.b64decode(password), base64.b64decode(payload))


def _to_json(text: str) -> Any:
    """Xiaomi prefixes its JSON responses with a guard string."""
    return json.loads(text.replace("&&&START&&&", ""))


class XiaomiCloud:
    """A single Xiaomi cloud session, logged in by scanning a QR code."""

    def __init__(self, country: str = DEFAULT_COUNTRY) -> None:
        """Initialize the connector."""
        self.country = country
        self.user_id: Optional[str] = None

        self._agent = self._generate_agent()
        self._device_id = self._generate_device_id()
        self._ssecurity: Optional[str] = None
        self._service_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

        # Filled in by async_start_login, consumed by async_wait_for_scan.
        self.login_url: Optional[str] = None
        self.qr_image: Optional[bytes] = None
        self._long_polling_url: Optional[str] = None
        self._timeout: int = 300

    # -- session handling --------------------------------------------------

    async def async_open(self) -> None:
        """Open the underlying HTTP session."""
        self._session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )

    async def __aenter__(self) -> "XiaomiCloud":
        """Open the underlying HTTP session."""
        await self.async_open()
        return self

    async def __aexit__(self, *_exc) -> None:
        """Close the underlying HTTP session."""
        await self.async_close()

    async def async_close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    # -- login -------------------------------------------------------------

    async def async_start_login(self) -> str:
        """Ask for a login QR code and return the URL it encodes."""
        params = {
            "_qrsize": "480",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "callback": "https://sts.api.io.mi.com/sts",
            "_hasLogo": "false",
            "sid": "xiaomiio",
            "serviceParam": "",
            "_locale": "en_GB",
            "_dc": str(int(time.time() * 1000)),
        }

        try:
            async with self._session.get(LOGIN_URL, params=params) as response:
                if response.status != 200:
                    raise XiaomiCloudException(
                        f"Could not request a login QR code (HTTP {response.status})"
                    )
                data = _to_json(await response.text())
        except aiohttp.ClientError as ex:
            raise XiaomiCloudException(f"Could not reach the Xiaomi login service: {ex}") from ex

        if "qr" not in data or "lp" not in data:
            raise XiaomiCloudException("The login service did not return a QR code")

        self.login_url = data["loginUrl"]
        self._long_polling_url = data["lp"]
        self._timeout = int(data.get("timeout", 300))

        # Fetch the rendered code so the config flow can show it inline
        # instead of sending the user to an external URL.
        try:
            async with self._session.get(data["qr"]) as response:
                if response.status == 200:
                    self.qr_image = await response.read()
        except aiohttp.ClientError:
            _LOGGER.debug("Could not download the QR image, falling back to the URL")

        return self.login_url

    async def async_wait_for_scan(self) -> None:
        """Long-poll until the QR code has been scanned and confirmed."""
        deadline = time.time() + self._timeout

        while time.time() < deadline:
            try:
                async with self._session.get(
                    self._long_polling_url,
                    timeout=aiohttp.ClientTimeout(total=_POLL_TIMEOUT),
                ) as response:
                    if response.status != 200:
                        _LOGGER.debug("Long poll returned HTTP %s, retrying", response.status)
                        continue
                    data = _to_json(await response.text())
            except asyncio.TimeoutError:
                # Expected: the server holds the request open until something
                # happens, and returns nothing if the user has not scanned yet.
                continue
            except aiohttp.ClientError as ex:
                raise XiaomiCloudException(f"Login polling failed: {ex}") from ex

            self.user_id = data["userId"]
            self._ssecurity = data["ssecurity"]
            await self._async_fetch_service_token(data["location"])
            return

        raise XiaomiCloudException("The QR code expired before it was scanned")

    async def _async_fetch_service_token(self, location: str) -> None:
        """Exchange the login location for a service token."""
        try:
            async with self._session.get(
                location,
                headers={"content-type": "application/x-www-form-urlencoded"},
            ) as response:
                if response.status != 200:
                    raise XiaomiCloudException(
                        f"Could not fetch a service token (HTTP {response.status})"
                    )
                for cookie in self._session.cookie_jar:
                    if cookie.key == "serviceToken":
                        self._service_token = cookie.value
        except aiohttp.ClientError as ex:
            raise XiaomiCloudException(f"Could not fetch a service token: {ex}") from ex

        if not self._service_token:
            raise XiaomiCloudException("The login did not yield a service token")

    # -- device lookup -----------------------------------------------------

    async def async_get_devices(self) -> list[dict]:
        """Return every device on the account, across all of its homes."""
        devices: list[dict] = []

        homes = await self._async_api_call(
            "/v2/homeroom/gethome",
            '{"fg": true, "fetch_share": true, "fetch_share_dev": true,'
            ' "limit": 300, "app_ver": 7}',
        )

        for home in (homes or {}).get("result", {}).get("homelist", []):
            result = await self._async_api_call(
                "/v2/home/home_device_list",
                '{"home_owner": ' + str(self.user_id)
                + ', "home_id": ' + str(home["id"])
                + ', "limit": 200, "get_split_device": true,'
                ' "support_smart_home": true}',
            )
            devices.extend((result or {}).get("result", {}).get("device_info", []))

        return devices

    async def _async_api_call(self, path: str, data: str) -> Optional[dict]:
        """POST an encrypted API request and decrypt the response."""
        base = "https://" + ("" if self.country == "cn" else f"{self.country}.") + "api.io.mi.com/app"
        url = base + path

        millis = round(time.time() * 1000)
        nonce = self._generate_nonce(millis)
        signed_nonce = self._signed_nonce(nonce)
        fields = self._generate_enc_params(
            url, "POST", signed_nonce, nonce, {"data": data}, self._ssecurity
        )

        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        cookies = {
            "userId": str(self.user_id),
            "yetAnotherServiceToken": str(self._service_token),
            "serviceToken": str(self._service_token),
            "locale": "en_GB",
            "timezone": "GMT+02:00",
            "is_daylight": "1",
            "dst_offset": "3600000",
            "channel": "MI_APP_STORE",
        }

        try:
            async with self._session.post(
                url, headers=headers, cookies=cookies, params=fields
            ) as response:
                if response.status != 200:
                    raise XiaomiCloudException(
                        f"Device lookup failed (HTTP {response.status})"
                    )
                decoded = _decrypt_rc4(
                    self._signed_nonce(fields["_nonce"]), await response.text()
                )
        except aiohttp.ClientError as ex:
            raise XiaomiCloudException(f"Device lookup failed: {ex}") from ex

        return json.loads(decoded)

    # -- signing helpers ---------------------------------------------------

    def _signed_nonce(self, nonce: str) -> str:
        digest = hashlib.sha256(
            base64.b64decode(self._ssecurity) + base64.b64decode(nonce)
        ).digest()
        return base64.b64encode(digest).decode()

    @staticmethod
    def _generate_nonce(millis: int) -> str:
        nonce_bytes = os.urandom(8) + int(millis / 60000).to_bytes(4, byteorder="big")
        return base64.b64encode(nonce_bytes).decode()

    @staticmethod
    def _generate_agent() -> str:
        agent_id = "".join(chr(random.randint(65, 69)) for _ in range(13))  # nosec
        random_text = "".join(chr(random.randint(97, 122)) for _ in range(18))  # nosec
        return f"{random_text}-{agent_id} APP/com.xiaomi.mihome APPV/10.5.201"

    @staticmethod
    def _generate_device_id() -> str:
        return "".join(chr(random.randint(97, 122)) for _ in range(6))  # nosec

    @staticmethod
    def _generate_enc_signature(url: str, method: str, signed_nonce: str, params: dict) -> str:
        parts = [str(method).upper(), url.split("com")[1].replace("/app/", "/")]
        parts.extend(f"{key}={value}" for key, value in params.items())
        parts.append(signed_nonce)
        return base64.b64encode(
            hashlib.sha1("&".join(parts).encode()).digest()  # nosec - required by the API
        ).decode()

    @classmethod
    def _generate_enc_params(
        cls,
        url: str,
        method: str,
        signed_nonce: str,
        nonce: str,
        params: dict,
        ssecurity: str,
    ) -> dict:
        params["rc4_hash__"] = cls._generate_enc_signature(url, method, signed_nonce, params)
        for key, value in params.items():
            params[key] = _encrypt_rc4(signed_nonce, value)
        params.update(
            {
                "signature": cls._generate_enc_signature(url, method, signed_nonce, params),
                "ssecurity": ssecurity,
                "_nonce": nonce,
            }
        )
        return params
