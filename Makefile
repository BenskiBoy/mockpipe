# Makefile for mockpipe project

# Variables
PYTHON = python3
PIP = pip3
SOURCE_DIR = mockpipe
TEST_DIR = tests
REQUIREMENTS = requirements.txt

# Default target
.PHONY: all
all: install

# Install dependencies
.PHONY: install
install:
	$(PIP) install -r $(REQUIREMENTS)

# Install development dependencies
.PHONY: install-dev
install-dev: install
	$(PIP) install -e ".[dev]"

# Install package locally in editable mode
.PHONY: install-local
install-local: build
	$(PIP) install -e .

# Run tests
.PHONY: test
test:
	pytest $(TEST_DIR)

# Run linting
.PHONY: lint
lint:
	flake8 $(SOURCE_DIR)
	black --check $(SOURCE_DIR)

# Format code
.PHONY: format
format:
	black $(SOURCE_DIR)

# Type checking
.PHONY: typecheck
typecheck:
	mypy $(SOURCE_DIR)

# Clean build artifacts
.PHONY: clean
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	find . -name "*.pyc" -delete

# Run the application
.PHONY: run
run:
	$(PYTHON) -m $(SOURCE_DIR)

# Build package
.PHONY: build
build: clean
	$(PYTHON) setup.py sdist bdist_wheel

# Help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  all        - Install dependencies (default)"
	@echo "  install    - Install dependencies"
	@echo "  install-dev- Install development dependencies"
	@echo "  install-local - Install package locally in editable mode"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linting"
	@echo "  format     - Format code"
	@echo "  typecheck  - Run type checking"
	@echo "  run        - Run the application"
	@echo "  build      - Build package"
	@echo "  clean      - Clean build artifacts"
	@echo "  help       - Show this help message"