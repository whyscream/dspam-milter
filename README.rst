dspam-milter README
===================

DSPAM milter is an implementation of the milter interface available in 
several MTAs for DSPAM_, a statistical spam and content filter for e-mail.
The milter talks to the DSPAM daemon over the regular DSPAM socket, using
the DLMTP protocol.

Development of dspam-milter is hosted on Github_, releases can be downloaded
from Pypi_. For questions, bugs and patches, please open an issue_. You can
also try to send an e-mail_.

.. image:: https://travis-ci.org/whyscream/dspam-milter.png?branch=master 
   :target: https://travis-ci.org/whyscream/dspam-milter
   :alt: build status

Requirements
============

* Python 2.7 (python)
* DSPAM running in daemon mode

To use the milter, you also need:

* pymilter_ (python-milter)

Installation
============

To install, simply run ``python setup.py install`` in the distibution root.

Milter usage
============

Dspam-milter is a ready to use application. The command ``dspam-milter`` should
have been installed in your path. Behaviour of the daemon can be controlled
by a configuration file. You can create the default config by running 
``dspam-milter --dump-config > /etc/dspam-milter.cfg``.

In general, dlmtp_* settings under `[dspam]` need to be configured, and 
DSPAM configuration needs to be altered to match these. Details on which
changes need to be made in the DSPAM configuration is also available 
in the config file.

When the configuration files have been altered and DSPAM is reloaded to enable
the new config, you can run dspam-milter by executing ``dspam-milter 
--config /etc/dspam-milter.cfg``. There is also an upstart init script available
in the misc/ folder for those running Ubuntu.

Features
========

Currently the package contains:

* dspam.client: A client (python class) that can talk to a DSPAM daemon over a socket.
* dspam.milter: A milter application to use DSPAM classification in an MTA.


License
=======

The dspam-milter code is available under the New (3-clause) BSD license.
See LICENSE for details.


.. _DSPAM: http://sourceforge.net/projects/dspam
.. _Github: http://github.com/whyscream/dspam-milter
.. _Pypi: https://pypi.python.org/pypi/dspam-milter
.. _issue: https://github.com/whyscream/dspam-milter/issues
.. _e-mail: dspam-milter@whyscream.net
.. _pymilter: https://pypi.python.org/pypi/pymilter
