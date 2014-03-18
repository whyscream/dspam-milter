# Copyright (c) 2012, Tom Hendrikx
# All rights reserved.
#
# See LICENSE for the license.

import socket
import logging
import re


class DspamClientError(Exception):
    pass

logger = logging.getLogger(__name__)


class DspamClient(object):
    """
    A DSPAM client can be used to interact with a DSPAM server.

    The client is able to speak to a DSPAM server over both a TCP or UNIX
    domain socket exposed by a running DSPAM server, and interact with it
    through its supported protocols: LMTP and DLMTP. The latter is an
    enhanced version of LMTP to facilitate some options that are not possible
    when using strict LMTP.

    Some common DSPAM operations are included in this class, custom
    operations can be built by creating a new LMTP dialog with the
    low-level LMTP commands.

    DSPAM server setup
    ==================
    To use the client to speak with a DSPAM server, the server must be
    configured to expose a TCP (dspam.conf: ServerHost, ServerPort) or
    UNIX domain socket (dspam.conf: ServerDomainSocketPath).
    The server can support mulitple modes (dspam.conf: ServerMode) for
    interaction with connecting clients. Which mode you need, depends on
    the operations you need to perform. Most of the time you'll want to
    use DLMTP though, which means that you'll also need to setup
    authentication (dspam.conf: ServerPass.<ident>).

    Python DspamClient setup
    ========================
    Each DspamClient instance needs to talk to a DSPAM server.
    You need to specify the socket where DSPAM is listening when creating
    a new instance. If you need to use DLMTP features (probably most of the
    time), you also need to pass the ident and password.

    """

    # Default configuration
    socket = 'inet:24@localhost'
    dlmtp_ident = None
    dlmtp_pass = None

    def __init__(self, socket=None, dlmtp_ident=None, dlmtp_pass=None):
        """
        Initialize new DSPAM client.

        The socket specifies where DSPAM is listening. Specify it in the form:
        unix:PATH or inet:PORT[@HOST]. For example, the default UNIX domain
        socket in dspam.conf would look like: unix:/var/run/dspam/dspam.sock,
        and the default TCP socket: inet:24@localhost.

        Args:
        socket      -- The socket on which DSPAM is listening.
        dlmtp_ident -- The authentication identifier.
        dlmtp_pass  -- The authentication password.

        """
        if socket is not None:
            self.socket = socket
        if dlmtp_ident is not None:
            self.dlmtp_ident = dlmtp_ident
        if dlmtp_pass is not None:
            self.dlmtp_pass = dlmtp_pass

        self.dlmtp = False
        self.results = {}
        # Some internal structures
        self._socket = None
        self._recipients = []

    def __del__(self):
        """
        Destroy the DSPAM client object.

        """
        if self._socket:
            self.quit()

    def _send(self, line):
        """
        Write a line of data to the server.

        Args:
        line -- A single line of data to write to the socket.

        """
        if not line.endswith('\r\n'):
            if line.endswith('\n'):
                logger.debug('Fixing bare LF before sending data to socket')
                line = line[0:-1] + '\r\n'
            else:
                logger.debug(
                    'Fixing missing CRLF before sending data to socket')
                line = line + '\r\n'
        logger.debug('Client sent: ' + line.rstrip())
        self._socket.send(line)

    def _read(self):
        """
        Read a single response line from the server.

        """
        line = ''
        finished = False
        while not finished:
            char = self._socket.recv(1)
            if char == '':
                return ''
            elif char == '\r':
                continue
            elif char == '\n':
                finished = True
                continue
            else:
                line = line + char
        logger.debug('Server sent: ' + line.rstrip())
        return line

    def _peek(self, chars=1):
        """
        Peek at the data in the server response.

        Peeking should only be done when the response can be predicted.
        Make sure that the socket will not block by requesting too
        much data from it while peeking.

        Args:
        chars -- the number of characters to peek.

        """
        line = self._socket.recv(chars, socket.MSG_PEEK)
        logger.debug('Server sent (peek): ' + line.rstrip())
        return line

    def connect(self):
        """
        Connect to TCP or domain socket, and process the server LMTP greeting.

        """
        # extract proto from socket setting
        try:
            (proto, spec) = self.socket.split(':')
        except ValueError:
            raise DspamClientError(
                'Failed to parse DSPAM socket specification, '
                'no proto found: ' + self.socket)

        if proto == 'unix':
            # connect to UNIX domain socket
            try:
                self._socket = socket.socket(
                    socket.AF_UNIX, socket.SOCK_STREAM)
                self._socket.connect(spec)
            except socket.error, err:
                self._socket = None
                raise DspamClientError(
                    'Failed to connect to DSPAM server '
                    'at socket {}: {}'.format(spec, err))
            logger.debug('Connected to DSPAM server at socket {}'.format(spec))

        elif proto == 'inet' or proto == 'inet6':
            # connect to TCP socket
            try:
                (port, host) = spec.split('@')
                port = int(port)
                if host == '':
                    host = 'localhost'
            except ValueError:
                port = int(spec)
                host = 'localhost'

            try:
                self._socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM)
                self._socket.connect((host, port))
            except socket.error, err:
                self._socket = None
                raise DspamClientError(
                    'Failed to connect to DSPAM server at host {} '
                    'port {}: {}'.format(host, port, err))
            logger.debug(
                'Connected to DSPAM server at host {}, port {}'.format(
                    host, port))
        else:
            raise DspamClientError(
                'Failed to parse DSPAM socket specification, '
                'unknown proto ' + proto)

        resp = self._read()
        if not resp.startswith('220'):
            raise DspamClientError(
                'Unexpected server response at connect: ' + resp)

    def lhlo(self):
        """
        Send LMTP LHLO greeting, and process the server response.

        A regular LMTP greeting is sent, and if accepted by the server, the
        capabilities it returns are parsed.

        DLMTP authentication starts here by announcing the dlmtp_ident in
        the LHLO as our hostname. When the ident is accepted and DLMTP
        mode is enabled (dspam.conf: ServerMode=dspam|auto), the
        DSPAMPROCESSMODE capability is announced by the server.
        When this capability is detected, the <DspamClient>.dlmtp flag
        will be enabled.

        """
        if self.dlmtp_ident is not None:
            host = self.dlmtp_ident
        else:
            host = socket.getfqdn()
        self._send('LHLO ' + host + '\r\n')

        finished = False
        while not finished:
            resp = self._read()
            if not resp.startswith('250'):
                raise DspamClientError(
                    'Unexpected server response at LHLO: ' + resp)
            if resp[4:20] == 'DSPAMPROCESSMODE':
                self.dlmtp = True
                logger.debug('Detected DLMTP extension in LHLO response')
            if resp[3] == ' ':
                # difference between "250-8BITMIME" and "250 SIZE"
                finished = True

    def mailfrom(self, sender=None, client_args=None):
        """
        Send LMTP MAIL FROM command, and process the server response.

        In DLMTP mode, the server expects the client to identify itself.
        Because the envelope sender is of no importance to DSPAM, the client
        is expected to send an identity and a password (dspam.conf:
        ServerPass.<ident>="<password>") in stead of the actual sender.

        When you need want DSPAM to deliver the message itself and need to
        pass the server an actual envelope sender for that, add the
        --mail-from parameter in client_args.

        When the server is setup in LMTP mode only (dspam.conf:
        ServerMode=standard), the envelope sender is a regular envelope
        sender, and is re-used when delivering the message after processing.

        Client args
        ===========
        When in DLMTP mode (and with proper auth credentials), the server
        accepts parameters specified by the client. These are in the form
        as they are passed to the command-line 'dspam' program.
        See man dspam(1) for details, and the process() or classify() methods
        in this class for simple examples.

        Args:
        sender      -- The envelope sender to use in LMTP mode.
        client_args -- DSPAM parameters to pass to the server in DLMTP mode.

        """
        if sender and client_args:
            raise DspamClientError('Arguments are mutually exclusive')

        if client_args and not self.dlmtp:
            raise DspamClientError(
                'Cannot send client args, server does not support DLMTP')

        command = 'MAIL FROM:'
        if not sender:
            if self.dlmtp_ident and self.dlmtp_pass:
                sender = self.dlmtp_pass + '@' + self.dlmtp_ident
            else:
                sender = ''
        command = command + '<' + sender + '>'

        if client_args:
            command = command + ' DSPAMPROCESSMODE="{}"'.format(client_args)

        self._send(command + '\r\n')
        resp = self._read()
        if not resp.startswith('250'):
            raise DspamClientError(
                'Unexpected server response at MAIL FROM: ' + resp)

    def rcptto(self, recipients):
        """
        Send LMTP RCPT TO command, and process the server response.

        The DSPAM server expects to find one or more valid DSPAM users as
        envelope recipients. The set recipient will be the user DSPAM
        processes mail for.

        When you need want DSPAM to deliver the message itself, and need to
        pass the server an envelope recipient for this that differs from the
        DSPAM user account name, use the --rcpt-to parameter in client_args
        at mailfrom().

        args:
        recipients -- A list of recipients

        """
        for rcpt in recipients:
            self._send('RCPT TO:<{}>\r\n'.format(rcpt))
            resp = self._read()
            if not resp.startswith('250'):
                raise DspamClientError(
                    'Unexpected server response at RCPT TO for '
                    'recipient {}: {}'.format(rcpt, resp))
            self._recipients.append(rcpt)

    def data(self, message):
        """
        Send LMTP DATA command and process the server response.

        The server response is stored as a list of dicts in
        <DspamClient>.results, keyed on the recipient name(s). Depending
        on the server return data, different formats are available:
        * LMTP mode    -- Dict containing 'accepted', a bool indicating
                          that the message was handed to the server.
        * Summary mode -- Dict containing 'username', 'result',
                          'classification', 'probability', 'confidence'
                          and 'signature'.
        * Stdout mode  -- Dict containing 'result' and 'message', the
                          complete message payload including added headers.

        The return data is always parsed and stored, independent of its format.
        If you requested a regular LMTP response, but the server
        responded with an DLMTP summary, the summary is still stored in
        <DspamClient>.results, and you will need to check the result format
        yourself and decide whether that was acceptable for your use case.
        This is due to the fact that it's possible to configure the server to
        return non LMTP responses, even when in LMTP mode (see dspam.conf:
        ServerParameters).

        Note: while processing response data in stdout mode, it's not possible
        to relate the returned messages to a specific recipient, when multiple
        recipients were specified in rcptto(). There is no guarantee
        that the message stored in <DspamClient>.results['foo'] actually
        belongs to the recipient 'foo'. If this relationship needs to be
        guaranteed, send each message with a single recipient in rcptto().

        args:
        message -- The full message payload to pass to the server.

        """
        self._send('DATA\r\n')
        resp = self._read()
        if not resp.startswith('354'):
            raise DspamClientError(
                'Unexpected server response at DATA: ' + resp)

        # Send message payload
        for line in message.split('\n'):
            if line == '.':
                # Dot stuffing
                line = '..'
            self._send(line)

        # Send end-of-data
        self._send('.\r\n')

        # Depending on server configuration, several responses are possible:
        # * Standard LMTP response code, once for each recipient:
        #   250 2.6.0 <bar> Message accepted for delivery
        # * Summary response (--deliver=summary), once for each recipient:
        #   X-DSPAM-Result: bar; result="Spam"; class="Spam"; \
        #     probability=1.0000; confidence=0.85; \
        #     signature=50c50c0f315636261418125
        #   (after the last summary line, a single dot is sent)
        # * Stdout response (--delivery=stdout), once for each recipient:
        #   X-Daemon-Classification: INNOCENT
        #   <complete mail body>
        #
        # Note that when an unknown recipient is passed in, DSPAM will simply
        #   deliver the message (dspam.conf: (Un)TrustedDeliveryAgent,
        #   DeliveryHost) unaltered and unfiltered. The response for unknown
        #   recipients will still be something indicating 'accepted'.

        peek = self._peek(24)
        if peek.startswith('250'):
            # Response is LTMP formatted
            regex = re.compile('250 \d\.\d\.\d <([^>]+)>')
            finished = False
            while not finished:
                resp = self._read()
                match = regex.match(resp)
                if not match:
                    raise DspamClientError(
                        'Unexpected server response at END-OF-DATA: ' + resp)
                rcpt = match.group(1)
                for r in self._recipients:
                    if r.lower() == rcpt.lower():
                        self._recipients.remove(r)
                        break
                else:
                    raise DspamClientError(
                        'Message was accepted for unknown recipient ' + rcpt)
                self.results[rcpt] = {'accepted': True}
                logger.debug(
                    'Message accepted for recipient {} in LMTP mode'.format(
                        rcpt))
                if not len(self._recipients):
                    finished = True

        elif peek.startswith('X-DSPAM-Result:'):
            # Response is in summary format
            regex = re.compile('X-DSPAM-Result: ([^;]+); result="(\w+)"; '
                               'class="(\w+)"; probability=([\d\.]+); '
                               'confidence=([\d\.]+); signature=([\w,/]+)')
            finished = False
            while not finished:
                resp = self._read()
                match = regex.match(resp)
                if not match:
                    raise DspamClientError(
                        'Unexpected server response at END-OF-DATA: ' + resp)
                rcpt = match.group(1)
                for r in self._recipients:
                    if r.lower() == rcpt.lower():
                        self._recipients.remove(r)
                        break
                else:
                    raise DspamClientError(
                        'Message was accepted for unknown '
                        'recipient {}'.format(rcpt))

                # map results to their DSPAM classification result names
                fields = ('user', 'result', 'class',
                          'probability', 'confidence', 'signature')
                self.results[rcpt] = dict(zip(fields, match.groups()))
                if self.results[rcpt]['signature'] == 'N/A':
                    del(self.results[rcpt]['signature'])

                logger.debug(
                    'Message handled for recipient {} in DLMTP summary mode, '
                    'result is {}'.format(rcpt, match.group(2)))
                if not len(self._recipients):
                    # we received responses for all accepted recipients
                    finished = True
            # read final dot
            resp = self._read()
            if resp != '.':
                raise DspamClientError(
                    'Unexpected server response at END-OF-DATA: ' + resp)

        elif peek.startswith('X-Daemon-Classification:'):
            # Response is in stdout format
            finished = False
            message = ''
            while not finished:
                resp = self._read()
                if resp.startswith('X-Daemon-Classification:'):
                    if message != '':
                        # A new message body starts, store the previous one
                        rcpt = self._recipients.pop(0)
                        self.results[rcpt] = {
                            'result': result,
                            'message': message
                        }
                        logger.debug(
                            'Message handled for recipient {} in DLMTP '
                            'stdout mode, result is {}, message body '
                            'is {} chars'.format(rcpt, result, len(message)))
                        message = ''
                    # Remember next result
                    result = resp[25:]

                elif resp == '.':
                    # A single dot can signal end-of-data, or might be just
                    #   regular mail data.
                    self._socket.setblocking(False)
                    try:
                        # If _peek() succeeds, we did not reach end-of-data yet
                        #   so it was message content.
                        peek = self._peek(1)
                        message = message + '\r\n' + resp
                    except socket.error:
                        # reached end-of-data, store message and finish
                        finished = True
                        rcpt = self._recipients.pop(0)
                        # strip final newline
                        message = message[0:-2]
                        self.results[rcpt] = {
                            'result': result,
                            'message': message
                        }
                        logger.debug(
                            'Message accepted for recipient {} in DLMTP '
                            'stdout mode, result is {}, message body '
                            'is {} chars'.format(rcpt, result, len(message)))

                    self._socket.setblocking(True)

                else:
                    # regular message data
                    if message == '':
                        message = resp
                    else:
                        message = message + '\r\n' + resp

        else:
            raise DspamClientError(
                'Unexpected server response at END-OF-DATA: ' + resp)

    def rset(self):
        """
        Send LMTP RSET command and process the server response.

        """
        self._send('RSET\r\n')
        resp = self._read()
        if not resp.startswith('250'):
            logger.warn('Unexpected server response at RSET: ' + resp)
        self._recipients = []
        self.results = {}

    def quit(self):
        """
        Send LMTP QUIT command, read the server response and disconnect.

        """
        self._send('QUIT\r\n')
        resp = self._read()
        if not resp.startswith('221'):
            logger.warning('Unexpected server response at QUIT: ' + resp)
        self._socket.close()
        self._socket = None
        self._recipients = []
        self.results = {}

    def process(self, message, user):
        """
        Process a message.
        """
        if not self._socket:
            self.connect()
            self.lhlo()
        else:
            self.rset()

        if not self.dlmtp:
            raise DspamClientError('DLMTP mode not available')

        self.mailfrom(client_args='--process --deliver=summary')
        self.rcptto((user,))
        self.data(message)

        # check for valid result format
        if 'class' not in self.results[user]:
            raise DspamClientError(
                'Unexpected response format from server at END-OF-DATA, '
                'an error occured')

        return self.results[user]

    def classify(self, message, user):
        """
        Classify a message.

        """
        if not self._socket:
            self.connect()
            self.lhlo()
        else:
            self.rset()

        if not self.dlmtp:
            raise DspamClientError('DLMTP mode not available')

        self.mailfrom(client_args='--classify --deliver=summary')
        self.rcptto((user,))
        self.data(message)

        # check for valid result format
        if 'class' not in self.results[user]:
            raise DspamClientError(
                'Unexpected response format from server at END-OF-DATA, '
                'an error occured')

        return self.results[user]

    def train(self, message, user, class_):
        """
        Train DSPAM with a message.

        """
        raise NotImplementedError

    def retrain_message(self, message, class_, source='error'):
        """
        Correct an invalid classification.

        """
        raise NotImplementedError

    def retrain_signature(self, signature, class_, source='error'):
        """
        Correct an invalid classification.

        """
        raise NotImplementedError


if __name__ == '__main__':

    message = """Subject: Test mail
Message-ID: <TEST.1010101@example.org>
Date: Wed, 23 Jul 2003 23:30:00 +0200
From: Sender <sender@example.org>
To: Recipient <recipient@example.net>
Precedence: junk
MIME-Version: 1.0
Content-Type: text/plain; charset=us-ascii
Content-Transfer-Encoding: 7bit

This is a test mail.
Dot-stuffing test on next line:
.
The line above, you see?

"""

    logging.basicConfig(level=logging.DEBUG)

    # Config method 1
    c = DspamClient('inet:2424@localhost', 'test', 'leey2Pah')

    # Config method 2
    #c = DspamClient()
    #c.socket = 'inet:2424@localhost'
    #c.dlmtp_ident = 'test'
    #c.dlmtp_pass = 'leey2Pah'

    # Config method 3
    #DspamClient.socket = 'inet:2424@localhost'
    #DspamClient.dlmtp_ident = 'test'
    #DspamClient.dlmtp_pass = 'leey2Pah'
    #c = DspamClient()

    results = c.process(message, 'recipient@example.net')
    print('Classification results: ' + str(results))
