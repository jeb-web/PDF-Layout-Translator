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
        self.debug_logger.info(" DÉBUT DE L'EXTRACTION XLIFF (v1.1 - Mode Bloc Corrigé) ")
        self.debug_logger.info("="*50)
        
        xliff = Element('xliff', attrib={'version': '1.2', 'xmlns': 'urn:oasis:names:tc:xliff:document:1.2'})
        file_elem = SubElement(xliff, 'file', attrib={'source-language': source_lang, 'target-language': target_lang, 'datatype': 'plaintext', 'original': 'pdf-document'})
        body = SubElement(file_elem, 'body')
        
        for page in pages:
            self.debug_logger.info(f"--- Page {page.page_number} ---")
            for block in page.text_blocks:
                lines = {}
                if not block.spans:
                    self.debug_logger.info(f"  - Bloc {block.id} ignoré (pas de spans).")
                    continue

                for span in block.spans:
                    line_key = round(span.bbox[1], 0) 
                    if line_key not in lines:
                        lines[line_key] = []
                    lines[line_key].append(span)
                
                sorted_lines_text = []
                for line_key in sorted(lines.keys()):
                    sorted_spans = sorted(lines[line_key], key=lambda s: s.bbox[0])
                    line_text = "".join([s.text for s in sorted_spans])
                    sorted_lines_text.append(line_text)
                
                block_text = "\n".join(sorted_lines_text)
                
                if block_text and block_text.strip():
                    log_friendly_text = block_text.replace('\n', ' [NL] ')
                    
                    # --- LA CORRECTION FINALE ET DÉFINITIVE ---
                    # L'ID de l'unité de traduction DOIT être l'ID du BLOC, pas du span.
                    unit_id = block.id
                    # -------------------------------------------

                    self.debug_logger.info(f"  - Bloc {unit_id}: Texte extrait avec {len(sorted_lines_text)} sauts de ligne.")
                    self.debug_logger.info(f"    -> \"{log_friendly_text[:80]}...\"")
                    
                    trans_unit = SubElement(body, 'trans-unit', attrib={'id': unit_id})
                    source = SubElement(trans_unit, 'source')
                    source.text = block_text
                    SubElement(trans_unit, 'target')
        
        self.debug_logger.info("="*50)
        self.debug_logger.info(" FIN DE L'EXTRACTION XLIFF ")
        self.debug_logger.info("="*50)
        
        xml_str = tostring(xliff, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        return parsed_str.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
