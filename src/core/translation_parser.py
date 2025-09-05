#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Parseur de traductions
Parse le fichier XLIFF retourné par l'utilisateur.
"""
import logging
from typing import Dict
from xml.etree import ElementTree

class TranslationParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_xliff(self, xliff_content: str) -> Dict[str, str]:
        self.logger.info("Parsing du fichier XLIFF traduit.")
        translations = {}
        try:
            xliff_content = xliff_content.replace('xmlns="urn:oasis:names:tc:xliff:document:1.2"', '')
            root = ElementTree.fromstring(xliff_content)
            for trans_unit in root.findall(".//trans-unit"):
                unit_id = trans_unit.get('id')
                target = trans_unit.find('target')
                if unit_id and target is not None:
                    translations[unit_id] = target.text.strip() if target.text else ""
        except ElementTree.ParseError as e:
            self.logger.error(f"Erreur de parsing XLIFF: {e}")
            raise ValueError("Le contenu fourni n'est pas un XML XLIFF valide.")
        
        self.logger.info(f"{len(translations)} traductions parsées avec succès.")
        return translations
