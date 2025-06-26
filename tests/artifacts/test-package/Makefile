.PHONY: clean build

# ============================================================================ #
# CLEAN COMMANDS
# ============================================================================ #

clean: clean-build clean-pyc ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	
# ============================================================================ #
# BUILD COMMANDS
# ============================================================================ #

build: clean ## builds source and wheel package

	flit build --format wheel

	flit build --format wheel --null-variant

	flit build --format wheel \
		-p "installable_plugin :: feat1 :: val1c"

	flit build --format wheel \
		-p "installable_plugin :: feat2 :: val2b"

	flit build --format wheel \
		-p "installable_plugin :: feat1 :: val1c" \
		-p "installable_plugin :: feat2 :: val2b"

	flit build --format wheel --null-variant --variant-label=null

	flit build --format wheel \
		-p "installable_plugin :: feat1 :: val1c" \
		--variant-label=foo

	flit build --format wheel \
		-p "installable_plugin :: feat2 :: val2b" \
		--variant-label=bar

	variantlib generate-index-json -d dist/
