####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
import logging
import asyncio
import curses
import time
import threading
import socket
import sys

from contextlib import asynccontextmanager

from aiohttp import web
from zeroconf.asyncio import AsyncZeroconf
from zeroconf import ServiceInfo, IPVersion

from thingwala.geyserwala.const import (
    GEYSERWALA_MODE_HOLIDAY,
    GEYSERWALA_MODE_SOLAR,
    GEYSERWALA_MODE_TIMER,
    GEYSERWALA_MODE_SETPOINT,
)


logger = logging.getLogger("mock-geyserwala")

PORT=8082
HOSTNAME="geyserwala_mock"
BIND="127.0.0.1"

class Server:
    def __init__(self, hostname=None, port=None, bind=None) -> None:
        self._port = int(port or PORT)
        self._bind = bind or BIND
        self._on_update = None
        self._run = True
        self.value = {}

        self.value['id'] = "0123456789" + str(self._port)
        self.value['name'] = "Mock-" + str(self._port)
        self.value['hostname'] = hostname or HOSTNAME
        self.value['time'] = "12:34"
        self.value['version'] = "0.0.1"
        self.value['status'] = "Idle"
        self.value['mode'] = "SOLAR"
        self.value['tank-temp'] = 45
        self.value['collector-temp'] = 40
        self.value['setpoint'] = 50
        self.value['pump-status'] = False
        self.value['element-demand'] = False
        self.value['boost-demand'] = False
        self.value['remote-demand'] = False
        self.value['remote-disable'] = False
        self.value['remote-setpoint'] = 55

    def on_update(self, on_update):
        self._on_update = on_update or (lambda:None)

    async def handle_root(self, request):
        return web.json_response(
            data={"success": False, "message": "Not found"},
            status=404
        )

    async def handle_post_session(self, request):
        return web.json_response(data={"success": True, "token": self.value['id']})

    def _authed(self, request):
        try:
            return request.headers['Authorization'] == f"Bearer {self.value['id']}"
        except KeyError:
            return False

    def _unauthorised(self):
        return web.json_response(
            data={"success": False, "message": "Unauthorized"},
            status=401
        )

    async def handle_get_value(self, request):
        if not self._authed(request):
            return self._unauthorised()

        if 'f' in request.query:
            blob = {}
            for key in request.query['f'].split(','):
                try:
                    blob[key] = self.value[key]
                except KeyError:
                    pass
            return web.json_response(data=blob)

        return web.json_response(
            data={"success": False, "message": "Not found"},
            status=404
        )

    async def handle_patch_value(self, request):
        if not self._authed(request):
            return self._unauthorised()

        blob = await request.json()
        for key in list(blob.keys()):
            if key in self.value:
                self.value[key] = blob[key]
            else:
                del blob[key]
        self._on_update()
        return web.json_response(data=blob)

    async def register_mdns(self):
        logger.info('Registering mDNS %s ', self.value['hostname'])
        aio_zc = AsyncZeroconf(ip_version=IPVersion.V4Only)


        info = ServiceInfo('_geyserwala._tcp.local.',
                            name=f"{self.value['hostname']}._geyserwala._tcp.local.",
                            port=self._port,
                            addresses=[socket.inet_aton(self._bind)],
                            server=f"{self.value['hostname']}.local.",
                            properties={
                                "id": self.value['id'],
                            },
                          ) 
        await aio_zc.async_register_service(info)

    async def run(self):
        app = web.Application()
        app.router.add_get('/', self.handle_root)
        app.router.add_post('/api/session', self.handle_post_session)
        app.router.add_get('/api/value', self.handle_get_value)
        app.router.add_patch('/api/value', self.handle_patch_value)

        runner = web.AppRunner(app)
        try:
            await runner.setup()
            site = web.TCPSite(runner, self._bind, self._port)
            await site.start()

            logger.info("Listening on %s:%s", self._bind, self._port)

            while self._run:
                await asyncio.sleep(2)
                continue
        except Exception as ex:
            logger.exception("Server::run")
        finally:
            await runner.cleanup()


