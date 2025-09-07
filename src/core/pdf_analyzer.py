#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
*** VERSION FINALE ET STABILISÉE v1.7.1 - CORRECTIF UNIFICATION ROBUSTE ***
"""
import logging
import re
from pathlib import Path
from typing import List, Tuple
import fitz
import copy
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo, Paragraph

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')

    def _normalize_font_name(self, font_name: str) -> str:
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    # --- NOUVEAU v2.5.1 ---
    # Méthode helper pour décider si deux blocs doivent être fusionnés (version robustifiée)
    def _should_merge(self, block_a: TextBlock, block_b: TextBlock) -> Tuple[bool, str]:
        # Vérification de robustesse : s'assurer que les blocs et leurs paragraphes/spans ne sont pas vides
        if not all([
            block_a.paragraphs,
            block_a.paragraphs[-1].spans,
            block_b.paragraphs,
            block_b.paragraphs[0].spans
        ]):
            return False, "Bloc ou paragraphe vide, fusion impossible"
            
        last_span_a = block_a.paragraphs[-1].spans[-1]
        first_span_b = block_b.paragraphs[0].spans[0]

        # Règle 1: Proximité Verticale
        vertical_gap = block_b.bbox[1] - block_a.bbox[3]
        line_height_threshold = last_span_a.font.size * 1.5
        if vertical_gap >= line_height_threshold:
            return False, f"Écart vertical trop grand ({vertical_gap:.1f} >= {line_height_threshold:.1f})"

        # Règle 2: Alignement Horizontal (assouplie)
        horizontal_gap = abs(last_span_a.bbox[0] - first_span_b.bbox[0])
        if horizontal_gap > 10:
            return False, f"Désalignement horizontal significatif ({horizontal_gap:.1f} > 10)"

        # Règle 3: Cohérence Stylistique (assouplie)
        style_a = last_span_a.font
        style_b = first_span_b.font
        font_name_a = style_a.name.split('-')[0]
        font_name_b = style_b.name.split('-')[0]
        if font_name_a != font_name_b:
            return False, f"Changement de police ({style_a.name} -> {style_b.name})"
        if abs(style_a.size - style_b.size) > 0.5:
            return False, f"Changement de taille ({style_a.size:.1f} -> {style_b.size:.1f})"
            
        return True, "Règles de fusion respectées"

    # --- NOUVEAU v2.5 ---
    # Méthode principale pour l'unification des blocs
    def _unify_text_blocks(self, blocks: List[TextBlock]) -> List[TextBlock]:
        if not blocks:
            return []

        self.debug_logger.info("    > Démarrage de la phase d'unification des blocs...")
        unified_blocks = []
        
        current_block = copy.deepcopy(blocks[0])

        for next_block in blocks[1:]:
            should_merge, reason = self._should_merge(current_block, next_block)
            
            if should_merge:
                current_block.paragraphs.extend(next_block.paragraphs)
                new_bbox = (
                    min(current_block.bbox[0], next_block.bbox[0]),
                    min(current_block.bbox[1], next_block.bbox[1]),
                    max(current_block.bbox[2], next_block.bbox[2]),
                    max(current_block.bbox[3], next_block.bbox[3])
                )
                current_block.bbox = new_bbox
                self.debug_logger.info(f"      - Fusion du bloc {next_block.id} dans {current_block.id}. Raison: {reason}")
            else:
                self.debug_logger.info(f"      - Finalisation du bloc unifié {current_block.id}. Raison de la rupture: {reason}")
                unified_blocks.append(current_block)
                current_block = copy.deepcopy(next_block)
        
        unified_blocks.append(current_block)
        self.debug_logger.info(f"    > Unification terminée. Nombre de blocs: {len(blocks)} -> {len(unified_blocks)}")
        return unified_blocks

    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
        # ... (Le reste de la fonction analyze_pdf reste identique à la version précédente)
        # ... (J'omets le copier-coller pour la lisibilité, mais il est inchangé)
