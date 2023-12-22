####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
import asyncio
import logging
import time

from contextlib import asynccontextmanager
from copy import deepcopy

import aiohttp

from thingwala.geyserwala.const import (
    GEYSERWALA_MODES,
    GEYSERWALA_MODE_SETPOINT,
    GEYSERWALA_MODE_TIMER,
    GEYSERWALA_MODE_SOLAR,
    GEYSERWALA_MODE_STANDBY,
    GEYSERWALA_MODE_HOLIDAY,
)
from thingwala.geyserwala.errors import RequestError, Unauthorized

logger = logging.getLogger(__name__)


class GeyserwalaClientAsync:
    _base_keys = [
        "id",
        "name",
        "version",
        "features",
        "status",
        "mode",
        "tank-temp",
        "element-demand",
    ]

    def __init__(
        self, host, username=None, password=None, port=80, session=None
    ) -> None:
        self._scheme = "http"
        self._host = host
        self._port = port
        self._user = username or "admin"
        self._pass = password or ""
        self._rest_timeout = 10
        self._lock = asyncio.Lock()
        self._session = session or aiohttp.ClientSession()
        self._values = {}
        self._last_update = 0
        self._cache_time = 0.5
        self._subscriptions = []

    async def close(self):
        await self._session.close()

    @property
    def authorized(self):
        return getattr(self._session, "_token", None) is not None

    async def _value_callback(self, value):
        if asyncio.iscoroutinefunction(value):
            return await value()
        if callable(value):
            return value()
        return value

    async def login(self, username, password):
        self._user = username
        self._pass = password
        password = await self._value_callback(self._pass)
        rsp = await self._json_req(
            "POST", "api/session", json={"username": self._user, "password": password}
        )
        if not rsp:
            self._session._token = None
            return False
        try:
            if rsp["success"] is True:
                self._session._token = rsp["token"]
                return True
        except KeyError as ex:
            logger.warning("Malformed response to auth request: %s", ex)
        return False

    async def logout(self):
        rsp = await self._json_req("DELETE", "api/session")
        if not rsp:
            return False
        if rsp["success"] is True:
            self._session._token = None
            return True
        return False

    @asynccontextmanager
    async def _auth(self):
        if not self.authorized:
            if not await self.login(self._user, self._pass):
                raise Unauthorized()
        yield

    async def _json_req(self, method: str, path: str, params=None, json=None):
        params = params or {}
        logger.debug("req: %s %s %s %s", method, path, params, json)
        try:
            async with self._lock:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                if hasattr(self._session, "_token"):
                    headers["Authorization"] = f"Bearer {self._session._token}"

                url = f"{self._scheme}://{self._host}:{self._port}/{path}"
                async with self._session.request(
                    method=method,
                    headers=headers,
                    url=url,
                    params=params,
                    json=json,
                    timeout=self._rest_timeout,
                ) as rsp:
                    status = rsp.status
                    if status == 200:
                        json_blob = await rsp.json()
                        return json_blob
        except asyncio.TimeoutError as ex:
            raise RequestError from ex
        except (
            aiohttp.ClientError,
            aiohttp.http_exceptions.HttpProcessingError,
        ) as ex:
            logger.debug(
                "aiohttp exception %s on %s %s [%s]: %s",
                ex.__class__.__name__,
                method,
                url,
                getattr(ex, "status", None),
                getattr(ex, "message", None),
            )
            raise RequestError() from ex
        except Exception as ex:
            logger.exception(
                "Non-aiohttp exception occured:  %s", ex
            )
            raise RequestError from ex
        if status == 401:
            if hasattr(self._session, "_token"):
                delattr(self._session, "_token")
            raise Unauthorized()
        raise RequestError(f"Unexpected status: {status}")

    def subscribe(self, key):
        if key not in self._subscriptions:
            self._subscriptions.append(key)

    def unsubscribe(self, key):
        if key in self._base_keys:
            return
        self._subscriptions.remove(key)

    async def update(self):
        keys = list(self._base_keys)
        keys.extend(self._subscriptions)
        return await self._update_keys(keys)

    async def _update_keys(self, keys):
        now = self._now()
        if (self._last_update + self._cache_time) > now:
            return True

        async with self._auth():
            rsp = await self._json_req("GET", "api/value", params={"f": ",".join(keys)})
            if rsp:
                self._values.update(rsp)
                self._last_update = now
                return True
            return False

    def _now(self):
        return time.time()

    async def _set_value(self, key, value):
        async with self._auth():
            ret = await self._json_req("PATCH", "api/value", json={key: value})
            if ret and ret[key] == value:
                self._values.update(ret)
                return True
            return False

    def get_value(self, key):
        return self._values.get(key)

    async def set_value(self, key, value):
        return await self._set_value(key, value)

    @property
    def id(self):
        return self._values.get("id", "?")

    @property
    def name(self):
        return self._values.get("name", "?")

    @property
    def version(self):
        return self._values.get("version", "?")

    def has_feature(self, key):
        try:
            return self._values.get("features", {})[key]
        except KeyError:
            return False

    @property
    def status(self):
        return self._values.get("status", "?")

    @property
    def tank_temp(self):
        return self._values.get("tank-temp", -25)

    @property
    def element_demand(self):
        return self._values.get("element-demand", False)

    @property
    def modes(self):
        modes = []
        modes.append(GEYSERWALA_MODE_SETPOINT)
        modes.append(GEYSERWALA_MODE_TIMER)
        if self.has_feature("f-collector") or self.has_feature("f-pv-panel"):
            modes.append(GEYSERWALA_MODE_SOLAR)
        else:
            modes.append(GEYSERWALA_MODE_STANDBY)
        modes.append(GEYSERWALA_MODE_HOLIDAY)
        return modes

    @property
    def mode(self):
        return self._values.get("mode", "?")

    async def set_mode(self, mode: str):
        if mode in GEYSERWALA_MODES:
            return await self._set_value("mode", mode)
        return False

    async def add_timer(self, timer: dict):
        timer = deepcopy(timer)
        timer["id"] = 0
        async with self._auth():
            ret = await self._json_req("POST", "api/value/timer", json=timer)
            return ret["id"]

    async def list_timers(self):
        async with self._auth():
            ret = await self._json_req("GET", "api/value/timer")
            return ret

    async def get_timer(self, idx: int):
        async with self._auth():
            ret = await self._json_req("GET", f"api/value/timer/{idx}")
            return ret

    async def update_timer(self, timer: dict):
        async with self._auth():
            ret = await self._json_req(
                "PUT", f"api/value/timer/{timer['id']}", json=timer
            )
            return ret

    async def delete_timer(self, idx: int):
        async with self._auth():
            ret = await self._json_req("DELETE", f"api/value/timer/{idx}")
            return ret["success"] is True and ret["id"] == idx
