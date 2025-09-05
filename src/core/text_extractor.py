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
                    self.debug_logger.info(f"  - Bloc {block.id}: Texte extrait avec {len(sorted_lines_text)} sauts de ligne.")
                    
                    # --- CORRECTION DE LA SYNTAXERROR ---
                    # On ne peut pas utiliser de backslash dans une expression f-string.
                    # On remplace donc \n par un marqueur visu
