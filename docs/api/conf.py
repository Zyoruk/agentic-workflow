import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

project = 'Agentic Workflow'
copyright = '2024, Zyoruk'
author = 'Zyoruk'
release = '0.3.0'

# GitHub repository configuration
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'both',
    'style_external_links': True,
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': True,
    'sticky_navigation': True,
    'includehidden': True,
}

# GitHub pages configuration
html_baseurl = 'https://zyoruk.github.io/agentic-workflow/'
html_show_sourcelink = True
html_context = {
    'display_github': True,
    'github_user': 'zyoruk',
    'github_repo': 'agentic-workflow',
    'github_banner': True,
    'github_button': True,
    'github_type': 'star',
    'github_count': True,
    'github_ribbon': 'fork',
}

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
    'sphinx.ext.githubpages',
]

# Docstring processing
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
    'inherited-members': True,
}

# Intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'fastapi': ('https://fastapi.tiangolo.com/', None),
    'langchain': ('https://api.python.langchain.com/en/latest/', None),
}

# Docstring processing settings
docstring_processor = 'sphinx.ext.napoleon'
docstring_processor_options = {
    'napoleon_google_docstring': True,
    'napoleon_numpy_docstring': False,
    'napoleon_include_init_with_doc': True,
    'napoleon_include_private_with_doc': True,
    'napoleon_include_special_with_doc': True,
    'napoleon_use_admonition_for_examples': True,
    'napoleon_use_admonition_for_notes': True,
    'napoleon_use_admonition_for_references': True,
    'napoleon_use_ivar': True,
    'napoleon_use_param': True,
    'napoleon_use_rtype': True,
}

# Cross-reference settings
default_role = 'py:obj'
nitpicky = True
nitpick_ignore = [
    ('py:class', 'ValidationError'),
    ('py:class', 'agentic_workflow.ValidationError'),
    ('py:class', 'agentic_workflow.core.exceptions.ValidationError'),
    ('py:class', 'agentic_workflow.guardrails.ValidationError'),
    ('py:class', 'agentic_workflow.guardrails.input_validation.ValidationError'),
]

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = True
autosummary_mock_imports = ['langchain', 'fastapi']
