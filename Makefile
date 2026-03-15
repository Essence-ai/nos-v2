# NeuronOS Makefile

.PHONY: all install install-dev test lint format clean iso docs help

# Default target
all: help

# Install all packages in development mode
install:
	pip install -e neuronos-hardware
	pip install -e neuronos-vm-manager

# Install with development dependencies
install-dev:
	pip install -e "neuronos-hardware[dev]"
	pip install -e "neuronos-vm-manager[dev,gui,monitor]"
	pip install -r requirements.txt

# Run all tests
test:
	pytest neuronos-hardware/tests/ -v
	pytest neuronos-vm-manager/tests/ -v

# Run linting
lint:
	ruff check neuronos-hardware/
	ruff check neuronos-vm-manager/
	mypy neuronos-hardware/neuron_hw/
	mypy neuronos-vm-manager/neuronvm/

# Format code
format:
	black neuronos-hardware/
	black neuronos-vm-manager/
	ruff check --fix neuronos-hardware/
	ruff check --fix neuronos-vm-manager/

# Clean build artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/

# Build ISO (requires Arch Linux with archiso)
iso:
	cd neuronos-iso && sudo mkarchiso -v -w /tmp/archiso-tmp -o ~/neuronos-out .

# Build documentation
docs:
	cd neuronos-docs && mkdocs build

# Serve documentation locally
docs-serve:
	cd neuronos-docs && mkdocs serve

# Initialize git repositories
git-init:
	@for dir in neuronos-iso neuronos-hardware neuronos-vm-manager \
	            neuronos-installer neuronos-single-gpu neuronos-docs; do \
		echo "Initializing $$dir..."; \
		cd $$dir && git init && git add . && \
		git commit -m "Initial commit" && cd ..; \
	done
	git init && git add . && git commit -m "Initial NeuronOS project setup"

# Show help
help:
	@echo "NeuronOS Development Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install      Install packages in development mode"
	@echo "  install-dev  Install with development dependencies"
	@echo "  test         Run all tests"
	@echo "  lint         Run linting (ruff, mypy)"
	@echo "  format       Format code (black, ruff)"
	@echo "  clean        Clean build artifacts"
	@echo "  iso          Build NeuronOS ISO (requires Arch Linux)"
	@echo "  docs         Build documentation"
	@echo "  docs-serve   Serve documentation locally"
	@echo "  git-init     Initialize git repositories"
	@echo "  help         Show this help message"
