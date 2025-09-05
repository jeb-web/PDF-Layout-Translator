#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Parseur de traductions
Parse le fichier XLIFF retourné par l'utilisateur.

Auteur: L'OréalGPT
Version: 2.0.2 (Correction du nom de la méthode et du parsing)
"""
import logging
from typing import Dict
from xml.etree import ElementTree

class TranslationParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # CORRECTION BUG N°3 : Le nom de la méthode est maintenant correct
    def parse_xliff(self, xliff_content: str) -> Dict[str, str]:
        """Parse le contenu XLIFF et retourne un dictionnaire de traductions."""
        self.logger.info("Parsing du fichier XLIFF traduit.")
        translations = {}
        try:
            # Remplacer le namespace par défaut pour une recherche plus simple et robuste
            # Cela évite les problèmes avec lxml vs ElementTree
            xliff_content = xliff_content.replace('xmlns="urn:oasis:names:tc:xliff:document:1.2"', '')
            root = ElementTree.fromstring(xliff_content)
            
            for trans_unit in root.findall(".//trans-unit"):
                unit_id = trans_unit.get('id')
                target = trans_unit.find('target')
                
                if unit_id and target is not None:
                    # Gérer le cas où la cible est vide (target.text is None)
                    translations[unit_id] = target.text.strip() if target.text else ""

        except ElementTree.ParseError as e:
            self.logger.error(f"Erreur de parsing XLIFF: {e}")
            raise ValueError("Le contenu fourni n'est pas un XML XLIFF valide.")
        
        self.logger.info(f"{len(translations)} traductions parsées avec succès.")
        return translations
