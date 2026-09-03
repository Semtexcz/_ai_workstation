.PHONY: install status validate update uninstall test

PYTHON ?= python3

install:
	$(PYTHON) scripts/workstation.py install

status:
	$(PYTHON) scripts/workstation.py status

validate:
	$(PYTHON) scripts/workstation.py validate

update:
	$(PYTHON) scripts/workstation.py update

uninstall:
	$(PYTHON) scripts/workstation.py uninstall

test:
	$(PYTHON) -m unittest discover -s tests -v
