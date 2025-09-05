#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Extracteur de texte pour traduction
Génère un fichier XLIFF à partir du DOM de la page.
"""
import logging
from typing import List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from core.data_model import PageObject

class TextExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')

    def create_xliff(self, pages: List[PageObject], source_lang: str, target_lang: str) -> str:
        self.debug_logger.info("="*50)
        self.debug_logger.info(" DÉBUT DE L'EXTRACTION XLIFF (v1.1 - Mode Bloc) ")
        self.debug_logger.info("="*50)
        
        xliff = Element('xliff', attrib={'version': '1.2', 'xmlns': 'urn:oasis:names:tc:xliff:document:1.2'})
        file_elem = SubElement(xliff, 'file', attrib={'source-language': source_lang, 'target-language': target_lang, 'datatype': 'plaintext', 'original': 'pdf-document'})
        body = SubElement(file_elem, 'body')
        
        for page in pages:
            self.debug_logger.info(f"--- Page {page.page_number} ---")
            for block in page.text_blocks:
                # --- LOGIQUE v1.1 : RECONSTRUCTION DES LIGNES ET PARAGRAPHES ---
                # Nous reconstruisons les lignes visuelles du PDF pour préserver les sauts de ligne.
                lines = {}
                if not block.spans:
                    self.debug_logger.info(f"  - Bloc {block.id} ignoré (pas de spans).")
                    continue

                # Regrouper les spans par leur coordonnée verticale (y0) pour reformer les lignes
                for span in block.spans:
                    # Utiliser une clé y0 arrondie pour regrouper les spans qui sont "à peu près" sur la même ligne
                    line_key = round(span.bbox[1], 0) 
                    if line_key not in lines:
                        lines[line_key] = []
                    lines[line_key].append(span)
                
                # Trier les spans de chaque ligne par leur coordonnée horizontale (x0)
                sorted_lines_text = []
                for line_key in sorted(lines.keys()):
                    sorted_spans = sorted(lines[line_key], key=lambda s: s.bbox[0])
                    line_text = "".join([s.text for s in sorted_spans])
                    sorted_lines_text.append(line_text)
                
                # Joindre les lignes avec un \n pour former le texte complet du bloc
                block_text = "\n".join(sorted_lines_text)
                
                if block_text and block_text.strip():
                    self.debug_logger.info(f"  - Bloc {block.id}: Texte extrait avec {len(sorted_lines_text)} sauts de ligne.")
                    self.debug_logger.info(f"    -> \"{block_text.replace(chr(10), ' [\\n] ')[:80]}...\"")
                    # On crée UNE SEULE unité de traduction par BLOC, avec l'ID du bloc.
                    trans_unit = SubElement(body, 'trans-unit', attrib={'id': block.id})
                    source = SubElement(trans_unit, 'source')
                    source.text = block_text
                    SubElement(trans_unit, 'target')
        
        self.debug_logger.info("="*50)
        self.debug_logger.info(" FIN DE L'EXTRACTION XLIFF ")
        self.debug_logger.info("="*50)
        
        xml_str = tostring(xliff, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        return parsed_str.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
