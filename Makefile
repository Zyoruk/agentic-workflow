.PHONY: install test lint format docs clean help

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install:  ## Install package with all dependencies
	pip install -e ".[dev,docs,test,embedding]"

install-minimal:  ## Install package with minimal dependencies
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev]"

install-docs:  ## Install documentation dependencies
	pip install -e ".[docs]"

install-test:  ## Install test dependencies
	pip install -e ".[test]"

install-embedding:  ## Install embedding dependencies
	pip install -e ".[embedding]"

install-all: install  ## Alias for install (for backward compatibility)

# Testing
test:  ## Run all tests
	python -m pytest

test-cov:  ## Run tests with coverage
	python -m pytest --cov=src/agentic_workflow --cov-report=html --cov-report=term

test-unit:  ## Run only unit tests
	python -m pytest -m unit

test-integration:  ## Run only integration tests
	python -m pytest -m integration

test-fast:  ## Run tests excluding slow ones
	python -m pytest -m "not slow"

# Code Quality
lint:  ## Run linting
	flake8 src/ tests/
	mypy src/

pre-commit-lint:  ## Run linting for pre-commit hook
	flake8 src/ tests/
	mypy src/

pre-commit-format:  ## Run formatting for pre-commit hook
	black src/ tests/
	isort src/ tests/

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
	$(MAKE) test

# Documentation
docs-init:  ## Initialize Sphinx API documentation structure
	rm -rf docs/api
	mkdir -p docs/api
	sphinx-quickstart docs/api --quiet --project "Agentic Workflow" --author "Zyoruk" --release "0.3.0" --language "en" --ext-autodoc --ext-viewcode --ext-githubpages --makefile --batchfile
	@echo "✅ API documentation structure initialized!"
	@echo "📝 Updating Sphinx configuration..."
	@echo "import os\nimport sys\nsys.path.insert(0, os.path.abspath('../..'))\n\nproject = 'Agentic Workflow'\ncopyright = '2024, Zyoruk'\nauthor = 'Zyoruk'\nrelease = '0.3.0'\n\n# GitHub repository configuration\nhtml_theme = 'sphinx_rtd_theme'\nhtml_theme_options = {\n    'navigation_depth': 4,\n    'titles_only': False,\n    'logo_only': False,\n    'display_version': True,\n    'prev_next_buttons_location': 'both',\n    'style_external_links': True,\n    'style_nav_header_background': '#2980B9',\n    'collapse_navigation': True,\n    'sticky_navigation': True,\n    'includehidden': True,\n}\n\n# GitHub pages configuration\nhtml_baseurl = 'https://zyoruk.github.io/agentic-workflow/'\nhtml_show_sourcelink = True\nhtml_context = {\n    'display_github': True,\n    'github_user': 'zyoruk',\n    'github_repo': 'agentic-workflow',\n    'github_banner': True,\n    'github_button': True,\n    'github_type': 'star',\n    'github_count': True,\n    'github_ribbon': 'fork',\n}\n\nextensions = [\n    'sphinx.ext.autodoc',\n    'sphinx.ext.viewcode',\n    'sphinx.ext.napoleon',\n    'sphinx.ext.intersphinx',\n    'sphinx.ext.autosummary',\n    'sphinx.ext.githubpages',\n]\n\n# Docstring processing\nnapoleon_google_docstring = True\nnapoleon_numpy_docstring = False\nnapoleon_include_init_with_doc = True\nnapoleon_include_private_with_doc = True\nnapoleon_include_special_with_doc = True\nnapoleon_use_admonition_for_examples = True\nnapoleon_use_admonition_for_notes = True\nnapoleon_use_admonition_for_references = True\nnapoleon_use_ivar = True\nnapoleon_use_param = True\nnapoleon_use_rtype = True\nnapoleon_type_aliases = None\n\n# Autodoc settings\nautodoc_default_options = {\n    'members': True,\n    'member-order': 'bysource',\n    'special-members': '__init__',\n    'undoc-members': True,\n    'exclude-members': '__weakref__',\n    'show-inheritance': True,\n    'inherited-members': True,\n}\n\n# Intersphinx settings\nintersphinx_mapping = {\n    'python': ('https://docs.python.org/3', None),\n    'fastapi': ('https://fastapi.tiangolo.com/', None),\n    'langchain': ('https://api.python.langchain.com/en/latest/', None),\n}\n\n# Docstring processing settings\ndocstring_processor = 'sphinx.ext.napoleon'\ndocstring_processor_options = {\n    'napoleon_google_docstring': True,\n    'napoleon_numpy_docstring': False,\n    'napoleon_include_init_with_doc': True,\n    'napoleon_include_private_with_doc': True,\n    'napoleon_include_special_with_doc': True,\n    'napoleon_use_admonition_for_examples': True,\n    'napoleon_use_admonition_for_notes': True,\n    'napoleon_use_admonition_for_references': True,\n    'napoleon_use_ivar': True,\n    'napoleon_use_param': True,\n    'napoleon_use_rtype': True,\n}\n\n# Cross-reference settings\ndefault_role = 'py:obj'\nnitpicky = True\nnitpick_ignore = [\n    ('py:class', 'ValidationError'),\n    ('py:class', 'agentic_workflow.ValidationError'),\n    ('py:class', 'agentic_workflow.core.exceptions.ValidationError'),\n    ('py:class', 'agentic_workflow.guardrails.ValidationError'),\n    ('py:class', 'agentic_workflow.guardrails.input_validation.ValidationError'),\n]\n\n# Autosummary settings\nautosummary_generate = True\nautosummary_imported_members = True\nautosummary_mock_imports = ['langchain', 'fastapi']\n" > docs/api/conf.py
	@echo "📝 Creating API documentation structure..."
	@echo "API Documentation\n=================\n\n.. toctree::\n   :maxdepth: 2\n   :caption: Contents:\n\n   modules\n\nIndices and tables\n==================\n\n* :ref:\`genindex\`\n* :ref:\`modindex\`\n* :ref:\`search\`" > docs/api/index.rst
	@echo "📝 Creating modules documentation..."
	@echo "Modules\n=======\n\n.. autosummary::\n   :toctree: _autosummary\n   :template: module.rst\n   :recursive:\n\n   agentic_workflow" > docs/api/modules.rst
	@echo "✅ API documentation setup complete!"

