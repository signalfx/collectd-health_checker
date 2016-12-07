#!/usr/bin/env python

# This plugin is intended to be a very basic health checker for any
# type of system that can be queried via http. Right now it just does
# an http response check and parses json.  If the value for a given
# json key returns the expected value, the plugin returns 1.
# If the value for the json key is not expected, the plugin will output the
# actual value in the collectd logs and return 0.
#
# This plugin copied over customized basic service health
# checks from SignalFx's Nagios configuration

import requests
import sys
import time

try:
    import collectd
except ImportError:
    import dummy_collectd as collectd

PLUGIN_NAME = 'health_checker'
TYPE = 'gauge'
SICK_MSG = 'Service is not healthy'
MISSING_JSON_MSG = 'All JSON keys not present.  Will not collect metrics'
BAD_CONFIG = 'BadConfig'

plugin_conf = {}


def log(param):
    if __name__ != '__main__':
        collectd.info('%s: %s' % (PLUGIN_NAME, param))
    else:
        sys.stderr.write('%s\n' % param)


def config(conf):
    global plugin_conf
    required_keys = ('Instance', 'URL')
    json_keys = ('JSONKey', 'JSONVal')
    chk_json = False
    bad_conf = 0

    for val in conf.children:
        if val.key == 'HEALTH_URL':
            plugin_conf['URL'] = val.values[0]
        elif val.key == 'URL':
            plugin_conf[val.key] = val.values[0]
        elif val.key == 'JSONKey':
            plugin_conf[val.key] = val.values[0]
            chk_json = True
        elif val.key == 'JSONVal':
            plugin_conf[val.key] = val.values[0]
            chk_json = True
        elif val.key == 'Instance':
            plugin_conf[val.key] = val.values[0]
        else:
            bad_conf = 1
            log('Unknown config key: %s' % val.key)

    for key in required_keys:
        if key not in plugin_conf:
            bad_conf = 1
            log('Missing required config setting: %s' % (key))

    if chk_json and \
       len(set(json_keys).intersection(plugin_conf.keys())) != len(json_keys):
        bad_conf = 1
        log('JSON must have both keys: %s' % (json_keys,))

    if bad_conf:
        plugin_conf[BAD_CONFIG] = bad_conf


def _get_health_status(plugin_conf):
    status = 0
    val = 0
    r = None
    health_url = plugin_conf.get('URL')
    json_key = plugin_conf.get('JSONKey')
    json_val = plugin_conf.get('JSONVal')
    try:
        r = requests.get(health_url, timeout=5)
    except:
        log('%s; %s is unreachable.' % (SICK_MSG, health_url))
    if r:
        status = r.status_code
        if status == 200:
            if json_key and json_val:
                try:
                    if r.json().get(json_key) == json_val:
                        val = 1
                    else:
                        log('%s; reporting %s' % (SICK_MSG,
                                                  r.json().get(json_key)))
                except:
                    log('%s; could not read json' % (SICK_MSG))
            else:
                val = 1
    return status, val


def read():
    sval = None
    hval = None
    if BAD_CONFIG in plugin_conf:
        val = 1
        collectd.Values(plugin=PLUGIN_NAME,
                        type_instance='plugin.conf.error',
                        type=TYPE,
                        values=[val]).dispatch()

        log('Invalid config keys found.  Will not collect metrics')
        return

    if 'URL' in plugin_conf:
        sval, hval = _get_health_status(plugin_conf)

    if sval is not None and hval is not None:
        collectd.Values(plugin=PLUGIN_NAME,
                        type_instance='service.health.status',
                        plugin_instance=plugin_conf.get('Instance'),
                        type=TYPE,
                        values=[sval]).dispatch()

        collectd.Values(plugin=PLUGIN_NAME,
                        type_instance='service.health.value',
                        plugin_instance=plugin_conf.get('Instance'),
                        type=TYPE,
                        values=[hval]).dispatch()


def init():
    log('Plugin %s initializing...' % PLUGIN_NAME)


def shutdown():
    log('Plugin %s shutting down...' % PLUGIN_NAME)


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
