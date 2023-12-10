####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
import pytest
import os

from thingwala.geyserwala.aio.client import GeyserwalaClientAsync


@pytest.fixture
def ip():
    return os.environ['TEST_IP']


@pytest.mark.asyncio
async def test_timers1(ip):

    gw = GeyserwalaClientAsync(ip)
    timers = await gw.list_timers()
    t = timers[0]

    t = await gw.get_timer(t['id'])
    print("get   ", t)
    t['dow'][0] = not t['dow'][0]
    t['dow'][1] = not t['dow'][1]
    t['dow'][2] = not t['dow'][2]
    t['dow'][3] = not t['dow'][3]
    t['dow'][4] = not t['dow'][4]
    t['dow'][5] = not t['dow'][5]
    t['dow'][6] = not t['dow'][6]

    print("update", t)
    t = await gw.update_timer(t)
    print("update", t)

    t = await gw.delete_timer(timers[-1]['id'])
    print("delete", t)

    t = {'begin': [12,34], 'end': [13,45], 'temp': 33, 'dow': [False, False, False, True, False, False, False]}
    t = await gw.add_timer(t)
    print("add   ", t)
    t = {'begin': [23,14], 'end': [23,46], 'temp': 33, 'dow': [True, True, True, False, True, True, True]}
    t = await gw.add_timer(t)
    print("add   ", t)