class Display():
    def __init__(self, stdscr, gw) -> None:
        self._stdscr = stdscr
        self._gw = gw
        self._run = True
        self._l = asyncio.get_event_loop()
        self._kb_q = asyncio.Queue()
        self._kb_t = threading.Thread(target=self._kb_thread)
        # self._kb_t = asyncio.to_thread(self._kb_thread)  # Available in Python 3.9
        self._kb_t.start()
        
        curses.curs_set(0)
        self._refresh()

    async def run(self):
        async def _loop():        
            while self._run:
                key = await self._kb_q.get()
                self.on_key(key)
                self._refresh()

        self._loop = asyncio.create_task(_loop())
        await asyncio.gather(
            self._loop,
        )

    def close(self):
        self._run = False
        self._loop.cancel()
        self._kb_t.join(timeout=1000)

    def _kb_thread(self):
        curses.noecho()
        self._stdscr.nodelay(True)
        try:
            while self._run:
                time.sleep(0.2)
                key = self._stdscr.getch()
                if key != curses.ERR:
                    self._l.call_soon_threadsafe(self._kb_q.put_nowait, key)
        finally:
            pass

    def refresh(self):
        self._l.call_soon_threadsafe(self._kb_q.put_nowait, None)

    def _refresh(self):
        def t(s):
            return str(s) + '      '
        self._stdscr.addstr(0, 0, f"Geyserwala Mock [{self._gw._bind}:{self._gw._port}]", curses.A_REVERSE)

        self._stdscr.addstr(2, 0, t("Name: " + self._gw.value['name']))
        self._stdscr.addstr(3, 0, t("ID: " + self._gw.value['id']))
        self._stdscr.addstr(4, 0, t("Time: " + self._gw.value['time']))
        self._stdscr.addstr(5, 0, t("Hostname: " + self._gw.value['hostname']))
        self._stdscr.addstr(6, 0, t("Status: " + self._gw.value['status']))
        self._stdscr.addstr(7, 0, t("(1,2,3,4) Mode: " + self._gw.value['mode']))
        self._stdscr.addstr(8, 0, t("(q,a) Setpoint:      " + str(self._gw.value['setpoint'])))
        self._stdscr.addstr(9, 0, t("(w,s) Water Temp:     " + str(self._gw.value['tank-temp'])))
        self._stdscr.addstr(10, 0, t("(e,d) Collector Temp: " + str(self._gw.value['collector-temp'])))
        self._stdscr.addstr(11, 0, t("(p) Pump:    " + ("RUNNING" if self._gw.value['pump-status'] else "STOPPED")))
        self._stdscr.addstr(12, 0, t("(h) Element: " + ("ON" if self._gw.value['element-demand'] else "OFF")))
        self._stdscr.addstr(13, 0, t("(b) Boost:   " + ("ON" if self._gw.value['boost-demand'] else "OFF")))
        self._stdscr.addstr(15, 0, t(f"(r) Register mDNS ({self._gw.value['hostname']})"))

    def on_key(self, key):
        if key is None:
            pass
        elif key == 27:
            self._run = False
        elif key == ord('r'):
            asyncio.create_task(self._gw.register_mdns())
        elif key == ord('q'):
            self._gw.value['setpoint'] += 1
        elif key == ord('a'):
            self._gw.value['setpoint'] -= 1

        elif key == ord('w'):
            self._gw.value['tank-temp'] += 1
        elif key == ord('s'):
            self._gw.value['tank-temp'] -= 1

        elif key == ord('e'):
            self._gw.value['collector-temp'] += 1
        elif key == ord('d'):
            self._gw.value['collector-temp'] -= 1

        elif key == ord('b'):
            self._gw.value['boost-demand'] = not self._gw.value['boost-demand']

        elif key == ord('h'):
            self._gw.value['element-demand'] = not self._gw.value['element-demand']

        elif key == ord('p'):
            self._gw.value['pump-status'] = not self._gw.value['pump-status']

        elif key == ord('1'):
            self._gw.value['mode'] = GEYSERWALA_MODE_HOLIDAY
        elif key == ord('2'):
            self._gw.value['mode'] = GEYSERWALA_MODE_SOLAR
        elif key == ord('3'):
            self._gw.value['mode'] = GEYSERWALA_MODE_TIMER
        elif key == ord('4'):
            self._gw.value['mode'] = GEYSERWALA_MODE_SETPOINT
        elif key == ord(' '):
            pass


def display(port=None):
    setup_file_logger()

    async def _coro(stdscr):
        gw = Server(port=port)
        dsp = Display(stdscr, gw)
        def _up():
            dsp.refresh()
        gw.on_update(_up)
        await asyncio.gather(
            asyncio.create_task(gw.register_mdns(), name='mDNS'),
            asyncio.create_task(gw.run(), name='Server'),
            asyncio.create_task(dsp.run()),
        )

    def _display(stdscr):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_coro(stdscr))

    curses.wrapper(_display)


def server(port=None):
    setup_cli_logger()

    async def _coro():
        gw = Server(port=port)
        await asyncio.gather(
            asyncio.create_task(gw.register_mdns(), name='mDNS'),
            asyncio.create_task(gw.run(), name='Server'),
        )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_coro())


def setup_file_logger(filename='gw.log'):
    logging.basicConfig(filename=filename,
                       filemode='a',
                       format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                       datefmt='%H:%M:%S',
                       level=logging.DEBUG)

def setup_cli_logger():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)


def main():
    try:
        display(*sys.argv[1:])
        # server(*sys.argv[1:])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
