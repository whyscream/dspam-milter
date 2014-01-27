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
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

setup(
    name = 'dspam-milter',
    version = 'GIT',
    packages = ['dspam'],
    scripts = ['bin/dspam-milter'],
    include_package_data = True,
    install_requires = ['pymilter'],
    zip_safe = True,
    tests_require=['pytest', 'flexmock'],
    cmdclass = {'test': PyTest},
)
