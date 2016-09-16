#!/usr/bin/env python

# This plugin is intended to be a very basic health checker for any
# type of system. Since it is intended to work with many systems, it
# abstracts out all return values so that all systems
# return the same metric value for success and failure.
# The plugin will output the actual failure value in the collectd logs.
#
# This plugin copied over customized basic service health and zookeeper
# health checks from SignalFx's Nagios configuration

import requests
import socket

try:
    import collectd
except ImportError:
    import dummy_collectd as collectd

PLUGIN_NAME = 'health_checker'
SEND = True
PLUGIN_INSTANCE = ''
TYPE = 'gauge'
SICK_MSG = 'Service is not healthy'
MISSING_JSON_MSG = 'All JSON keys not present.  Will not collect metrics'
ZK_OK_CMD = 'ruok'
ZK_WRITE_CMD = 'isro'
ZK_HOST = 'localhost'
plugin_conf = {}


def log(param):
    if __name__ != '__main__':
        collectd.info('%s: %s' % (PLUGIN_NAME, param))
    else:
        sys.stderr.write('%s\n' % param)


def config(conf):
    global plugin_conf
    required_keys = ('Instance',)
    json_keys = ('JSONKey', 'JSONVal')
    chk_json = False

    for val in conf.children:
        if val.key == 'HEALTH_URL':
            plugin_conf[val.key] = val.values[0]
        elif val.key == 'JSONKey':
            plugin_conf[val.key] = val.values[0]
            chk_json = True
        elif val.key == 'JSONVal':
            plugin_conf[val.key] = val.values[0]
            chk_json = True
        elif val.key == 'ZKHost':
            plugin_conf[val.key] = val.values[0]
        elif val.key == 'ZKPort':
            plugin_conf[val.key] = val.values[0]
        elif val.key == 'Instance':
            plugin_conf[val.key] = val.values[0]
        else:
            log('Unknown config key: %s' % val.key)

    for key in required_keys:
        rkey = plugin_conf.get(key)
        if rkey is None:
            raise ValueError('Missing required config setting: %s' % (key))

    if chk_json:
        json_ls = []
        for key in json_keys:
            jkey = plugin_conf.get(key)
            if jkey:
                json_ls.append(jkey)
        if len(json_ls) != len(json_keys):
            raise ValueError('JSON must have both keys: %s' % (json_keys,))

    if 'ZKHost' in plugin_conf:
        if 'ZKPort' not in plugin_conf:
            raise ValueError('Must include ZKPort as config key for'
                             ' zookeeper health check')


def _get_http_response(plugin_conf):
    status = 0
    health_url = plugin_conf.get('HEALTH_URL')
    try:
        resp = requests.get(health_url).status_code
        if resp == 200:
            status = 1
        else:
            log('%s; %s return code is %s' % (SICK_MSG, resp))
        return status
    except:
        log('%s; %s is unreachable.' % (SICK_MSG, health_url))
        return status


def _get_json_status(plugin_conf):
    status = 0
    val = 0
    health_url = plugin_conf.get('HEALTH_URL')
    json_key = plugin_conf.get('JSONKey')
    json_val = plugin_conf.get('JSONVal')
    try:
        r = requests.get(health_url)
        if r.status_code == 200:
            status = 1
        if json_key in r.json():
            if r.json().get(json_key) == json_val:
                val = 1
            else:
                log('%s; reporting %s' % (SICK_MSG, r.json().get(json_key)))
        return status, val
    except:
        return status, val


def _send_zk_command(cmd, plugin_conf, timeout=1):
    data = 0
    zk_host = ZK_HOST
    if 'ZKHost' in plugin_conf:
        zk_host = plugin_conf.get('ZKHost')
    zk_port = plugin_conf.get('ZKPort')
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((zk_host, int(zk_port)))
        s.send(cmd)
        data = s.recv(2048)
        s.close()
    except socket.timeout:
        # if zookeeper is not ok it won't respond; treat as critical
        log('%s; timed out calling "%s" on %s:%s'
            % (SICK_MSG, cmd, zk_host, zk_port))
    except socket.error, e:
        log('%s; error calling "%s" on %s:%s: %s'
            % (SICK_MSG, cmd, zk_host, zk_port, e))
    return data


def _get_zk_status(plugin_conf):
    status = 0
    val = 0
    zk_ok = _send_zk_command(ZK_OK_CMD, plugin_conf)
    if zk_ok == 'imok':
        status = 1
        zk_write = _send_zk_command(ZK_WRITE_CMD, plugin_conf)
        if zk_write == 'rw':
            val = 1
        else:
            log('%s; not writeable; %s is %s'
                % (SICK_MSG, ZK_WRITE_CMD, zk_write))
    else:
        log('%s: rouk command failed' % SICK_MSG)
    return status, val


def read():
    sval = None
    hval = None
    if 'HEALTH_URL' in plugin_conf:
        if 'JSONKey' in plugin_conf and 'JSONVal' in plugin_conf:
            sval, hval = _get_json_status(plugin_conf)
        elif 'JSONKey' in plugin_conf and 'JSONVal' not in plugin_conf:
            log('%s' % MISSING_JSON_MSG)
        elif 'JSONVal' in plugin_conf and 'JSONKey' not in plugin_conf:
            log('%s' % MISSING_JSON_MSG)
        else:
            sval = _get_http_response(plugin_conf)
            hval = 1

    if 'ZKPort' in plugin_conf:
        sval, hval = _get_zk_status(plugin_conf)

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
    else:
        log('No valid config keys found.  Will not collect metrics')


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
