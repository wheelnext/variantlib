.PHONY: clean test coverage build install lint

# ============================================================================ #
# CLEAN COMMANDS
# ============================================================================ #

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	rm -rf .hypothesis/
	rm -rf .pytest_cache/
	rm -f .coverage
	rm -f .dmypy.json
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage*
	rm -fr htmlcov/
	rm -fr .pytest_cache

# ============================================================================ #
# LINT COMMANDS
# ============================================================================ #

lint:
# Lint all files in the current directory (and any subdirectories).
	ruff check --fix

format:
# Format all files in the current directory (and any subdirectories).
	ruff format

# ============================================================================ #
# TEST COMMANDS
# ============================================================================ #

test: ## run tests
	pytest

test-fast: ## run tests quickly - only 1 hypothesis example per test
	pytest --hypothesis-profile fast

test-all: ## run tests on every Python version with tox
	tox

coverage: ## check code coverage
	coverage run --source comp_bench_tools -m pytest
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

# ============================================================================ #
# BUILD COMMANDS
# ============================================================================ #

build: clean ## builds source and wheel package
	pip install --upgrade wheel
	python3 -m build --wheel
	ls -l dist

publish: build
	pip install --upgrade twine
	twine upload --config-file=.pypirc dist/*.whl

# ============================================================================ #
# INSTALL COMMANDS
# ============================================================================ #

install: clean ## install the package to the active Python's site-packages
	pip install -e ".[dev,test]"
