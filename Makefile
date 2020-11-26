# Bash is needed for time
.DEFAULT_GOAL = all
SHELL := /bin/bash -o pipefail
RED := $(shell tput setaf 1)
GREEN := $(shell tput setaf 2)
NOCOLOR := $(shell tput sgr0)
PYTHON := python3
VENVDIR := $(CURDIR)/venv
VENVPIP := $(VENVDIR)/bin/python -m pip
VENVPYTHON := $(VENVDIR)/bin/python

# Module specific parameters
MODULE := emmorphpy
MODULE_PARAMS := --raw

# This target does not show as possible target with bash completion
--extra-deps:
 	# Do extra stuff (e.g. compiling, downloading) before building the package
	@command -v hfst-lookup >/dev/null 2>&1 || \
		(echo >&2 "$(RED)Command 'hfst-lookup' could not be found!$(NOCOLOR)"; exit 1)
.PHONY: --extra-deps

--clean-extra-deps:
	@exit 0
	# @rm -rf stuff
.PHONY: --clean-extra-deps

# From here only generic parts

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

all: clean venv build install test
	@echo "$(GREEN)The package is succesfully installed into the virtualenv ($(VENVDIR)) and all tests are OK!$(NOCOLOR)"

install-dep-packages:
	@echo "Installing needed packages from Aptfile..."
	@command -v apt-get >/dev/null 2>&1 || \
			(echo >&2 "$(RED)Command 'apt-get' could not be found!$(NOCOLOR)"; exit 1)
	@[[ $$(dpkg -l | grep -wcf $(CURDIR)/Aptfile) -eq $$(cat $(CURDIR)/Aptfile | wc -l) ]] || \
		(sudo -E apt-get update && \
		sudo -E apt-get -yq --no-install-suggests --no-install-recommends $(travis_apt_get_options) install \
			`cat $(CURDIR)/Aptfile`)
	@echo "$(GREEN)Needed packages are succesfully installed!$(NOCOLOR)"
.PHONY: install-dep-packages

venv:
	@echo "Creating virtualenv...$(NOCOLOR)"
	rm -rf $(VENVDIR)
	$(PYTHON) -m venv $(VENVDIR)
	$(VENVPIP) install wheel
	$(VENVPIP) install -r requirements-dev.txt
	@echo "$(GREEN)Virtualenv is succesfully created!$(NOCOLOR)"
.PHONY: venv

build: install-dep-packages venv --extra-deps
	@echo "Building package..."
	@[[ -z "$$(ls dist/*.whl dist/*.tar.gz 2> /dev/null)" ]] || \
		(echo -e "$(RED)dist/*.whl dist/*.tar.gz files exists.\nPlease use 'make clean' before build!$(NOCOLOR)"; \
		exit 1)
	@$(VENVPYTHON) setup.py sdist bdist_wheel
	@echo "$(GREEN)Package is succesfully built!$(NOCOLOR)"
.PHONY: build

install: build
	@echo "Installing package to user..."
	$(VENVPIP) install --upgrade dist/*.whl
	@echo "$(GREEN)Package is succesfully installed!$(NOCOLOR)"
.PHONY: install

test:
	@echo "Running tests..."
	@[[ $$(compgen -G "$(CURDIR)/tests/inputs/*.in") ]] || (echo "$(RED)No input testfiles found!$(NOCOLOR)"; exit 1)
	for TEST_INPUT in $(CURDIR)/tests/inputs/*.in; do \
		TEST_OUTPUT=$(CURDIR)/tests/outputs/$$(basename $${TEST_INPUT%in}out) ; \
		time (cd /tmp && $(VENVPYTHON) -m $(MODULE) $(MODULE_PARAMS) -i $${TEST_INPUT} | \
		diff -sy --suppress-common-lines - $${TEST_OUTPUT} 2>&1 | head -n100); \
	done
	@echo "$(GREEN)The test was completed successfully!$(NOCOLOR)"
	@echo "Comparing GIT TAG (\"$(TRAVIS_TAG)\") with pacakge version (\"v$(OLDVER)\")..."
	@[[ "$(TRAVIS_TAG)" == "v$(OLDVER)" || "$(TRAVIS_TAG)" == "" ]] && \
	  echo "$(GREEN)OK!$(NOCOLOR)" || \
	  (echo "$(RED)Versions do not match!$(NOCOLOR)"; exit 1)
.PHONY: test

uninstall:
	@echo "Uninstalling..."
	@[[ ! -d $(VENVDIR) || -z $$($(VENVPIP) list | grep -w $(MODULE)) ]] || $(VENVPIP) uninstall -y $(MODULE)
	@echo "$(GREEN)The package was uninstalled successfully!$(NOCOLOR)"
.PHONY: uninstall

clean: --clean-extra-deps
	rm -rf $(VENVDIR) dist/ build/ $(MODULE).egg-info/
.PHONY: clean

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
	@[[ ! -z "$(NEWVER)" ]] || \
		(echo -e "$(RED)Do not call this target!\nUse 'release-major', 'release-minor' or 'release-patch'!$(NOCOLOR)"; \
		 exit 1)
	@[[ -z $$(git status --porcelain) ]] || (echo "$(RED)Working dir is dirty!$(NOCOLOR)"; exit 1)
	@echo "NEW VERSION: $(NEWVER)"
	# Clean install, test and tidy up
	@make clean uninstall install test uninstall clean
	@sed -i -r "s/__version__ = '$(OLDVER)'/__version__ = '$(NEWVER)'/" $(MODULE)/version.py
	@git add $(MODULE)/version.py
	@git commit -m "Release $(NEWVER)"
	@git tag -a "v$(NEWVER)" -m "Release $(NEWVER)"
	@git push
	@git push --tags
.PHONY: __release
