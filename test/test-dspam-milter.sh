#!/bin/sh

# Simple test utility to pass a message to the milter, and see the results.
# Install libmilter-server0 package from http://milter-manager.sourceforge.net/

TESTDIR=$(dirname $0)
TESTFILE=$1
if test -z "$TESTFILE"; then
    TESTFILE="$TESTDIR"/data/generic.eml
fi

milter-test-server \
    --output-message \
    --connection-spec=inet:2425@localhost \
    --connect-host=mail.example.org \
    --connect-address=inet:1234@192.0.2.1 \
    --helo-fqdn=mail.example.org \
    --envelope-from=sender@example.org \
    --envelope-recipient=recipient@example.net \
    --mail-file=$TESTFILE
