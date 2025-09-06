#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Modèle de Données
Définit la structure des objets utilisés pour représenter une page PDF.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class FontInfo:
    name: str
    size: float
    color: str
    is_bold: bool
    is_italic: bool

@dataclass
class TextSpan:
    id: str
    text: str
    font: FontInfo
    bbox: Tuple[float, float, float, float]
    translated_text: str = ""
    # Le drapeau is_end_of_paragraph est maintenant géré par la structure ci-dessous.

# [JALON 1] Nouvelle structure pour représenter un paragraphe sémantique.
@dataclass
class Paragraph:
    id: str
    spans: List[TextSpan] = field(default_factory=list)

@dataclass
class TextBlock:
    id: str
    bbox: Tuple[float, float, float, float]
    # [JALON 1] Le TextBlock contient maintenant une liste de paragraphes.
    paragraphs: List[Paragraph] = field(default_factory=list)
    # [JALON 1] Nous gardons temporairement la liste plate de spans pour la compatibilité
    # avec les modules qui ne sont pas encore mis à jour.
    spans: List[TextSpan] = field(default_factory=list)
    alignment: int = 0  # L'alignement sera implémenté dans un jalon futur.
    final_bbox: Tuple[float, float, float, float] = None

@dataclass
class PageObject:
    page_number: int
    dimensions: Tuple[float, float]
    text_blocks: List[TextBlock] = field(default_factory=list)
