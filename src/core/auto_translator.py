#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Module de Traduction Automatique
Utilise des services externes pour traduire le contenu d'un fichier XLIFF.

Auteur: L'OréalGPT
Version: 2.0.1
"""

import logging
from lxml import etree
from time import sleep

# Essayer d'importer googletrans. Si l'import échoue, la fonctionnalité sera désactivée.
try:
    from googletrans import Translator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False

class AutoTranslator:
    """Encapsule la logique de traduction automatique."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if GOOGLETRANS_AVAILABLE:
            self.translator = Translator()
        else:
            self.translator = None

    def is_available(self) -> bool:
        """Vérifie si le service de traduction est disponible."""
        return GOOGLETRANS_AVAILABLE

    def translate_xliff_content(self, xliff_content: str, target_lang: str) -> str:
        """
        Traduit le contenu d'un fichier XLIFF en utilisant Google Translate.
        En cas d'erreur de traduction pour un segment, le texte source est conservé.
        """
        if not self.is_available():
            raise RuntimeError("La bibliothèque 'googletrans' n'est pas installée. La traduction automatique est désactivée.")

        self.logger.info(f"Début de la traduction automatique vers '{target_lang}'...")
        
        # lxml nécessite des bytes pour le parsing, donc on encode
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xliff_content.encode('utf-8'), parser)
        
        # Le namespace est crucial pour que lxml trouve les balises
        ns = {'xliff': 'urn:oasis:names:tc:xliff:document:1.2'}
        
        # Trouver toutes les unités de traduction
        trans_units = root.xpath("//xliff:trans-unit", namespaces=ns)
        total_units = len(trans_units)
        self.logger.info(f"{total_units} segments à traduire.")

        for i, unit in enumerate(trans_units):
            source = unit.find("xliff:source", namespaces=ns)
            target = unit.find("xliff:target", namespaces=ns)
            
            if source is not None and source.text and source.text.strip():
                try:
                    # Ajout d'une petite pause pour éviter de se faire bloquer par Google
                    if i > 0 and i % 10 == 0:
                        sleep(0.5)

                    translated_text = self.translator.translate(source.text, dest=target_lang).text
                    if target is None:
                        target = etree.SubElement(unit, "target")
                    target.text = translated_text
                except Exception as e:
                    self.logger.warning(f"Échec de la traduction pour le segment '{source.text[:30]}...': {e}. Le texte source sera conservé.")
                    # En cas d'erreur, on copie le texte source dans la cible
                    if target is None:
                        target = etree.SubElement(unit, "target")
                    target.text = source.text
            elif target is None:
                # S'il n'y a pas de source, créer une cible vide pour garder le fichier valide
                etree.SubElement(unit, "target")

        self.logger.info("Traduction automatique terminée.")
        # Re-convertir l'arbre lxml en une chaîne de caractères formatée
        return etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True).decode('utf-8')
