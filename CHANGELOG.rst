Changelog for dspam-milter
==========================

This file contains a somewhat user-friendly overview of changes done in a 
release. It also lists people that contributed bugs, patches, ideas
or other improvements.

For the gory details on each release, please use the diff links at the bottom
of each release.

HEAD
----

* Allowed DSPAM to change recipient names, after report from Marco Favero

https://github.com/whyscream/dspam-milter/compare/0.3.4...HEAD

0.3.4
-----

* Dropped shell script for creating releases, just use a (dev) version everywhere
* Old-style init script for debian (contributed by darac in `PR 18`_)
* Improved pid file handling after report from Alan Chandler
* Renamed `--dump-config` arg to `--default-config`
* Made recipient handling case-insensitive after report from darac
* Added CHANGELOG for functional overview of improvements and contributions

https://github.com/whyscream/dspam-milter/compare/0.3.3...HEAD

.. _PR 18: https://github.com/whyscream/dspam-milter/pull/18

0.3.3
-----

* Fixed release script
* Re-released broken 0.3.2 release

https://github.com/whyscream/dspam-milter/compare/0.3.2...0.3.3

0.3.2
-----

* Added test for proper rst formatting in README
* Refactored setup.py from distrbute to setuptools
* Added cmdline arg parsing, and basic args (`--config`, `--dump-config`, `--version`)
* Added MTA queue id to all INFO level logging
* Lots of added details in README

https://github.com/whyscream/dspam-milter/compare/0.3.1...0.3.2

0.3.1
-----

* Fixed README rendering for Pypi

https://github.com/whyscream/dspam-milter/compare/0.3...0.3.1

0.3
---

* Initial public release

https://github.com/whyscream/dspam-milter/compare/107fc17c43...0.3
