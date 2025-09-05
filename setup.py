#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Script d'installation et de compilation
Configuration pour l'installation et la création d'exécutables

Auteur: L'OréalGPT
Version: 2.0.2
"""

import sys
import os
import shutil
from pathlib import Path
from setuptools import setup, find_packages
import subprocess

# ... (les informations sur le projet restent les mêmes) ...
PROJECT_NAME = "pdf-layout-translator"
VERSION = "2.0.2"
DESCRIPTION = "Application de traduction de documents PDF avec préservation de la mise en page"
AUTHOR = "L'OréalGPT"
URL = "https://github.com/loreal/pdf-layout-translator"

# --- MODIFICATION DES DÉPENDANCES ---
INSTALL_REQUIRES = [
    # PDF Processing
    "PyMuPDF>=1.23.14",
    "reportlab>=4.0.7",
    
    # Font Management
    "fonttools>=4.47.0",
    "pillow>=10.1.0",
    
    # Text Processing & Data
    "regex>=2023.10.3",
    
    # NOUVELLES DÉPENDANCES POUR LA TRADUCTION AUTOMATIQUE
    "lxml>=4.9.3",
    "googletrans==4.0.0-rc1", # Version spécifique requise
]

DEV_REQUIRES = [
    "pytest>=7.4.3",
    "flake8>=6.1.0",
    "pyinstaller>=6.3.0",
]

# ... (Le reste du fichier setup.py reste identique à celui que vous aviez, 
# je le remets ici pour que vous ayez le fichier complet et à jour)

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Office/Business",
    "Topic :: Text Processing",
]

ENTRY_POINTS = {
    "gui_scripts": [
        "pdf-layout-translator=src.main:main",
    ],
}

# Fonction pour récupérer la version (peut être simplifiée si non utilisée)
def get_version():
    version_file = Path("src") / "__version__.py"
    if version_file.exists():
        with open(version_file, 'r') as f:
            exec(f.read())
            return locals().get('__version__', VERSION)
    return VERSION

# Lancement du setup
setup(
    name=PROJECT_NAME,
    version=get_version(),
    description=DESCRIPTION,
    author=AUTHOR,
    url=URL,
    packages=find_packages(include=["src", "src.*"]),
    package_dir={"": "."},
    python_requires=">=3.8",
    install_requires=INSTALL_REQUIRES,
    extras_require={
        "dev": DEV_REQUIRES,
    },
    entry_points=ENTRY_POINTS,
    classifiers=CLASSIFIERS,
    zip_safe=False,
    include_package_data=True,
)
