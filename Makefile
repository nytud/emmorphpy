# Bash is needed for time
SHELL := /bin/bash -o pipefail
DIR := ${CURDIR}
red := $(shell tput setaf 1)
green := $(shell tput setaf 2)
sgr0 := $(shell tput sgr0)
# DEP_COMMAND := "command"
# DEP_FILE := "file"
MODULE := "emmorphpy"
MODULE_PARAMS := "--raw"
TEST_INPUT := "test_words.txt"
TEST_OUTPUT := "gold_output.txt"

# Parse version string and create new version. Originally from: https://github.com/mittelholcz/contextfun
# Variable is empty in Travis-CI if not git tag present
TRAVIS_TAG ?= ""
OLDVER := $$(grep -P -o "(?<=__version__ = ')[^']+" $(MODULE)/version.py)

MAJOR := $$(echo $(OLDVER) | sed -r s"/([0-9]+)\.([0-9]+)\.([0-9]+)/\1/")
MINOR := $$(echo $(OLDVER) | sed -r s"/([0-9]+)\.([0-9]+)\.([0-9]+)/\2/")
PATCH := $$(echo $(OLDVER) | sed -r s"/([0-9]+)\.([0-9]+)\.([0-9]+)/\3/")

NEWMAJORVER="$$(( $(MAJOR)+1 )).0.0"
NEWMINORVER="$(MAJOR).$$(( $(MINOR)+1 )).0"
NEWPATCHVER="$(MAJOR).$(MINOR).$$(( $(PATCH)+1 ))"

all:
	@echo "See Makefile for possible targets!"

# extra:
# 	# Do extra stuff (e.g. compiling, downloading) before building the package

# clean-extra:
# 	rm -rf extra stuff

install-dep-packages:
# 	# Install packages in Aptfile
	sudo -E apt-get update
	sudo -E apt-get -yq --no-install-suggests --no-install-recommends $(travis_apt_get_options) install `cat Aptfile`

check:
# 	# Check for file or command
	@command -v hfst-lookup >/dev/null 2>&1 || { echo >&2 'Command `hfst-lookup` could not be found!'; exit 1; }

dist/*.whl dist/*.tar.gz: check # extra
	@echo "Building package..."
	python3 setup.py sdist bdist_wheel

build: dist/*.whl dist/*.tar.gz

install-user: build
	@echo "Installing package to user..."
	pip3 install dist/*.whl

test:
	@echo "Running tests..."
	time (cd /tmp && python3 -m ${MODULE} ${MODULE_PARAMS} -i $(DIR)/tests/${TEST_INPUT} | \
	diff -sy --suppress-common-lines - $(DIR)/tests/${TEST_OUTPUT} 2>&1 | head -n100)

install-user-test: install-user test
	@echo "$(green)The test was completed successfully!$(sgr0)"

check-version:
	@echo "Comparing GIT TAG (\"$(TRAVIS_TAG)\") with pacakge version (\"v$(OLDVER)\")..."
	 @[[ "$(TRAVIS_TAG)" == "v$(OLDVER)" || "$(TRAVIS_TAG)" == "" ]] && \
	  echo "$(green)OK!$(sgr0)" || \
	  (echo "$(red)Versions do not match!$(sgr0)" && exit 1)

ci-test: install-user-test check-version

uninstall:
	@echo "Uninstalling..."
	pip3 uninstall -y ${MODULE}

install-user-test-uninstall: install-user-test uninstall

clean: # clean-extra
	rm -rf dist/ build/ ${MODULE}.egg-info/

clean-build: clean build

# Do actual release with new version. Originally from: https://github.com/mittelholcz/contextfun
release-major:
	@make -s __release NEWVER=$(NEWMAJORVER)
.PHONY: release-major


release-minor:
	@make -s __release NEWVER=$(NEWMINORVER)
.PHONY: release-minor


release-patch:
	@make -s __release NEWVER=$(NEWPATCHVER)
.PHONY: release-patch


__release:
	@if [[ -z "$(NEWVER)" ]] ; then \
		echo 'Do not call this target!' ; \
		echo 'Use "release-major", "release-minor" or "release-patch"!' ; \
		exit 1 ; \
		fi
	@if [[ $$(git status --porcelain) ]] ; then \
		echo 'Working dir is dirty!' ; \
		exit 1 ; \
		fi
	@echo "NEW VERSION: $(NEWVER)"
	@make clean uninstall install-user-test-uninstall
	@sed -i -r "s/__version__ = '$(OLDVER)'/__version__ = '$(NEWVER)'/" $(MODULE)/version.py
	@make check-version
	@git add $(MODULE)/version.py
	@git commit -m "Relaase $(NEWVER)"
	@git tag -a "v$(NEWVER)" -m "Release $(NEWVER)"
	@git push --tags
.PHONY: __release
