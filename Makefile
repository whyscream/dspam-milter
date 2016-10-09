ifdef WORKON_HOME
	VIRTUALENV = $(WORKON_HOME)/dspam-milter
else
ifdef TRAVIS
	VIRTUALENV = $(HOME)/virtualenv/python$(TRAVIS_PYTHON_VERSION)
	PYTHON_VERSION = $(TRAVIS_PYTHON_VERSION)
else
	VIRTUALENV = $(shell pwd)/env
endif
endif

PYTHON = $(VIRTUALENV)/bin/python
PYTHON_VERSION_MAJOR = $(shell echo $(PYTHON_VERSION) | cut -c 1)

test: $(VIRTUALENV) pymilter
	$(PYTHON) -m pip install -r requirements/test.txt
	$(PYTHON) -m pytest

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	$(RM) -r .coverage .cache

realclean: clean
	$(RM) -r $(VIRTUALENV)

# install unreleased pymilter package for python3
pymilter:
ifeq ($(PYTHON_VERSION_MAJOR),3)
	$(PYTHON) -m pip install misc/pymilter-1.0.1-py3-626d5ae.tar.gz
else
	$(PYTHON) -m pip install pymilter
endif

$(VIRTUALENV):
	virtualenv -p /usr/bin/python$(PYTHON_VERSION) $(VIRTUALENV)


.PHONY: test
