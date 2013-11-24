# Copyright (c) 2012, Tom Hendrikx
# All rights reserved.
#
# See LICENSE for the license.

from distutils.core import setup

setup(name='pydspam',
    description='Python utilities for interacting with DSPAM ',
    author='Tom Hendrikx',
    author_email='pydspam@whyscream.net',
    url='https://github.com/whyscream/pydspam',
    version='GIT',
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
)
