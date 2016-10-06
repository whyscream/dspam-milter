ifdef WORKON_HOME
	VIRTUALENV = $(WORKON_HOME)/dspam-milter
else
	VIRTUALENV = $(shell pwd)/env
endif

PYTHON_VERSION := 2
PYTHON = $(VIRTUALENV)/bin/python

test: $(VIRTUALENV)
	$(PYTHON) -m pip install -r requirements/test.txt
	$(PYTHON) -m pytest

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	$(RM) -r .coverage .cache

realclean: clean
	$(RM) -r $(VIRTUALENV)

$(VIRTUALENV):
	virtualenv -p /usr/bin/python$(PYTHON_VERSION) $(VIRTUALENV)


.PHONY: test
