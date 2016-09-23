# Copyright (c) 2013, Tom Hendrikx
# All rights reserved.
#
# See LICENSE for the license.

import atexit
import errno
import logging
from logging.handlers import SysLogHandler
import os
import resource
import signal
import sys

logger = logging.getLogger(__name__)


def daemonize(pidfile=None):
    """
    Turn the running process into a proper daemon according to PEP3143.

    Args:
    pidfile --The pidfile to create.

    """

    # Prevent core dumps
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    # Change working directory
    os.chdir("/")

    # Change file creation mask
    os.umask(0)

    # Detach process context: do double fork
    pid = os.fork()
    if pid > 0:
        os._exit(0)
    os.setsid()
    pid = os.fork()
    if pid > 0:
        os._exit(0)

    # Create signal handler for SIGTERM
    def terminate(signal, stack_frame):
        msg = 'Terminating on signal {}'.format(signal)
        logger.info(msg)
        raise SystemExit(msg)
    signal.signal(signal.SIGTERM, terminate)

    # Redirect input/output streams
    streams = [sys.stdin, sys.stdout, sys.stderr]
    for stream in streams:
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, stream.fileno())

    # Close file descriptors
    for fd in [stream.fileno() for stream in streams]:
        try:
            os.close(fd)
        except OSError as err:
            if err.errno == errno.EBADF:
                # File descriptor was not open
                pass

    # Create pidfile
    if pidfile is None or pidfile.strip() == '':
        logger.debug('Empty pidfile set')
    else:
        pid = os.getpid()
        try:
            with open(pidfile, 'w') as f:
                f.write('{}\n'.format(pid))
                f.close()
        except EnvironmentError:
            logger.error('Failed to create pidfile at {}'.format(pidfile))

        def remove_pid_file():
            os.remove(pidfile)

        atexit.register(remove_pid_file)

    logger.debug('Process daemonized')


def config_str2dict(option_value):
    """
    Parse the value of a config option and convert it to a dictionary.

    The configuration allows lines formatted like:
    foo = Bar:1,Baz,Flub:0.75
    This gets converted to a dictionary:
    foo = { 'Bar': 1, 'Baz': 0, 'Flub': 0.75 }

    Args:
    option_value -- The config string to parse.

    """
    dict = {}
    for key in option_value.split(','):
        if ':' in key:
            key, value = pair.split(':')
            value = float(value)
        else:
            value = 0
        dict[key] = value
    return dict


def log_to_syslog():
    """
    Configure logging to syslog.

    """
    # Get root logger
    rl = logging.getLogger()
    rl.setLevel('INFO')

    # Stderr gets critical messages (mostly config/setup issues)
    #   only when not daemonized
    stderr = logging.StreamHandler(stream=sys.stderr)
    stderr.setLevel(logging.CRITICAL)
    stderr.setFormatter(logging.Formatter(
        '%(asctime)s %(name)s: %(levelname)s %(message)s'))
    rl.addHandler(stderr)

    # All interesting data goes to syslog, using root logger's loglevel
    syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_MAIL)
    syslog.setFormatter(logging.Formatter(
        '%(name)s[%(process)d]: %(levelname)s %(message)s'))
    rl.addHandler(syslog)
    #logger.info('Logging configured')
