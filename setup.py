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

# http://pytest.org/dev/goodpractises.html#integration-with-setuptools-test-commands
class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['--cov', 'dspam', '.']
        self.test_suite = True
    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

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
    tests_require=['pytest', 'pytest-cov', 'pytest-pep8','flexmock'],
    cmdclass = {'test': PyTest},
)
