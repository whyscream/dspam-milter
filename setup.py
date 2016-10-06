# Copyright (c) 2014, Tom Hendrikx
# All rights reserved.
#
# See LICENSE for the license.

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys

from dspam import VERSION

with open('README.rst') as readme:
    long_description = readme.read()

setup(
    name = 'dspam-milter',
    version = VERSION,
    url = 'https://github.com/whyscream/dspam-milter',
    author = 'Tom Hendrikx',
    author_email = 'dspam-milter@whyscream.net',
    description = 'Milter interface to the DSPAM spam filter engine',
    long_description = long_description,
    packages = ['dspam'],
    include_package_data = True,
    entry_points = {
        'console_scripts': [
            'dspam-milter = dspam.milter:main',
        ]
    },
    install_requires = ['pymilter'],
    zip_safe = True,
)
