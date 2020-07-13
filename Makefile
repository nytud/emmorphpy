# Bash is needed for time
SHELL := /bin/bash
DIR := ${CURDIR}
all:
	@echo "See Makefile for possible targets!"

install-dep-packages:
	sudo -E apt-get update
	sudo -E apt-get -yq --no-install-suggests --no-install-recommends $(travis_apt_get_options) install `cat Aptfile`

check-hfst-lookup:
	@command -v hfst-lookup >/dev/null 2>&1 || { echo >&2 'Command `hfst-lookup` could not be found!'; exit 1; }

dist/*.whl dist/*.tar.gz: check-hfst-lookup
	@echo "Building package..."
	python3 setup.py sdist bdist_wheel

build: dist/*.whl dist/*.tar.gz

install-user: build
	@echo "Installing package to user..."
	pip3 install dist/*.whl

test:
	@echo "Running tests..."
	time (cd /tmp && python3 -m emmorphpy --raw -i $(DIR)/tests/test_words.txt | \
			diff -sy --suppress-common-lines - $(DIR)/tests/gold_output.txt 2>&1 | head -n100)

install-user-test: install-user test
	@echo "The test was completed successfully!"

ci-test: install-user-test

uninstall:
	@echo "Uninstalling..."
	pip3 uninstall -y emmorphpy

install-user-test-uninstall: install-user-test uninstall

clean:
	rm -rf dist/ build/ emmorphpy.egg-info/

clean-build: clean build