docs-autodoc:  ## Generate API documentation from docstrings
	cd docs/api && sphinx-apidoc -o _autosummary ../../src/agentic_workflow -f -M
	cd docs/api && make html

docs-check-format:  ## Check docstring formatting
	@echo "Checking docstring formatting..."
	@python tools/scripts/check_docstrings.py src/agentic_workflow

docs-fix-format:  ## Fix docstring formatting issues
	@echo "Fixing docstring formatting..."
	@python tools/scripts/check_docstrings.py src/agentic_workflow --fix

docs: docs-check-format docs-autodoc  ## Build API documentation with Sphinx

docs-sphinx: docs-autodoc  ## Build API documentation with Sphinx

docs-mkdocs:  ## Build MkDocs documentation
	mkdocs build

docs-serve-sphinx: docs-sphinx  ## Serve Sphinx API documentation
	python -m http.server 8000 --directory docs/api/_build/html

docs-serve-mkdocs:  ## Serve MkDocs documentation
	mkdocs serve

docs-clean:  ## Clean documentation build artifacts
	cd docs/api && make clean
	rm -rf site/
	rm -rf docs/api/_build/

docs-check:  ## Check documentation links and build
	mkdocs build --strict
	cd docs/api && make linkcheck

# Development
dev-setup: install  ## Setup development environment
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✅ Development environment setup complete!"

dev-down:  ## Stop development services
	docker-compose -f docker-compose.dev.yml down

# Cleanup
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
	$(MAKE) docs-clean

# Package Management
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
