# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Path setup --------------------------------------------------------------

# Add the src directory so autodoc can find the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# -- Project information -----------------------------------------------------

project = "Microsoft OpenTelemetry Distro for Python"
copyright = "Microsoft Corporation"  # pylint: disable=redefined-builtin
author = "Microsoft"

# -- General configuration ---------------------------------------------------

# Easy automatic cross-references for `code in backticks`
default_role = "any"

extensions = [
    # API doc generation
    "sphinx.ext.autodoc",
    # Support for google-style docstrings
    "sphinx.ext.napoleon",
    # Infer types from hints instead of docstrings
    "sphinx_autodoc_typehints",
    # Add links to source from generated docs
    "sphinx.ext.viewcode",
    # Link to other sphinx docs
    "sphinx.ext.intersphinx",
    # Add a .nojekyll file for GitHub Pages
    "sphinx.ext.githubpages",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "opentelemetry": (
        "https://opentelemetry-python.readthedocs.io/en/latest/",
        None,
    ),
}

templates_path = ["_templates"]

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}

# Napoleon configuration
napoleon_use_ivar = True

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = []
