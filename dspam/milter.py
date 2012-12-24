# Copyright (c) 2012, Tom Hendrikx
# All rights reserved.
#
# See LICENSE for the license.

import ConfigParser
import datetime
import logging
from logging.handlers import SysLogHandler
import os.path
import sys
import time

import Milter

from dspam import VERSION
from dspam.client import *

logger = logging.getLogger(__name__)

class DspamMilter(Milter.Base):
    """
    A milter interface to the DSPAM daemon.

    This milter can be added to an MTA setup so messages can be inspected
    by a DSPAM server, and optionally rejected or quarantined based on the
    classification results.
 
    """

    # Constants defining possible return codes for compute_verdict()
    VERDICT_ACCEPT = 1
    VERDICT_QUARANTINE = 2
    VERDICT_REJECT = 3

    # Default configuration
    dspam_user = None
    headers = {'Processed': 0, 'Confidence': 0, 'Probability': 0, 'Result': 0, 'Signature': 0}
    header_prefix = 'X-DSPAM-'
    reject_classes = {'Blacklisted': 0, 'Blocklisted': 0, 'Spam': 0.9}
    quarantine_classes = {'Virus': 0}
    accept_classes = {'Innocent': 0, 'Whitelisted': 0}

    def __init__(self):
        """
        Create a new milter instance.

        """
        self.id = Milter.uniqueID()
        self.message = ''
        self.recipients = []
        self.dspam = None

    def connect(self, hostname, family, hostaddr):
        """
        Log new connections.

        """
        self.client_ip = hostaddr[0]
        self.client_port = hostaddr[1]
        self.time_start = time.time()
        logger.info('<{}> Connect from {}[{}]:{}'.format(self.id, hostname, self.client_ip, self.client_port))
        return Milter.CONTINUE

    def envrcpt(self, rcpt):
        """
        Send all recipients to DSPAM.

        """
        if rcpt.startswith('<'):
            rcpt = rcpt[1:]
        if rcpt.endswith('>'):
            rcpt = rcpt[:-1]
        self.recipients.append(rcpt)
        logger.debug('<{}> Received RCPT {}'.format(self.id, rcpt))
        return Milter.CONTINUE

    @Milter.noreply
    def header(self, name, value):
        """
        Store all message headers.

        """
        self.message += "{}: {}\r\n".format(name, value)
        logger.debug('<{}> Received {} header'.format(self.id, name))
        return Milter.CONTINUE

    @Milter.noreply
    def eoh(self):
        """
        Store end of message headers.

        """
        self.message += "\r\n"
        return Milter.CONTINUE

    @Milter.noreply
    def body(self, block):
        """
        Store message body.

        """
        self.message += block
        logger.debug('<{}> Received {} bytes of message body'.format(self.id, len(block)))
        return Milter.CONTINUE

    def eom(self):
        """
        Send the message to DSPAM for classification and a return a milter
        response based on the results.

        If <DspamMilter>.dspam_user is set, that single DSPAM user account
        will be used for processing the message. If it is unset, all envelope
        recipients will be passed to DSPAM, and the final decision is based on
        the least invasive result in all their classification results.

        """
        queue_id = self.getsymval('i')
        logger.info('<{}> Sending message with MTA queue id {} to DSPAM'.format(self.id, queue_id))

        try:
            if not self.dspam:
                self.dspam = DspamClient()
                self.dspam.connect()
                self.dspam.lhlo()
                if not self.dspam.dlmtp:
                    logger.warning('<{}> Connection to DSPAM is established, but DLMTP seems unavailable'.format(self.id))
            else:
                self.dspam.rset()
        except DspamClientError, err:
            logger.error('<{}> An error ocurred while connecting to DSPAM: {}'.format(self.id, err))
            return Milter.TEMPFAIL

        try:
            self.dspam.mailfrom(client_args='--process --deliver=summary')
            if self.dspam_user:
                self.dspam.rcptto((self.dspam_user,))
            else:
                self.dspam.rcptto(self.recipients)
            self.dspam.data(self.message)
        except DspamClientError, err:
            logger.error('<{}> An error ocurred while talking to DSPAM: {}'.format(self.id, err))
            return Milter.TEMPFAIL

        # Clear caches
        self.message = ''
        self.recipients = []

        # With multiple recipients, if different verdicts were returned, always
        #   use the 'lowest' verdict as final, so mail is not lost unexpected.
        final_verdict = None
        for rcpt in self.dspam.results:
            results = self.dspam.results[rcpt]
            logger.info('<{}> DSPAM returned results for RCPT {}: {}'.format(self.id, rcpt, ' '.join('{}={}'.format(k, v) for k, v in results.iteritems())))
            verdict = self.compute_verdict(results)
            if final_verdict is None or verdict < final_verdict:
                final_verdict = verdict
                final_results = results

        if final_verdict == self.VERDICT_REJECT:
            logger.info('<{0}> Rejecting message based on DSPAM results: user={1[user]} class={1[class]} confidence={1[confidence]}'.format(self.id, final_results))
            self.setreply('550', '5.7.1', 'Message is {0[class]}'.format(final_results))
            return Milter.REJECT
        elif final_verdict == self.VERDICT_QUARANTINE:
            logger.info('<{0}> Quarantining message based on DSPAM results: user={1[user]} class={1[class]} confidence={1[confidence]}'.format(self.id, final_results))
            self.add_dspam_headers(final_results)
            self.quarantine('Message is {0[class]} according to DSPAM'.format(final_results))
            return Milter.ACCEPT
        else:
            logger.info('<{0}> Accepting message based on DSPAM results: user={1[user]} class={1[class]} confidence={1[confidence]}'.format(self.id, final_results))
            self.add_dspam_headers(final_results)
            return Milter.ACCEPT

    def close(self):
        """
        Log disconnects.

        """
        time_spent = time.time() - self.time_start
        logger.info('<{}> Disconnect from [{}]:{}, time spent {:.3f} seconds'.format(self.id, self.client_ip, self.client_port, time_spent))
        return Milter.CONTINUE

    def compute_verdict(self, results):
        """
        Match results to the configured reject, quarantine and accept classes,
        and return a verdict based on that.

        The verdict classes are matched in the order: reject_classes,
        quarantine_classes, accept_classes. This means that you can configure 
        different verdicts for different confidence results, for instance:
        reject_classes= Spam:0.99       # Reject obvious spam
        quarantine_classes = Spam:0.7   # Quarantine spam with confidence
                                        #   between 0.7 and 0.99
        accept_classes = Spam           # Accept low confidence spam (good
                                        #   for FP and retraining)

        Args:
        results -- A results dictionary from DspamClient.

        """
        if results['class'] in self.reject_classes:
            threshold = self.reject_classes[ results['class'] ]
            if float(results['confidence']) >= threshold:
                logger.debug('<{0}> Suggesting to reject the message based on DSPAM results: user={1[user]}, class={1[class]}, confidence={1[confidence]}'.format(self.id, results))
                return self.VERDICT_REJECT

        if results['class'] in self.quarantine_classes:
            threshold = self.quarantine_classes[ results['class'] ]
            if float(results['confidence']) >= threshold:
                logger.debug('<{0}> Suggesting to quarantine the message based on DSPAM results: user={1[user]}, class={1[class]}, confidence={1[confidence]}'.format(self.id, results))
                return self.VERDICT_QUARANTINE

        if results['class'] in self.accept_classes:
            threshold = self.accept_classes[ results['class'] ]
            if float(results['confidence']) >= threshold:
                logger.debug('<{0}> Suggesting to accept the message based on DSPAM results: user={1[user]}, class={1[class]}, confidence={1[confidence]}'.format(self.id, results))
                return self.VERDICT_ACCEPT

        logger.debug('<{0}> Suggesting to accept the message, no verdict class matched DSPAM results: user={1[user]}, class={1[class]}, confidence={1[confidence]}'.format(
                    self.id, results))
        return self.VERDICT_ACCEPT

    def add_dspam_headers(self, results):
        """
        Format DSPAM headers with passed results, and add them to the message.

        Args:
        results -- A results dictionary from DspamClient.
        """
        for header in self.headers:
            hname = self.header_prefix + header
            if header.lower() in results:
                hvalue = results[header.lower()]
                logger.debug('<{}> Adding header {}: {}'.format(self.id, hname, hvalue))
                self.addheader(hname, hvalue)
            elif header == 'Processed':
                # X-DSPAM-Processed: Wed Dec 12 02:19:23 2012
                hvalue = datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')
                logger.debug('<{}> Adding header {}: {}'.format(self.id, hname, hvalue))
                self.addheader(hname, hvalue)
            else:
                logger.warning('<{}> Not adding header {}, no data available in DSPAM results'.format(self.id, hname))


