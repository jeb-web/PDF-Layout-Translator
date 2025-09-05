#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Extracteur de texte pour traduction
Génère un fichier XLIFF à partir du DOM de la page.

Auteur: L'OréalGPT
Version: 2.0.1 (Correction de syntaxe)
"""
import logging
from typing import List
from xml.etree.ElementTree import Element, SubElement, ElementTree, tostring
from xml.dom import minidom
from .data_model import PageObject

class TextExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_xliff(self, pages: List[PageObject], source_lang: str, target_lang: str) -> str:
        """Crée une chaîne de caractères au format XLIFF 1.2."""
        self.logger.info(f"Création du fichier XLIFF de '{source_lang}' vers '{target_lang}'")

        xliff = Element('xliff', attrib={'version': '1.2'})
        file_elem = SubElement(xliff, 'file', attrib={
            'source-language': source_lang,
            'target-language': target_lang,
            'datatype': 'plaintext',
            'original': 'pdf-document'
        })
        body = SubElement(file_elem, 'body')

        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    # N'extraire que les spans qui contiennent du texte visible
                    if span.text and span.text.strip():
                        trans_unit = SubElement(body, 'trans-unit', attrib={'id': span.id})
                        source = SubElement(trans_unit, 'source')
                        source.text = span.text
                        target = SubElement(trans_unit, 'target') # Laisser la cible vide
        
        # Pretty print de la sortie XML
        xml_str = tostring(xliff, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        # CORRECTION: Suppression des caractères parasites à la fin de la ligne
        return parsed_str.toprettyxml(indent="  ", encoding="utf-8").decode('utf-8')
