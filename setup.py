# Copyright (c) 2012, Tom Hendrikx
# All rights reserved.
#
# See LICENSE for the license.

from distutils.core import setup, Command

class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys,subprocess
        errno = subprocess.call(['py.test', '--verbose', '--pep8', 'dspam/'])
        raise SystemExit(errno)

setup(name='dspam-milter',
    description='Milter implementation for DSPAM',
    author='Tom Hendrikx',
    author_email='dspam-milter@whyscream.net',
    url='https://github.com/whyscream/dspam-milter',
    version='0.3',
    packages=['dspam'],
    scripts=['bin/dspam-milter'],
    data_files=[('/etc/', ['bin/dspam-milter.cfg'])],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Topic :: Communications :: Email :: Filters'
    ],
    license='New (3-clause) BSD License',
    cmdclass={
        'test': PyTest
    }
)
