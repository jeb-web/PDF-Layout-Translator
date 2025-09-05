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

    def create_xliff(self, pages: List[PageObject], source_lang: str, target_lang: str) -> str:
        self.logger.info(f"Création du fichier XLIFF de '{source_lang}' vers '{target_lang}' (Mode Span Stable)")
        xliff = Element('xliff', attrib={'version': '1.2', 'xmlns': 'urn:oasis:names:tc:xliff:document:1.2'})
        file_elem = SubElement(xliff, 'file', attrib={'source-language': source_lang, 'target-language': target_lang, 'datatype': 'plaintext', 'original': 'pdf-document'})
        body = SubElement(file_elem, 'body')
        
        # --- RETOUR À LA LOGIQUE ORIGINALE ET STABLE ---
        # On traite chaque span individuellement. C'est moins élégant, mais c'est fiable.
        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    if span.text and span.text.strip():
                        trans_unit = SubElement(body, 'trans-unit', attrib={'id': span.id})
                        source = SubElement(trans_unit, 'source')
                        source.text = span.text
                        SubElement(trans_unit, 'target')
        
        xml_str = tostring(xliff, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        # Cette fonction retourne TOUJOURS une chaîne de caractères.
        return parsed_str.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
