.PHONY: install test lint format docs clean help

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package and dependencies
	pip install -e ".[dev,docs,test]"

test:  ## Run tests
	python -m pytest

test-cov:  ## Run tests with coverage
	python -m pytest --cov=src/agentic_workflow --cov-report=html --cov-report=term

test-unit:  ## Run only unit tests
	python -m pytest -m unit

test-integration:  ## Run only integration tests
	python -m pytest -m integration

test-fast:  ## Run tests excluding slow ones
	python -m pytest -m "not slow"

lint:  ## Run linting
	flake8 src/ tests/
	mypy src/

pre-commit:  ## Run all pre-commit hooks
	pre-commit run --all-files

format:  ## Format code
	black src/ tests/
	isort src/ tests/

format-check:  ## Check code formatting
	black --check src/ tests/
	isort --check-only src/ tests/

quality:  ## Run all quality checks
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) pre-commit
	$(MAKE) test

docs:  ## Build documentation with Sphinx
	cd docs && make html

docs-serve:  ## Serve documentation with MkDocs
	mkdocs serve

clean:  ## Clean build artifacts
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

dev-setup: install  ## Setup development environment
	pre-commit install
	@echo "✅ Development environment setup complete!"

dev-down:  ## Stop development services
	docker-compose -f docker-compose.dev.yml down

package-check:  ## Check if package can be imported
	python -c "import agentic_workflow; print(f'✅ Package {agentic_workflow.__version__} imported successfully!')"

# Version Management with Commitizen
version-check:  ## Check current version
	cz version

version-bump:  ## Automatically bump version based on conventional commits
	cz bump

version-bump-dry:  ## Show what version would be bumped to (dry run)
	cz bump --dry-run

changelog:  ## Generate/update CHANGELOG.md
	cz changelog

commit:  ## Create a conventional commit interactively
	cz commit

release:  ## Create a release (bump version, update changelog, create tag)
	cz bump --changelog

info:  ## Show conventional commit info
	cz info
