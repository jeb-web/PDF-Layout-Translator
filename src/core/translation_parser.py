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
        self.debug_logger = logging.getLogger('debug_trace')

    def parse_xliff(self, xliff_content: str) -> Dict[str, str]:
        self.debug_logger.info("="*50)
        self.debug_logger.info(" DÉBUT DU PARSING XLIFF (v1.1 - Mode Bloc) ")
        self.debug_logger.info("="*50)
        
        translations = {}
        try:
            # Nettoyage de namespace pour simplifier le parsing
            xliff_content = xliff_content.replace('xmlns="urn:oasis:names:tc:xliff:document:1.2"', '')
            root = ElementTree.fromstring(xliff_content)
            
            for trans_unit in root.findall(".//trans-unit"):
                unit_id = trans_unit.get('id')
                target = trans_unit.find('target')
                
                # Le texte peut être vide (None) ou une chaîne vide, on le gère.
                target_text = target.text if target is not None and target.text is not None else ""
                
                if unit_id:
                    translations[unit_id] = target_text
                    self.debug_logger.info(f"  - Traduction trouvée pour l'ID de bloc '{unit_id}'.")
                else:
                    self.debug_logger.warning("  - Unité de traduction sans ID trouvée. Elle sera ignorée.")
                    
        except ElementTree.ParseError as e:
            self.logger.error(f"Erreur de parsing XLIFF: {e}")
            self.debug_logger.error(f"ERREUR FATALE LORS DU PARSING XLIFF: {e}", exc_info=True)
            raise ValueError("Le contenu fourni n'est pas un XML XLIFF valide.")
        
        self.debug_logger.info(f"{len(translations)} traductions pour des blocs ont été parsées avec succès.")
        self.debug_logger.info("="*50); self.debug_logger.info(" FIN DU PARSING XLIFF "); self.debug_logger.info("="*50)
        return translations
