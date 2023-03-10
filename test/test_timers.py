####################################################################################
# Copyright (c) 2023 ThingWala                                                     #
####################################################################################
from thingwala.geyserwala import GeyserwalaAsyncClient


async def test_timers1(ip):

    gw = GeyserwalaAsyncClient(ip)
    timers = await gw.async_list_timers()

    t = await gw.async_get_timer(t['id'])
    print("get   ", t)
    t['dow'][0] = not t['dow'][0]
    t['dow'][1] = not t['dow'][1]
    t['dow'][2] = not t['dow'][2]
    t['dow'][3] = not t['dow'][3]
    t['dow'][4] = not t['dow'][4]
    t['dow'][5] = not t['dow'][5]
    t['dow'][6] = not t['dow'][6]

    print("update", t)
    t = await gw.async_update_timer(t)
    print("update", t)

    t = await gw.async_delete_timer(timers[-1]['id'])
    print("delete", t)

    t = {'begin': [12,34], 'end': [13,45], 'temp': 33, 'dow': [False, False, False, True, False, False, False]}
    t = await gw.async_add_timer(t)
    print("add   ", t)
    t = {'begin': [23,14], 'end': [23,46], 'temp': 33, 'dow': [True, True, True, False, True, True, True]}
    t = await gw.async_add_timer(t)
    print("add   ", t)
