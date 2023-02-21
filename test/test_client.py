####################################################################################
# Copyright (c) 2023 ThingWala                                                     #
####################################################################################
import asyncio

from thingwala.geyserwala import GeyserwalaAsyncClient

from thingwala.geyserwala.const import (
    GEYSERWALA_MODE_TIMER,
    GEYSERWALA_MODE_HOLIDAY,
)


async def test_client(ip):
    gw = GeyserwalaAsyncClient(ip)

    await gw.update_status_async()
    assert gw.name == "Geyserwala"
    assert len(gw.time) == 5
    gw.status
    gw.pump_status
    gw.tank_temp
    gw.collector_temp
    gw.boost
    gw.element_demand
    gw.setpoint
    gw.mode

    await gw.set_mode_async(GEYSERWALA_MODE_TIMER)
    await gw.set_setpoint_async(65)
    await gw.set_boost_async(True)
    await asyncio.sleep(2)
    await gw.set_boost_async(True)
    await gw.set_mode_async(GEYSERWALA_MODE_HOLIDAY)
