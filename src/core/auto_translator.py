#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Module de Traduction Automatique
Utilise des services externes pour traduire le contenu d'un fichier XLIFF.
"""
import logging
from lxml import etree
from time import sleep

try:
    from googletrans import Translator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False

class AutoTranslator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        if GOOGLETRANS_AVAILABLE:
            self.translator = Translator()
        else:
            self.translator = None

    def is_available(self) -> bool:
        return GOOGLETRANS_AVAILABLE

    def translate_xliff_content(self, xliff_content: str, target_lang: str) -> str:
        if not self.is_available():
            raise RuntimeError("La bibliothèque 'googletrans' n'est pas installée.")

        self.debug_logger.info("--- Début de la Traduction Automatique (Mode Fiable) ---")
        
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xliff_content.encode('utf-8'), parser)
        
        ns = {'xliff': 'urn:oasis:names:tc:xliff:document:1.2'}
        trans_units = root.xpath("//xliff:trans-unit", namespaces=ns)
        total_units = len(trans_units)
        
        translated_count, failed_count = 0, 0
        for i, unit in enumerate(trans_units):
            source = unit.find("xliff:source", namespaces=ns)
            target = unit.find("xliff:target", namespaces=ns)
            
            source_text = source.text if source is not None and source.text else ""
            
            if source_text.strip():
                translated_text = ""
                try:
                    if i > 0 and i % 15 == 0:
                        sleep(0.5)
                    
                    translation_result = self.translator.translate(source_text, dest=target_lang)
                    
                    if translation_result and translation_result.text:
                        translated_text = translation_result.text
                        translated_count += 1
                    else:
                        self.debug_logger.warning(f"  -> Traduction vide pour '{source_text[:30]}...'. Texte source conservé.")
                        translated_text = source_text
                        failed_count += 1

                except Exception as e:
                    self.debug_logger.warning(f"  -> Échec de traduction pour '{source_text[:30]}...': {e}. Texte source conservé.")
                    translated_text = source_text
                    failed_count += 1
                
                if target is None:
                    target = etree.SubElement(unit, "target")
                target.text = translated_text
            elif target is None:
                etree.SubElement(unit, "target")

        self.debug_logger.info(f"--- Fin de la boucle de Traduction: {translated_count} succès, {failed_count} échecs. ---")
        
        # --- BLINDAGE FINAL ---
        # Cette fonction NE DOIT JAMAIS retourner None.
        try:
            # On tente de convertir l'arbre XML modifié en chaîne de caractères.
            final_xliff = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True).decode('utf-8')
            self.debug_logger.info("  -> Conversion finale du XLIFF en chaîne de caractères réussie.")
            return final_xliff
        except Exception as e:
            # En cas d'échec critique, on retourne un XLIFF vide mais valide pour ne JAMAIS retourner None.
            self.logger.error(f"Erreur critique lors de la finalisation du XLIFF traduit: {e}")
            self.debug_logger.error(f"  -> ERREUR CRITIQUE lors de la conversion finale du XLIFF. Retour d'un XLIFF vide.", exc_info=True)
            return '<?xml version="1.0" encoding="UTF-8"?><xliff version="1.
