#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Modèle de Données
Définit la structure des objets utilisés pour représenter une page PDF.

Auteur: L'OréalGPT
Version: 2.0.5 (Correction des imports de typing)
"""

from dataclasses import dataclass, field
# CORRECTION : Ajout de l'import manquant
from typing import List, Tuple

@dataclass
class FontInfo:
    """Représente les attributs de style d'un segment de texte."""
    name: str
    size: float
    color: str
    is_bold: bool
    is_italic: bool

@dataclass
class TextSpan:
    """Représente un segment de texte continu avec un style unique."""
    id: str
    text: str
    font: FontInfo
    bbox: Tuple[float, float, float, float]
    translated_text: str = ""

@dataclass
class TextBlock:
    """Représente un bloc de texte qui peut contenir plusieurs styles."""
    id: str
    bbox: Tuple[float, float, float, float]
    final_bbox: Tuple[float, float, float, float] = None
    spans: List[TextSpan] = field(default_factory=list)

@dataclass
class ImageBlock:
    """Représente une image sur la page."""
    id: str
    bbox: Tuple[float, float, float, float]
    data: bytes

@dataclass
class PageObject:
    """Représente la structure complète d'une seule page."""
    page_number: int
    dimensions: Tuple[float, float]
    text_blocks: List[TextBlock] = field(default_factory=list)
    image_blocks: List[ImageBlock] = field(default_factory=list)
