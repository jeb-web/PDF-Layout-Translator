#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

# Dépendances de production (le strict minimum pour que l'application fonctionne)
INSTALL_REQUIRES = [
    "PyMuPDF>=1.23.14",
    "fonttools>=4.47.0",
    "lxml>=4.9.3",
    "googletrans==4.0.0-rc1",
    # CORRECTION : Dépendances critiques restaurées
    "reportlab>=4.0.7",
    "Pillow>=10.1.0",
]

# Dépendances de développement (outils pour le développeur)
DEV_REQUIRES = [
    "pytest>=7.4.3",
    "flake8>=6.1.0",
    "pyinstaller>=6.3.0",
]

setup(
    name="pdf-layout-translator",
    version="2.1.0",
    description="Application de traduction de PDF avec préservation de la mise en page.",
    author="L'OréalGPT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=INSTALL_REQUIRES,
    extras_require={"dev": DEV_REQUIRES},
    entry_points={"gui_scripts": ["pdf-layout-translator=src.main:main"]},
)
