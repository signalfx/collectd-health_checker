#!/usr/bin/env python

import requests

try:
    import collectd
except ImportError:
    import dummy_collectd as collectd

PLUGIN_NAME = 'health_checker'
SEND = True
PLUGIN_INSTANCE = ''
TYPE = 'gauge'


def log(param):
    if __name__ != '__main__':
        collectd.info("%s: %s" % (PLUGIN_NAME, param))
    else:
        sys.stderr.write("%s\n" % param)


def config(conf):
    for val in conf.children:
        if val.key == 'HEALTH_URL':
            global HEALTH_URL
            HEALTH_URL = val.values[0]
        if val.key == 'Instance':
            global INSTANCE
            INSTANCE = val.values[0]


def _get_http_response(HEALTH_URL):
    try:
        return requests.get(HEALTH_URL).status_code
    except:
        return 0


def read():
    val = _get_http_response(HEALTH_URL)
    collectd.Values(plugin=PLUGIN_NAME,
                    type_instance="service.health",
                    plugin_instance=INSTANCE,
                    type=TYPE,
                    values=[val]).dispatch()


def init():
    log("Plugin %s initializing..." % PLUGIN_NAME)


def shutdown():
    log("Plugin %s shutting down..." % PLUGIN_NAME)


if __name__ != '__main__':
    # when running inside plugin register each callback
    collectd.register_init(init)
    collectd.register_config(config)
    collectd.register_read(read)
    collectd.register_shutdown(shutdown)
else:
    # outside plugin just collect the info
    read()
    if len(sys.argv) < 2:
        while True:
            time.sleep(10)
            read()
