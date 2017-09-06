import os.path

import pytest
from flexmock import flexmock

from .client import *


def test_init():
    c = DspamClient()
    assert(c.socket == 'inet:24@localhost')
    assert(c.dlmtp_ident is None)
    assert(c.dlmtp_pass is None)


def test_init_with_args(tmpdir):
    sock = 'unix:' + os.path.join(str(tmpdir), 'dspam.sock')
    dlmtp_ident = 'bar'
    dlmtp_pass = 'baz'
    c = DspamClient(sock, dlmtp_ident, dlmtp_pass)
    assert c.socket == sock
    assert c.dlmtp_ident == dlmtp_ident
    assert c.dlmtp_pass == dlmtp_pass


@pytest.mark.parametrize('input,expected', [
    ('foo\r\n', 'foo\r\n'),
    ('foo\n', 'foo\r\n'),
    ('foo', 'foo\r\n'),
    ('foo\r', 'foo\r\r\n'),
])
def test_send(input, expected):
    sock = flexmock()
    sock.should_receive('send').once().with_args(expected)
    c = DspamClient()
    c._socket = sock
    c._send(input)


def test_read():
    sock = flexmock()
    sock.should_receive('recv').and_return(
        '', 'f', 'o', 'o', '\r', '\n', 'b', 'a', 'r', '\n', 'qux').one_by_one()
    c = DspamClient()
    c._socket = sock
    assert c._read() == ''
    assert c._read() == 'foo'
    assert c._read() == 'bar'
    assert c._peek() == 'qux'


def test_connect(monkeypatch):
    def noop(*args, **kwargs):
        pass
    monkeypatch.setattr(socket.socket, 'connect', noop)

    c = DspamClient()
    flexmock(c).should_receive('_read').once().and_return(
        '220 DSPAM DLMTP 3.10.2 Authentication Required')
    c.connect()
    assert isinstance(c._socket, socket.socket)
    # reset the socket to prevent 'Broken pipe' errors during test teardown invoked by DspamClient.quit()
    c._socket = None


def test_connect_unix_failed(tmpdir):
    sock = 'unix:' + os.path.join(str(tmpdir), 'dspam.sock')
    c = DspamClient(sock)
    with pytest.raises(DspamClientError):
        c.connect()


def test_connect_invalid_socketspec():
    sock = 'foo'
    c = DspamClient(sock)
    with pytest.raises(DspamClientError):
        c.connect()

    sock = 'foo:bar'
    c = DspamClient(sock)
    with pytest.raises(DspamClientError):
        c.connect()


def test_lhlo():
    c = DspamClient(dlmtp_ident='foo')
    flexmock(c).should_receive('_send').once().with_args('LHLO foo\r\n')
    (flexmock(c)
        .should_receive('_read')
        .times(6)
        .and_return('250-localhost.localdomain')
        .and_return('250-PIPELINING')
        .and_return('250-ENHANCEDSTATUSCODES')
        .and_return('250-DSPAMPROCESSMODE')
        .and_return('250-8BITMIME')
        .and_return('250 SIZE'))
    c.lhlo()
    assert c.dlmtp is True


def test_lhlo_no_dlmtp():
    c = DspamClient()
    flexmock(c).should_receive('_send').once().with_args(re.compile('^LHLO '))
    (flexmock(c)
        .should_receive('_read')
        .times(5)
        .and_return('250-localhost.localdomain')
        .and_return('250-PIPELINING')
        .and_return('250-ENHANCEDSTATUSCODES')
        .and_return('250-8BITMIME')
        .and_return('250 SIZE'))
    c.lhlo()
    assert c.dlmtp is False


def test_lhlo_unexpected_response():
    c = DspamClient()
    flexmock(c).should_receive('_send').once().with_args(re.compile('^LHLO '))
    flexmock(c).should_receive('_read').once().and_return('foo')
    with pytest.raises(DspamClientError):
        c.lhlo()


def test_mailfrom_invalid_args():
    c = DspamClient()
    with pytest.raises(DspamClientError):
        c.mailfrom(sender='foo', client_args='bar')

    c = DspamClient()
    c.dlmtp = False
    with pytest.raises(DspamClientError):
        c.mailfrom(client_args='foo')


@pytest.mark.parametrize('sender,dlmtp_ident,dlmtp_pass,expected', [
    (None, None, None, 'MAIL FROM:<>\r\n'),
    ('qux', None, None, 'MAIL FROM:<qux>\r\n'),
    ('qux', 'foo', None, 'MAIL FROM:<qux>\r\n'),
    # sender overrules dlmtp args
    ('qux', 'foo', 'bar', 'MAIL FROM:<qux>\r\n'),
    (None, 'foo', None, 'MAIL FROM:<>\r\n'),
    # no sender, dlmtp args are ok -> use them
    (None, 'foo', 'bar', 'MAIL FROM:<bar@foo>\r\n'),
    (None, None, 'bar', 'MAIL FROM:<>\r\n'),
])
def test_mailfrom_sender(sender, dlmtp_ident, dlmtp_pass, expected):
    c = DspamClient(dlmtp_ident=dlmtp_ident, dlmtp_pass=dlmtp_pass)
    flexmock(c).should_receive('_send').once().with_args(expected)
    flexmock(c).should_receive('_read').once().and_return('250 OK')
    c.mailfrom(sender)


