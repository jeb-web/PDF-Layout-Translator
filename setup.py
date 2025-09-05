#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Script d'installation et de compilation
Configuration pour l'installation et la création d'exécutables

Auteur: L'OréalGPT
Version: 2.0.2
"""

from pathlib import Path
from setuptools import setup, find_packages

# --- CONFIGURATION CENTRALE DU PROJET ---
PROJECT_NAME = "pdf-layout-translator"
VERSION = "2.0.2"
DESCRIPTION = "Application de traduction de documents PDF avec préservation de la mise en page via une architecture DOM."
AUTHOR = "L'OréalGPT"
URL = "https://github.com/loreal/pdf-layout-translator"

# Dépendances de production (le strict minimum pour que l'application fonctionne)
INSTALL_REQUIRES = [
    "PyMuPDF>=1.23.14",
    "reportlab>=4.0.7",
    "fonttools>=4.47.0",
    "pillow>=10.1.0",
    "regex>=2023.10.3",
    "lxml>=4.9.3",
    "googletrans==4.0.0-rc1", # Version spécifique requise pour la traduction auto
]

# Dépendances de développement (outils pour le développeur)
DEV_REQUIRES = [
    "pytest>=7.4.3",
    "flake8>=6.1.0",
    "pyinstaller>=6.3.0",
]

# --- SETUP SCRIPT ---
setup(
    name=PROJECT_NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    url=URL,
    # Trouve automatiquement tous les packages dans le dossier 'src'
    packages=find_packages(where="."),
    package_dir={"": "."},
    # L'application ne fonctionnera qu'avec Python 3.8 ou supérieur
    python_requires=">=3.8",
    # Listes de dépendances
    install_requires=INSTALL_REQUIRES,
    extras_require={
        "dev": DEV_REQUIRES,
    },
    # Point d'entrée pour lancer l'application graphique
    entry_points={
        "gui_scripts": [
            "pdf-layout-translator=src.main:main",
        ],
    },
    # Classifications pour le catalogue PyPI
    classifiers=[
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
    ],
    zip_safe=False,
    include_package_data=True,
)
