# Configuration file for the Sphinx documentation builder.

import os
import sys
from datetime import datetime

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -------

project = 'QC Matrix Generator'
copyright = f'{datetime.now().year}, QC Team'
author = 'QC Team'
release = '1.0.0'
version = '1.0'

# -- General configuration -----

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- HTML output -------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_nav_header_background': '#2980B9',
}

# -- Autodoc options ---

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': False,
    'show-inheritance': True,
}

# -- Napoleon settings ---

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = True

# -- Language ------

language = 'es'
