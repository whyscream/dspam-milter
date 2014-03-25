# Copyright (c) 2014, Tom Hendrikx
# All rights reserved.
#
# See LICENSE for the license.

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys

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

install_requires = ['pymilter']
if sys.version_info[0] == 2 and sys.version_info[1] < 7:
    install_requires.append('argparse')

setup(
    name = 'dspam-milter',
    version = 'GIT',
    description = 'Milter interface to the DSPAM spam filter engine',
    packages = ['dspam'],
    include_package_data = True,
    entry_points = {
        'console_scripts': [
            'dspam-milter = dspam.milter:main',
        ]
    },
    install_requires = install_requires,
    zip_safe = True,
    tests_require=['pytest-cov', 'pytest-pep8', 'pytest', 'flexmock'],
    cmdclass = {'test': PyTest},
)