def test_mailfrom_client_args():
    c = DspamClient()
    c.dlmtp = True
    flexmock(c).should_receive('_send').once().with_args(
        'MAIL FROM:<> DSPAMPROCESSMODE="bar"\r\n')
    flexmock(c).should_receive('_read').once().and_return('250 OK')
    c.mailfrom(client_args='bar')


def test_mailfrom_error_response():
    c = DspamClient()
    flexmock(c).should_receive('_send').once()
    flexmock(c).should_receive('_read').once().and_return(
        '451 Some error ocurred')
    with pytest.raises(DspamClientError):
        c.mailfrom()


def test_rcptto():
    c = DspamClient()
    flexmock(c).should_receive('_send').once().with_args('RCPT TO:<foo>\r\n')
    flexmock(c).should_receive('_read').once().and_return('250 2.1.5 OK')
    c.rcptto(('foo',))


def test_rcptto_multiple():
    c = DspamClient()
    flexmock(c).should_receive('_send').times(3).with_args(re.compile(
        '^RCPT TO:<\w+>\\r\\n'))
    flexmock(c).should_receive('_read').times(3).and_return('250 2.1.5 OK')
    c.rcptto(('foo', 'bar', 'qux'))


def test_rcptto_unexpected_response():
    c = DspamClient()
    flexmock(c).should_receive('_send').once().with_args(
        re.compile('^RCPT TO:<\w+>\\r\\n'))
    flexmock(c).should_receive('_read').once().and_return(
        '550 5.5.1 No such user')
    with pytest.raises(DspamClientError):
        c.rcptto(('foo'))


def test_data_unexpected_response_at_data():
    c = DspamClient()
    flexmock(c).should_receive('_send').once().with_args('DATA\r\n')
    flexmock(c).should_receive('_read').once().and_return(
        '451 Some error ocurred')
    with pytest.raises(DspamClientError):
        c.data('Sample message')


def test_data_dotstuffing():
    c = DspamClient()
    c._recipients = ['foo']
    flexmock(c).should_receive('_send').with_args('DATA\r\n')
    flexmock(c).should_receive('_read').and_return(
        '354 Enter mail, end with "." on a line by itself').and_return(
        '250 2.5.0 <foo> Message accepted for delivery')
    flexmock(c).should_receive('_send').with_args('..')
    flexmock(c).should_receive('_send').with_args('.\r\n')
    flexmock(c).should_receive('_peek').once().and_return(
        '250 2.5.0 <foo> Message ')
    c.data('.')


def test_case_insensitive_recipient_lmtp_mode():
    c = DspamClient()
    c._recipients = ['FOO']
    flexmock(c).should_receive('_send').with_args('DATA\r\n')
    flexmock(c).should_receive('_read').and_return(
        '354 Enter mail, end with "." on a line by itself').and_return(
        '250 2.5.0 <foo> Message accepted for delivery')
    flexmock(c).should_receive('_send').with_args('Some message for FOO')
    flexmock(c).should_receive('_send').with_args('.\r\n')
    flexmock(c).should_receive('_peek').once().and_return(
        '250 2.5.0 <foo> Message ')
    c.data('Some message for FOO')


def test_case_insensitive_recipient_summary_mode():
    """
    The same as the earlier test, but now assuming we told DSPAM
    at MAIL FROM stage to use summary mode.
    """
    c = DspamClient()
    c._recipients = ['FOO']
    flexmock(c).should_receive('_send').with_args('DATA\r\n')
    flexmock(c).should_receive('_read').and_return(
        '354 Enter mail, end with "." on a line by itself').and_return(
        'X-DSPAM-Result: foo; result="Innocent"; class="Innocent"; '
        'probability=0.4000; confidence=1.00; signature=5328aeee248441704964098').and_return(
        '.')
    flexmock(c).should_receive('_send').with_args('Some message for FOO')
    flexmock(c).should_receive('_send').with_args('.\r\n')
    flexmock(c).should_receive('_peek').once().and_return(
        'X-DSPAM-Result: foo; res')
    c.data('Some message for FOO')


def test_result_for_different_recipient():
    """
    Verify that we can handle results even when DSPAM decides to report a different recipient.

    As described in issue #37, sometimes DSPAM will return results for a different
    recipient name than the one that was initially sent by the cliet.
    """
    c = DspamClient()
    c._recipients = ['ALIAS']
    flexmock(c).should_receive('_send').with_args('DATA\r\n')
    flexmock(c).should_receive('_read').and_return(
        '354 Enter mail, end with "." on a line by itself').and_return(
        '250 2.5.0 <USER> Message accepted for delivery')
    flexmock(c).should_receive('_send').with_args('Some message for USER but sent to ALIAS address')
    flexmock(c).should_receive('_send').with_args('.\r\n')
    flexmock(c).should_receive('_peek').once().and_return(
        '250 2.5.0 <USER> Message ')
    c.data('Some message for USER but sent to ALIAS address')
