SHELL := /bin/bash
.DEFAULT_GOAL := help
.SHELLFLAGS = -e -c
.ONESHELL:
.SILENT:

PYTHON_VERSION := 3.13

PIP_INSTALL_ARGS ?= -e

.PHONY: venv
venv: venv/lib/python$(PYTHON_VERSION)/site-packages ## Create the virtual environment and install dependencies

.PHONY: run
run: venv/lib/python$(PYTHON_VERSION)/site-packages ## Run the application
	. ./venv/bin/activate
	template

.PHONY: build
build: venv/lib/python$(PYTHON_VERSION)/site-packages ## Build the wheel
	. ./venv/bin/activate
	if ! [ -d venv/lib/python$(PYTHON_VERSION)/site-packages/setuptools ]; then
		pip install $(PIP_INSTALL_ARGS) ".[build]"
	fi
	python3 -m build --wheel --outdir dist

export TWINE_USERNAME ?= fa-krypton-bot

.PHONY: release
release: env-TWINE_USERNAME env-TWINE_PASSWORD ## Upload the wheel
	. ./venv/bin/activate
	if ! [ -d dist/ ]; then
		$(MAKE) build
	fi
	if ! [ -d venv/lib/python$(PYTHON_VERSION)/site-packages/twine ]; then
		pip install $(PIP_INSTALL_ARGS) ".[build]"
	fi
	python3 -m twine upload \
		-u "$(TWINE_USERNAME)" \
		-p "$(TWINE_PASSWORD)" \
		dist/*

##@ Code quality

.PHONY: check
check: check/format check/lint ## Run all non-testing checks

.PHONY: check/format
check/format: venv/lib/python$(PYTHON_VERSION)/site-packages ## Run the formatter
	. ./venv/bin/activate
	if ! command -v black > /dev/null 2>&1 || ! command -v isort > /dev/null 2>&1; then \
		pip install $(PIP_INSTALL_ARGS) ".[format]"
	fi
	isort . --check-only
	black . --check

.PHONY: check/lint
check/lint: venv/lib/python$(PYTHON_VERSION)/site-packages ## Run the linter
	. ./venv/bin/activate
	if ! command -v flake8 > /dev/null || ! command -v mypy > /dev/null; then
		pip install $(PIP_INSTALL_ARGS) ".[lint]"
	fi
	flake8
	mypy .

.PHONY: format
format: venv/lib/python$(PYTHON_VERSION)/site-packages ## Run the formatter
	. ./venv/bin/activate
	if ! command -v black > /dev/null 2>&1 || ! command -v isort > /dev/null 2>&1; then \
		pip install $(PIP_INSTALL_ARGS) ".[format]"
	fi
	isort .
	black .

.PHONY: lint
lint: check/lint ## Alias for check/lint

.PHONY: test
test: venv/lib/python$(PYTHON_VERSION)/site-packages ## Run the tests
	. ./venv/bin/activate
	if ! command -v pytest > /dev/null; then \
		pip install $(PIP_INSTALL_ARGS) ".[test]"
	fi
	pytest

##@ Utilities

.PHONY: assert/python-version
assert/python-version: ## Check the version of python
	test $$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2) = $(PYTHON_VERSION) || (echo "Python $(PYTHON_VERSION) is required." && exit 1)

env-%:
	: $${$*?Environment variable $* not set}

.PHONY: help
help: ## Displays help info
	awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Internal

venv/bin/pip: assert/python-version
	python3 -m venv venv

venv/lib/python$(PYTHON_VERSION)/site-packages: venv/bin/pip
	. ./venv/bin/activate
	pip install $(PIP_INSTALL_ARGS) .

