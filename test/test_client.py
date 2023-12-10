####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
import asyncio
import pytest
import os

from thingwala.geyserwala.aio.client import GeyserwalaClientAsync

from thingwala.geyserwala.const import (
    GEYSERWALA_MODE_TIMER,
    GEYSERWALA_MODE_HOLIDAY,
)


@pytest.fixture
def ip():
    return os.environ['TEST_IP']


@pytest.mark.asyncio
async def test_client(ip):
    gw = GeyserwalaClientAsync(ip)

    await gw.update_status()
    assert gw.name == "Geyserwala"
    gw.status
    gw.pump_status
    gw.tank_temp
    gw.collector_temp
    gw.boost_demand
    gw.element_demand
    gw.setpoint
    gw.mode

    await gw.set_mode(GEYSERWALA_MODE_TIMER)
    await gw.set_setpoint(65)
    await gw.set_boost_demand(True)
    await asyncio.sleep(2)
    await gw.set_boost_demand(True)
    await gw.set_mode(GEYSERWALA_MODE_HOLIDAY)
