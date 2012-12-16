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

To use the milter, you also need:

* pymilter (python-milter)
* DSPAM (dspam)

Installation
============

To install, simply run ''python setup.py install'' in the distibution root.

License
=======

The pydspam code is available under the New (3-clause) BSD license.
See LICENSE for details.


.. _Python: http://python.org
.. _DSPAM: http://sourceforge.net/projects/dspam
.. _Github: http://github.com/whyscream/pydspam
.. _issue: https://github.com/whyscream/pydspam/issues
.. _e-mail: pydspam@whyscream.net
