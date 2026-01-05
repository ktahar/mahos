.PHONY: all format lint install-dev test docs browse clean

ifeq ($(OS),Windows_NT)
    OPEN := "start"
else
    UNAME := $(shell uname -s)
    ifeq ($(UNAME),Linux)
        OPEN := xdg-open
    else
        OPEN := open
    endif
endif

all: format lint test

format:
	black .

lint:
	flake8 . --show-source --statistics

install-dev:
	python -m pip install -e ./pkgs/mahos -e ./pkgs/mahos-dq

test:
	@python -c "import mahos, mahos_dq" >/dev/null 2>&1 || make install-dev
	python -m pytest --timeout=10

docs:
	sphinx-build -b html docs-src docs

browse:
	$(OPEN) docs/index.html

dq-ext:
	cd pkgs/mahos-dq-ext/src/mahos_dq_ext && make

clean:
	$(RM) -r docs
	$(RM) -r docs-src/*/generated
