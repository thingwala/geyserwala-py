####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
import asyncio

from dataclasses import dataclass
import logging

from zeroconf import IPVersion
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf

logger = logging.getLogger(__name__)


@dataclass
class Device:
    ip: str
    port: int
    hostname: str
    properties: dict[str, str]


class GeyserwalaDiscoveryAsync:
    async def mdns_discover(self, timeout=10) -> None:
        devices = []
        services = "_geyserwala._tcp.local."
        aio_zc = AsyncZeroconf(ip_version=IPVersion.V4Only)
        try:
            found = []

            def _handler(_zeroconf, service_type, name, state_change):
                if state_change.name == "Added":
                    found.append((service_type, name))

            aio_browser = AsyncServiceBrowser(
                aio_zc.zeroconf,
                services,
                handlers=[_handler],
            )

            await asyncio.sleep(timeout)
            await aio_browser.async_cancel()

            for service_type, name in found:
                info = await aio_zc.async_get_service_info(service_type, name)
                properties = {
                    k.decode("utf-8"): v.decode("utf-8")
                    for k, v in info.properties.items()
                }
                devices.append(
                    Device(
                        info.parsed_addresses()[0], info.port, info.server, properties
                    )
                )

        finally:
            await aio_zc.async_close()

        return devices
