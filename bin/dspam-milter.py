#!/usr/bin/env python

import sys
import dspam.milter

# Allow passing an alternative config file from the command-line
config_file = '/etc/dspam-milter.py'
if len(sys.argv) > 1:
    config_file = sys.argv[1]

dspam.milter.runmilter(config_file)
