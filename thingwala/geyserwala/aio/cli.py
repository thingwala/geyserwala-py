####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
import logging
import sys
import asyncio

from thingwala.geyserwala.aio.client import GeyserwalaClientAsync
from thingwala.geyserwala.aio.discovery import GeyserwalaDiscoveryAsync


root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
root.addHandler(handler)


async def status(ip, username="admin", password=""):
    gw = GeyserwalaClientAsync(ip, username, password)
    try:
        while True:
            await gw.update_status()
            if not gw.authorized:
                return
            print("---")
            print(f"Geyserwala [{ip}]")
            print(f"Name: {gw.name}")
            print(f"Time: {gw.time}")
            print(f"Status: {gw.status}")
            pump = "RUNNING" if gw.pump_status else "STOPPED"
            print(
                f"Water: {gw.tank_temp}  Collector: {gw.collector_temp}  Pump: {pump}"
            )
            boost = "YES" if gw.boost_demand else "NO "
            element = "ON" if gw.element_demand else "OFF"
            print(f"Boost: {boost}   Setpoint: {gw.setpoint}  Element: {element}")
            print("Mode:", gw.mode)

            await asyncio.sleep(2)
    finally:
        await gw.close()


async def timers(ip, username="admin", password=""):
    gw = GeyserwalaClientAsync(ip, username, password)
    try:
        items = await gw.list_timers()
        for timer in items:
            print(timer)

    finally:
        await gw.close()


async def discover():
    gw = GeyserwalaDiscoveryAsync()
    return await gw.mdns_discover()


async def main(args):
    if args[0] == "discover":
        res = await discover()
        if not res:
            print("None found")
        else:
            for r in res:
                print(r)
    elif args[0] == "status":
        await status(*args[1:])
    elif args[0] == "timers":
        await timers(*args[1:])
    else:
        print(f"Unknown command: {args[0]}")


def cli():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(sys.argv[1:]))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
