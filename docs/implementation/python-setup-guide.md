# Python Development Environment Setup Guide

## Overview

This guide provides detailed instructions for setting up the Python development environment for the agentic workflow project, implementing Task 1.1 from our epics breakdown.

## Prerequisites

- Linux/WSL2 environment (Ubuntu 22.04 recommended)
- Git installed and configured
- Internet connection for package downloads

## 1. Python Environment Setup

### Install Python 3.11+ with pyenv

```bash
# Install pyenv dependencies
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev

# Install pyenv
curl https://pyenv.run | bash

# Add to ~/.zshrc (since user uses zsh)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# Reload shell
source ~/.zshrc

# Install Python 3.11
pyenv install 3.11.8
pyenv global 3.11.8
```

### Create Project Virtual Environment

```bash
# Navigate to project directory
cd /home/zyoruk/Projects/agentic-workflow

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and install basic tools
pip install --upgrade pip
pip install pip-tools setuptools wheel
```

## 2. Project Structure Setup

### Create Python Package Structure

```bash
# Create source directory structure
mkdir -p src/agentic_workflow/{core,agents,graph,api,utils}
mkdir -p tests/{unit,integration,system}
mkdir -p tools/{scripts,config}
mkdir -p docs/{api,user}

# Create __init__.py files
touch src/agentic_workflow/__init__.py
touch src/agentic_workflow/core/__init__.py
touch src/agentic_workflow/agents/__init__.py
touch src/agentic_workflow/graph/__init__.py
touch src/agentic_workflow/api/__init__.py
touch src/agentic_workflow/utils/__init__.py
```

### Create Configuration Files

#### pyproject.toml
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "agentic-workflow"
version = "0.1.0"
description = "AI-driven agentic workflow system for autonomous software development"
authors = [
    {name = "Your Name", email = "your.email@example.com"},
]
readme = "README.md"
requires-python = ">=3.11"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "langchain>=0.1.0",
    "openai>=1.0.0",
    "neo4j>=5.15.0",
    "weaviate-client>=3.25.0",
    "redis>=5.0.0",
    "networkx>=3.2",
    "pydantic>=2.5.0",
    "pandas>=2.1.0",
    "numpy>=1.25.0",
    "asyncio-mqtt>=0.13.0",
    "prometheus-client>=0.19.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "black>=23.11.0",
    "flake8>=6.1.0",
    "mypy>=1.7.0",
    "isort>=5.12.0",
    "pre-commit>=3.5.0",
    "jupyterlab>=4.0.0",
    "ipython>=8.17.0",
]
docs = [
    "sphinx>=7.2.0",
    "sphinx-rtd-theme>=1.3.0",
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.4.0",
]
test = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "coverage>=7.3.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/agentic-workflow"
Documentation = "https://agentic-workflow.readthedocs.io"
Repository = "https://github.com/yourusername/agentic-workflow"

