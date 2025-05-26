import os
import sys

sys.path.insert(0, os.path.abspath("../../"))  # Point to the project root

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Target Assistant Bot"
copyright = "2025, bivlked"
author = "bivlked"
release = "0.1.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # Include documentation from docstrings
    "sphinx.ext.napoleon",  # Support for Google and NumPy style docstrings
    "sphinx.ext.viewcode",  # Add links to source code
    "sphinx.ext.intersphinx",  # Link to other projects' documentation
    "sphinx_rtd_theme",  # Read the Docs theme
    "sphinx_autodoc_typehints",  # Better typehints in autodoc
    "myst_parser",  # For Markdown support
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]  # Exclude build directory

language = "ru"

# -- Options for autodoc -----------------------------------------------------
aputodoc_member_order = "bysource"  # Order members by source order

# -- Options for Napoleon (Google/NumPy docstrings) -------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = False  # Assuming Google style
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True

# -- Options for sphinx-autodoc-typehints -----------------------------------
always_document_param_types = True
typehints_fully_qualified = False

# -- Options for Intersphinx -----------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "telegram": ("https://docs.python-telegram-bot.org/en/stable/", None),
    "apscheduler": ("https://apscheduler.readthedocs.io/en/stable/", None),
    "structlog": ("https://www.structlog.org/en/stable/", None),
    # 'openai': ('https://platform.openai.com/docs/api-reference', None), # Temporarily commented out
    "gspread": ("https://docs.gspread.org/en/latest/", None),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_css_files = [
#    'css/custom.css',
# ]
