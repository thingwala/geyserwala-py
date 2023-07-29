####################################################################################
# Copyright (c) 2023 Thingwala                                                     #
####################################################################################
from zeroconf import ServiceBrowser, Zeroconf


class MdnsListener:

    def remove_service(self, zeroconf, type, name):
        print("removed: %s" % (name,))

    def update_service(self, zeroconf, type, name):
        print("Updated: %s" % (name,))

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        print("Added: %s -> %s" % (name, info))


zeroconf = Zeroconf()
listener = MdnsListener()
browser = ServiceBrowser(zeroconf, "_geyserwala._tcp.local.", listener)
try:
    input("Press enter to exit...\n\n")
finally:
    zeroconf.close()
