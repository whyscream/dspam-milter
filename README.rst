pydspam README
==============

Pydspam is a collection of python libraries and programs that provide a 
Python_ interface to DSPAM_. This will enable more developers to 
harness the power of DSPAM in new ways, without having knowledge of C.

Development of pydspam is hosted on Github_. For questions, bugs and patches,
please open an issue_ there. You can also try to send an e-mail_.

Features
========

Currently the package contains:

* dspam.client: A client that can talk to a DSPAM daemon over a socket.
* dspam.milter: A milter application to use DSPAM classification in an MTA.

Requirements
============

* Python 2.7 (python)
* DSPAM running in daemon mode

To use the milter, you also need:

* pymilter (python-milter)
* daemon (python-daemon)

Installation
============

To install, simply run ``python setup.py install`` in the distibution root.

Milter usage
============

The Milter is a ready to use application. The command ``dspam-milter`` should
have been installed in your path. Behaviour of the daemon can be controlled
by editing ``/etc/dspam-milter.cfg``. In general dlmtp_* settings need to be
configured, and added to dspam.conf. Start the milter process with the
command: ``dspam-milter start``.

License
=======

The pydspam code is available under the New (3-clause) BSD license.
See LICENSE for details.


.. _Python: http://python.org
.. _DSPAM: http://sourceforge.net/projects/dspam
.. _Github: http://github.com/whyscream/pydspam
.. _issue: https://github.com/whyscream/pydspam/issues
.. _e-mail: pydspam@whyscream.net