[tool.setuptools.packages.find]
where = ["src"]

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["agentic_workflow"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "neo4j.*",
    "weaviate.*",
    "langchain.*",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src/agentic_workflow",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]
```

#### requirements.txt and requirements-dev.txt
```bash
# Generate requirements files
pip-compile pyproject.toml --output-file requirements.txt
pip-compile pyproject.toml --extra dev --output-file requirements-dev.txt
```

## 3. Code Quality Tools Configuration

### Flake8 Configuration (.flake8)
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503, E501
exclude = 
    .git,
    __pycache__,
    .venv,
    .eggs,
    *.egg,
    build,
    dist,
    docs
per-file-ignores =
    __init__.py:F401
    tests/*:S101,S106
```

### Pre-commit Configuration (.pre-commit-config.yaml)
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Install and Setup Pre-commit
```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files (initial run)
pre-commit run --all-files
```

## 4. CI/CD Pipeline Configuration

### GitLab CI/CD (.gitlab-ci.yml)
```yaml
stages:
  - quality
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  PYTHON_VERSION: "3.11"

cache:
  paths:
    - .cache/pip
    - .venv/

before_script:
  - python -V
  - pip install virtualenv
  - virtualenv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install -e ".[dev,test]"

code_quality:
  stage: quality
  image: python:3.11
  script:
    - black --check src/ tests/
    - isort --check-only src/ tests/
    - flake8 src/ tests/
    - mypy src/
  allow_failure: false

unit_tests:
  stage: test
  image: python:3.11
  script:
    - pytest tests/unit/ -v --cov=src/agentic_workflow --cov-report=xml
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    expire_in: 1 week

integration_tests:
  stage: test
  image: python:3.11
  services:
    - redis:7
    - neo4j:5.15
  variables:
    REDIS_URL: "redis://redis:6379"
    NEO4J_URL: "bolt://neo4j:7687"
  script:
    - pytest tests/integration/ -v
  allow_failure: false

build_package:
  stage: build
  image: python:3.11
  script:
    - pip install build
    - python -m build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week
  only:
    - main
    - develop

build_docker:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t agentic-workflow:$CI_COMMIT_SHA .
    - docker tag agentic-workflow:$CI_COMMIT_SHA agentic-workflow:latest
  only:
    - main
    - develop
```

## 5. Testing Framework Setup

### Pytest Configuration (already in pyproject.toml)

### Sample Test Structure
```bash
# Create sample test files
cat > tests/unit/test_example.py << 'EOF'
"""Example unit test."""
import pytest
from agentic_workflow.utils.example import example_function


def test_example_function():
    """Test example function."""
    result = example_function("test")
    assert result == "test_processed"


@pytest.mark.asyncio
async def test_async_example():
    """Test async functionality."""
    # Example async test
    pass
EOF

cat > tests/integration/test_example_integration.py << 'EOF'
"""Example integration test."""
import pytest


@pytest.mark.integration
def test_database_connection():
    """Test database connectivity."""
    # Example integration test
    pass
EOF
```

## 6. Documentation Setup

### Sphinx Configuration
```bash
# Create docs directory structure
mkdir -p docs/source
cd docs

# Initialize Sphinx
sphinx-quickstart --quiet --project="Agentic Workflow" \
  --author="Your Name" --ext-autodoc --ext-viewcode \
  --ext-napoleon --makefile --no-batchfile source

# Configure Sphinx (docs/source/conf.py additions)
cat >> source/conf.py << 'EOF'

# Add autodoc configuration
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Add Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
EOF
```

### MkDocs Configuration (mkdocs.yml)
```yaml
site_name: Agentic Workflow Documentation
site_url: https://yourdomain.com/agentic-workflow
repo_url: https://github.com/yourusername/agentic-workflow
repo_name: yourusername/agentic-workflow

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate
    - navigation.top
    - search.suggest
    - search.highlight
    - content.tabs.link
    - content.code.annotation
    - content.code.copy
  language: en
  palette:
    - scheme: default
      primary: blue
      accent: blue
      toggle:
        icon: material/toggle-switch-off-outline
        name: Switch to dark mode
    - scheme: slate
      primary: blue
      accent: blue
      toggle:
        icon: material/toggle-switch
        name: Switch to light mode

plugins:
  - search
  - mkdocstrings

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Architecture: architecture.md
  - API Reference: api/
  - Development: development.md

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - admonition
  - pymdownx.arithmatex:
      generic: true
  - footnotes
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.mark
  - attr_list
  - pymdownx.emoji:
      emoji_index: !!python/name:materialx.emoji.twemoji
      emoji_generator: !!python/name:materialx.emoji.to_svg
```

## 7. Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY pyproject.toml .
COPY README.md .

# Install the package
RUN pip install -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "agentic_workflow.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Development (docker-compose.dev.yml)
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - ENVIRONMENT=development
      - REDIS_URL=redis://redis:6379
      - NEO4J_URL=bolt://neo4j:7687
      - NEO4J_AUTH=neo4j/password
    depends_on:
      - redis
      - neo4j
      - weaviate

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  neo4j:
    image: neo4j:5.15
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data

  weaviate:
    image: semitechnologies/weaviate:1.21.2
    ports:
      - "8080:8080"
    environment:
      - QUERY_DEFAULTS_LIMIT=25
      - AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate
      - DEFAULT_VECTORIZER_MODULE=none
      - CLUSTER_HOSTNAME=node1

volumes:
  neo4j_data:
```

## 8. Installation and Verification

### Install Dependencies
```bash
# Activate virtual environment
source .venv/bin/activate

# Install package in development mode
pip install -e ".[dev,docs,test]"

# Verify installation
python -c "import agentic_workflow; print('Package installed successfully!')"
```

### Run Quality Checks
```bash
# Format code
black src/ tests/
isort src/ tests/

# Run linting
flake8 src/ tests/

# Run type checking
mypy src/

# Run tests
pytest

# Generate coverage report
pytest --cov=src/agentic_workflow --cov-report=html
```

### Start Development Services
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Verify services
curl http://localhost:8000/health  # API health check
```

## 9. Development Workflow

### Daily Development Process
1. Activate virtual environment: `source .venv/bin/activate`
2. Pull latest changes: `git pull origin main`
3. Create feature branch: `git checkout -b feature/new-feature`
4. Make changes and write tests
5. Run quality checks: `pre-commit run --all-files`
6. Run tests: `pytest`
7. Commit changes: `git commit -m "feat: add new feature"`
8. Push and create merge request

### Common Commands
```bash
# Development commands
make install      # Install dependencies
make test         # Run tests
make lint         # Run linting
make format       # Format code
make docs         # Build documentation
make clean        # Clean build artifacts

# Create Makefile with these commands
cat > Makefile << 'EOF'
.PHONY: install test lint format docs clean

install:
	pip install -e ".[dev,docs,test]"

test:
	pytest

test-cov:
	pytest --cov=src/agentic_workflow --cov-report=html

lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

docs:
	cd docs && make html

docs-serve:
	mkdocs serve

clean:
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/

dev-setup: install
	pre-commit install
	docker-compose -f docker-compose.dev.yml up -d

dev-down:
	docker-compose -f docker-compose.dev.yml down
EOF
```

## 10. Verification Checklist

- [ ] Python 3.11+ installed and configured
- [ ] Virtual environment created and activated
- [ ] Project structure created correctly
- [ ] Dependencies installed successfully
- [ ] Code quality tools configured and passing
- [ ] Pre-commit hooks installed and working
- [ ] Tests running successfully
- [ ] CI/CD pipeline configured
- [ ] Documentation framework setup
- [ ] Docker configuration working
- [ ] Development services running
- [ ] All quality checks passing

## Next Steps

After completing this setup:

1. **Proceed to Task 1.2**: Core System Architecture
2. **Begin implementing**: Basic FastAPI application structure
3. **Setup monitoring**: Add basic health checks and logging
4. **Create first tests**: Implement basic test cases for core functionality

This completes the Python development environment setup. The environment is now ready for team collaboration and development of the agentic workflow system. 