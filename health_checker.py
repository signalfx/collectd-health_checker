#!/usr/bin/env python

import requests

try:
    import collectd

except ImportError:
    try:
        import dummy_collectd as collectd
    except:
        pass

PLUGIN_NAME = 'health_checker'
SEND = True
PLUGIN_INSTANCE = ''
TYPE = 'gauge'


def log(param):
    """
    Log messages to either collectd or stdout depending on how it was called.
    :param param: the message
    :return:  None
    """

    if __name__ != '__main__':
        collectd.info("%s: %s" % (PLUGIN_NAME, param))
    else:
        sys.stderr.write("%s\n" % param)


def config(conf):
    """
    Parses and loads options from the collectd plugin config file

    :param conf: a Config object
    :return: None
    """

    for val in conf.children:
        if val.key == 'URL':
            global URL
            URL = val.values[0]
        if val.key == 'Instance':
            global INSTANCE
            INSTANCE = val.values[0]


def _get_http_response(URL):
    response = 0
    try:
        r = requests.get(URL)
        response = r.status_code
    except:
        pass
    return response


def read():

    val = _get_http_response(URL)
    collectd.Values(plugin=PLUGIN_NAME,
                    type_instance="service.health",
                    plugin_instance=INSTANCE,
                    type=TYPE,
                    values=[val]).dispatch()

    global SEND
    if SEND:
        notif = collectd.Notification(plugin=PLUGIN_NAME,
                                      type_instance="started",
                                      type="objects")
        notif.severity = 4  # OKAY
        notif.message = "The %s plugin has just started" % PLUGIN_NAME
        notif.dispatch()
        SEND = False


def init():
    """
    This method has been registered as the init callback; this gives the plugin
    a way to do startup actions.  We'll just log a message
    :return: None
    """

    log("Plugin %s initializing..." % PLUGIN_NAME)


def shutdown():
    """
    This method has been registered as the shutdown callback. this gives the
    plugin a way to clean up after itself before shutting down.  We'll just log
    a message.
    :return: None
    """

    log("Plugin %s shutting down..." % PLUGIN_NAME)


def log_cb(severity, message):
    """
    This method has been registered as the log callback.
    :param severity: an integer and small for important messages
      and high for less important messages
    :param message: a string without a newline at the end
    :return: None
    """

    pass


if __name__ != "__main__":
    # when running inside plugin register each callback
    collectd.register_init(init)
    collectd.register_config(config)
    collectd.register_log(log_cb)
    collectd.register_read(read)
    collectd.register_shutdown(shutdown)
else:
    # outside plugin just collect the info
    read()
    if len(sys.argv) < 2:
        while True:
            time.sleep(10)
            read()
