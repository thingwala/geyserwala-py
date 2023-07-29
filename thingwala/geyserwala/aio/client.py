####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
import logging
import asyncio

from contextlib import asynccontextmanager

import aiohttp

from thingwala.geyserwala.errors import Unauthorized, RequestError
from thingwala.geyserwala.const import (
    GEYSERWALA_MODES,
    GEYSERWALA_MODE_SETPOINT,
    GEYSERWALA_MODE_TIMER,
    GEYSERWALA_MODE_SOLAR,
    GEYSERWALA_MODE_HOLIDAY,
    GEYSERWALA_MODE_STANDBY,
    GEYSERWALA_SETPOINT_TEMP_MAX,
    GEYSERWALA_SETPOINT_TEMP_MIN,
)


logger = logging.getLogger(__name__)


class GeyserwalaClientAsync:
    def __init__(self, host, username=None, password=None, port=80, session=None) -> None:
        self._scheme = "http"
        self._host = host
        self._port = port
        self._user = username or "admin"
        self._pass = password or ""
        self._rest_timeout = 10
        self._lock = asyncio.Lock()
        self._session = session or aiohttp.ClientSession()
        self._status = {}
        self._status_values = [
            "features",
            "id",
            "version",
            "name",
            "hostname",
            "time",
            "status",
            "tank-temp",
            "collector-temp",
            "pump-status",
            "boost-demand",
            "setpoint",
            "element-demand",
            "mode",
            "external-demand",
            "external-setpoint",
            "lowpower-enable",
        ]

    async def close(self):
        await self._session.close()

    @property
    def authorized(self):
        return getattr(self._session, '_token', None) is not None

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
        rsp = await self._json_req('POST', 'api/session', json={'username': self._user, 'password': password})
        if not rsp:
            self._session._token = None
            return False
        if rsp['success'] is True:
            self._session._token = rsp['token']
            return True
        return False

    async def logout(self):
        rsp = await self._json_req('DELETE', 'api/session')
        if not rsp:
            return False
        if rsp['success'] is True:
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
        logger.debug('req: %s %s %s %s', method, path, params, json)
        try:
            async with self._lock:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                if hasattr(self._session, '_token'):
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
        except (
            aiohttp.ClientError,
            aiohttp.http_exceptions.HttpProcessingError,
        ) as ex:
            logger.error(
                "aiohttp exception on %s %s [%s]: %s",
                method,
                url,
                getattr(ex, "status", None),
                getattr(ex, "message", None),
            )
            raise RequestError() from ex
        except Exception as ex:
            logger.exception(
                "Non-aiohttp exception occured:  %s", getattr(ex, "__dict__", {})
            )
            raise RequestError from ex
        if status == 401:
            if hasattr(self._session, '_token'):
                delattr(self._session, '_token')
            raise Unauthorized()
        raise RequestError("Unexpected status: %s", status)

    async def update_status(self):
        async with self._auth():
            rsp = await self._json_req("GET", "api/value", params={"f": ','.join(self._status_values)})
            if rsp:
                self._status.update(rsp)
                return True
            return False

    async def _set_value(self, key, value):
        async with self._auth():
            ret = await self._json_req("PATCH", "api/value", json={key: value})
            if ret:
                self._status.update(ret)
                return True
            return False

    @property
    def id(self):
        return self._status.get("id", "?")

    @property
    def version(self):
        return self._status.get("version", "?")

    def has_feature(self, key):
        try:
            return self._status.get("features", {})[key]
        except KeyError:
            return False

    @property
    def name(self):
        return self._status.get("name", "?")

    @property
    def hostname(self):
        return self._status.get("hostname", "?")

    @property
    def time(self):
        return self._status.get("time", "?")

    @property
    def status(self):
        return self._status.get("status", "?")

    @property
    def tank_temp(self):
        return self._status.get("tank-temp", 0)

    @property
    def collector_temp(self):
        return self._status.get("collector-temp", 0)

    @property
    def pump_status(self):
        return self._status.get("pump-status", None)

    @property
    def boost_demand(self):
        return self._status.get("boost-demand", None)

    async def set_boost_demand(self, on: bool):
        return await self._set_value("boost-demand", on)

    @property
    def setpoint(self):
        return self._status.get("setpoint", None)

    async def set_setpoint(self, setpoint: int):
        if GEYSERWALA_SETPOINT_TEMP_MIN <= setpoint <= GEYSERWALA_SETPOINT_TEMP_MAX:
            return await self._set_value("setpoint", setpoint)
        return False

    @property
    def element_demand(self):
        return self._status.get("element-demand", None)

    @property
    def modes(self):
        modes = []
        modes.append(GEYSERWALA_MODE_SETPOINT)
        modes.append(GEYSERWALA_MODE_TIMER)
        if self.has_feature('f-collector'):
            modes.append(GEYSERWALA_MODE_SOLAR)
        if self.has_feature('f-collector'):
            modes.append(GEYSERWALA_MODE_HOLIDAY)
        if not self.has_feature('f-collector'):
            modes.append(GEYSERWALA_MODE_STANDBY)
        return modes

    @property
    def mode(self):
        return self._status.get("mode", "?")

    async def set_mode(self, mode: str):
        if mode in GEYSERWALA_MODES:
            return await self._set_value("mode", mode)
        return False

    @property
    def external_demand(self):
        return self._status.get("external-demand", None)

    async def set_external_demand(self, on: bool):
        return await self._set_value("external-demand", on)

    @property
    def external_setpoint(self):
        return self._status.get("external-setpoint", None)

    async def set_external_setpoint(self, external_setpoint: int):
        if GEYSERWALA_SETPOINT_TEMP_MIN <= external_setpoint <= GEYSERWALA_SETPOINT_TEMP_MAX:
            return await self._set_value("external-setpoint", external_setpoint)
        return False

    @property
    def lowpower_enable(self):
        return self._status.get("lowpower-enable", None)

    async def set_lowpower_enable(self, on: bool):
        return await self._set_value("lowpower-enable", on)

    async def add_timer(self, timer: dict):
        timer['id'] = 0
        async with self._auth():
            ret = await self._json_req("POST", "api/value/timer", json=timer)
            return ret

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
            ret = await self._json_req("PUT", f"api/value/timer/{timer['id']}", json=timer)
            return ret

    async def delete_timer(self, idx: int):
        async with self._auth():
            ret = await self._json_req("DELETE", f"api/value/timer/{idx}")
            return ret
