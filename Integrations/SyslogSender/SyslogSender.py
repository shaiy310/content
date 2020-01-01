import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *
''' IMPORTS '''

from contextlib import contextmanager
from logging.handlers import SysLogHandler
from distutils.util import strtobool
import requests
import logging
import socket

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

''' CONSTANTS '''


PLAYGROUND_INVESTIGATION_TYPE = 9
INCIDENT_OPENED = 'incidentOpened'
LOGGING_LEVEL_DICT = {
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
SEVERITY_DICT = {
    'Unknown': 0,
    'Low': 1,
    'Medium': 2,
    'High': 3,
    'Critical': 4
}

''' Syslog Manager '''


class SyslogManager:
    def __init__(self, address: str, port: int, protocol: str, logging_level: int):
        """
        Class for managing instances of a syslog logger.
        :param address: The IP address of the syslog server.
        :param port: The port of the syslog server.
        :param protocol: The messaging protocol (TCP / UDP).
        :param logging_level: The logging level.
        """
        self.address = address
        self.port = port
        self.protocol = protocol
        self.logging_level = logging_level

    @contextmanager  # type: ignore[misc, arg-type]
    def get_logger(self) -> logging.Logger:
        """
        Get a new instance of a syslog logger.
        :return: syslog logger
        """
        handler = self._get_handler()
        syslog_logger = self._init_logger(handler)
        try:
            yield syslog_logger
        finally:
            syslog_logger.removeHandler(handler)
            handler.close()

    def _get_handler(self) -> SysLogHandler:
        """
        Get a syslog handler for a logger according to provided parameters.
        :return: syslog handler
        """
        if self.protocol == 'tcp':
            return SysLogHandler((self.address, self.port), socktype=socket.SOCK_STREAM)
        else:
            return SysLogHandler((self.address, self.port))

    def _init_logger(self, handler: SysLogHandler) -> logging.Logger:
        """
        Initialize a logger with a syslog handler.
        :param handler: A syslog handler
        :return: A syslog logger
        """
        syslog_logger = logging.getLogger('SysLogLogger')
        syslog_logger.setLevel(self.logging_level)
        syslog_logger.addHandler(handler)

        return syslog_logger


''' HELPER FUNCTIONS '''


def init_manager(params: dict) -> SyslogManager:
    """
    Create a syslog manager instance according to provided parameters.
    :param params: Parameters for the syslog manager.
    :return: syslog manager
    """
    address = params.get('address', '')
    port = int(params.get('port', 514))
    protocol = params.get('protocol', 'udp').lower()
    logging_level = LOGGING_LEVEL_DICT.get(params.get('logging_level', 'INFO'), logging.INFO)

    return SyslogManager(address, port, protocol, logging_level)


def send_log(manager: SyslogManager, message: str, log_level: str):
    """
    Use a syslog manager to get a logger and send a message to syslog.
    :param manager: The syslog manager
    :param message: The message to send
    :param log_level: The logging level
    """
    with manager.get_logger() as syslog_logger:   # type: logging.Logger
        if log_level == 'DEBUG':
            syslog_logger.debug(message)
        if log_level == 'INFO':
            syslog_logger.info(message)
        if log_level == 'WARNING':
            syslog_logger.warning(message)
        if log_level == 'ERROR':
            syslog_logger.error(message)
        if log_level == 'CRITICAL':
            syslog_logger.critical(message)


def check_for_mirrors():
    """
    Check for newly created mirrors and update the server accordingly
    """
    integration_context = demisto.getIntegrationContext()
    if integration_context.get('mirrors'):
        mirrors = json.loads(integration_context['mirrors'])
        for mirror in mirrors:
            if not mirror['mirrored']:
                demisto.info('Mirroring: {}'.format(mirror['investigation_id']))
                mirror = mirrors.pop(mirrors.index(mirror))
                investigation_id = mirror['investigation_id']
                mirror_type = mirror['mirror_type']
                demisto.mirrorInvestigation(investigation_id, '{}:{}'.format(mirror_type, 'FromDemisto'), False)
                mirror['mirrored'] = True
                mirrors.append(mirror)

                demisto.setIntegrationContext({'mirrors': json.dumps(mirrors)})


def mirror_investigation():
    """
    Update the integration context with a new or existing mirror.
    """
    mirror_type = demisto.args().get('type', 'all')

    investigation = demisto.investigation()

    if investigation.get('type') == PLAYGROUND_INVESTIGATION_TYPE:
        return_error('Can not perform this action in playground.')

    investigation_id = investigation.get('id')
    integration_context = demisto.getIntegrationContext()
    if 'mirrors' not in integration_context:
        mirrors: list = []
    else:
        mirrors = json.loads(integration_context['mirrors'])

    mirror_filter = list(filter(lambda m: m['investigation_id'] == investigation_id, mirrors))
    if mirror_filter:
        # Delete existing mirror
        mirrors.pop(mirrors.index(mirror_filter[0]))
    mirror = {
        'investigation_id': investigation.get('id'),
        'mirror_type': mirror_type,
        'mirrored': False
    }

    mirrors.append(mirror)
    demisto.setIntegrationContext({'mirrors': json.dumps(mirrors)})

    demisto.results('Investigation mirrored successfully.')


''' Syslog send command '''


def syslog_send(manager: SyslogManager, min_severity: int):
    """
    Send a message to syslog
    """
    message = demisto.args().get('message', '')
    entry = demisto.args().get('entry')
    ignore_add_url = demisto.args().get('ignoreAddURL', False)
    log_level = demisto.args().get('log_level')
    severity = demisto.args().get('severity')  # From server
    message_type = demisto.args().get('messageType', '')  # From server

    if severity:
        try:
            severity = int(severity)
        except Exception:
            severity = None

    if message_type == INCIDENT_OPENED and (severity is not None and severity < min_severity):
        return

    if not message:
        message = ' '

    message = message.replace('\n', ' ').replace('\r', ' ').replace('`', '')
    investigation = demisto.investigation()
    if investigation:
        if entry:
            message = '{}, {}'.format(entry, message)
        message = '{}, {}'.format(investigation.get('id'), message)

    if ignore_add_url and isinstance(ignore_add_url, str):
        ignore_add_url = bool(strtobool(ignore_add_url))
    if not ignore_add_url:
        investigation = demisto.investigation()
        server_links = demisto.demistoUrls()
        if investigation:
            if investigation.get('type') != PLAYGROUND_INVESTIGATION_TYPE:
                link = server_links.get('warRoom')
                if link:
                    if entry:
                        link += '/' + entry
                    message += ' {}'.format(link)
            else:
                link = server_links.get('server', '')
                if link:
                    message += ' {}#/home'.format(link)

    if not log_level:
        if severity == SEVERITY_DICT['Critical']:
            log_level = 'CRITICAL'
        else:
            log_level = 'INFO'

    send_log(manager, message, log_level)

    demisto.results('Message sent to syslog successfully.')


def long_running_main():
    """
    Loop for the long running process.
    """
    while True:
        check_for_mirrors()
        time.sleep(5)


''' MAIN '''


def main():
    LOG('Command being called is %s' % (demisto.command()))

    syslog_manager = init_manager(demisto.params())
    min_severity = SEVERITY_DICT.get(demisto.params().get('severity', 'Low'), 1)

    try:
        if demisto.command() == 'test-module':
            with syslog_manager.get_logger() as syslog_logger:  # type: logging.Logger
                syslog_logger.info('This is a test')
            demisto.results('ok')
        elif demisto.command() == 'mirror-investigation':
            mirror_investigation()
        elif demisto.command() == 'send-notification':
            syslog_send(syslog_manager, min_severity)
        elif demisto.command() == 'long-running-execution':
            long_running_main()
    except Exception as e:
        LOG(e)
        LOG.print_log()
        return_error(str(e))


if __name__ in ['__main__', '__builtin__', 'builtins']:
    main()