def verdict_config_to_dict(verdict_cfg):
    """
    Parse a verdict classes line as specified in the configuration file, and return it as a dictionary.

    Args:
    verdict_cfg -- A string describing a verdict.

    """
    dict = {}
    for classification in verdict_cfg.split(','):
        if ':' in classification:
            classification, confidence = classification.split(':')
            confidence = float(confidence)
        else:
            confidence = 0
        dict[classification] = confidence
    return dict


def runmilter(config_file=None):
    """
    Configure and run a milter process.

    Args:
    config_file -- Path to optional config file.

    """
    # Logging setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Stderr gets critical messages (mostly config/setup issues)
    stderr = logging.StreamHandler(stream=sys.stderr)
    stderr.setLevel(logging.CRITICAL)
    stderr.setFormatter(logging.Formatter('%(asctime)s %(name)s: %(levelname)s %(message)s'))
    root_logger.addHandler(stderr)

    # All interesting data goes to syslog
    syslog = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_MAIL)
    syslog.setFormatter(logging.Formatter(os.path.basename(sys.argv[0]) + '[%(process)d]: %(name)s: %(levelname)s %(message)s'))
    root_logger.addHandler(syslog)

    logger.info('DSPAM Milter (v{}) startup'.format(VERSION))

    # Create configuration with basic settings
    milter_defaults = {'socket': 'inet:2425@localhost', 'timeout': 300, 'loglevel': 'INFO'}
    config = ConfigParser.RawConfigParser()
    config.add_section('milter')
    for option in milter_defaults:
        config.set('milter', option, milter_defaults[option])

    # Read config file
    if config_file:
        try:
            config.readfp(open(config_file))
        except IOError, err:
                logger.critical('Error while reading config file {}: {}'.format(config_file, err.strerror))
                sys.exit(1)
        logger.info('Parsed config file ' + config_file)

    # Extract user-defined log level from configuration
    loglevel = config.get('milter', 'loglevel')
    loglevel_numeric = getattr(logging, loglevel.upper(), None)
    if not isinstance(loglevel_numeric, int):
        logger.critical('Config contains unsupported loglevel: ' + loglevel)
        exit(1)
    root_logger.setLevel(loglevel_numeric)
    logger.debug('Config option configured: milter::loglevel: {}'.format(loglevel))

    # Milter configuration
    milter_socket = config.get('milter', 'socket')
    logger.debug('Config option configured: milter::socket: {}'.format(milter_socket))
    milter_timeout = config.get('milter', 'timeout')
    logger.debug('Config option configured: milter::timeout: {}'.format(milter_timeout))

    # Dspam configuration
    if config.has_section('dspam'):
        for option in ['socket', 'dlmtp_ident', 'dlmtp_pass']:
            if config.has_option('dspam', option):
                setattr(DspamClient, option, config.get('dspam', option))
                logger.debug('Config option configured: dspam::{}: {}'.format(option, getattr(DspamClient, option)))

        if config.has_option('dspam', 'user'):
            DspamMilter.dspam_user = config.get('dspam', 'user')
            logger.debug('Config option configured: dspam::user: {}'.format(DspamMilter.dspam_user))

    # Classification settings
    if config.has_section('classification'):
        for option in ['headers', 'header_prefix', 'reject_classes', 'quarantine_classes', 'accept_classes']:
            if config.has_option('classification', option):
                value = config.get('classification', option)
                if ',' in value:
                    try:
                        value = verdict_config_to_dict(value)
                    except:
                        logger.critical('Config contains invalid markup for {}: {}'.format(option, value))
                        sys.exit(1)
                setattr(DspamMilter, option, value)
                logger.debug('Config option configured: classification::{}: {}'.format(option, value))

    # Start the milter
    logger.debug('Configuration completed, starting process')
    Milter.factory = DspamMilter
    Milter.runmilter('DspamMilter', milter_socket, milter_timeout)
    logger.info('DSPAM Milter (v{}) shutdown'.format(VERSION))
    logging.shutdown()


if __name__ == "__main__":
    runmilter()
