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

        self.debug_logger.info("--- Début de la Traduction Automatique ---")
        self.debug_logger.info(f"Langue cible demandée : '{target_lang}'")
        
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(xliff_content.encode('utf-8'), parser)
        
        ns = {'xliff': 'urn:oasis:names:tc:xliff:document:1.2'}
        trans_units = root.xpath("//xliff:trans-unit", namespaces=ns)
        total_units = len(trans_units)
        self.debug_logger.info(f"Nombre total de segments à traduire trouvés : {total_units}")
        
        translated_count, failed_count = 0, 0
        for i, unit in enumerate(trans_units):
            source = unit.find("xliff:source", namespaces=ns)
            target = unit.find("xliff:target", namespaces=ns)
            
            if source is not None and source.text and source.text.strip():
                source_text = source.text
                self.debug_logger.info(f"  > Traitement {i+1}/{total_units} (ID: {unit.get('id')}): '{source_text[:70]}...'")
                translated_text = "" # Initialisation
                try:
                    # Pause pour éviter le blocage de l'API
                    if i > 0 and i % 15 == 0:
                        self.debug_logger.info("    ... Pause de 0.5s pour éviter le blocage de l'API...")
                        sleep(0.5)
                    
                    # --- BLOC DE FIABILISATION ---
                    translation_result = self.translator.translate(source_text, dest=target_lang)
                    
                    # Vérification cruciale : la bibliothèque peut renvoyer None
                    if translation_result and translation_result.text:
                        translated_text = translation_result.text
                        translated_count += 1
                        self.debug_logger.info(f"    Succès -> '{translated_text[:70]}...'")
                    else:
                        # Si la traduction échoue silencieusement, on conserve le texte source.
                        self.logger.warning(f"Traduction vide retournée pour '{source_text[:30]}...'. Texte source conservé.")
                        self.debug_logger.warning(f"    Échec ! Résultat de traduction vide. Conservation du texte source.")
                        translated_text = source_text
                        failed_count += 1
                    # --- FIN DU BLOC ---

                except Exception as e:
                    self.logger.warning(f"Échec traduction pour '{source_text[:30]}...': {e}. Texte source conservé.")
                    self.debug_logger.warning(f"    Échec ! Erreur: {e}. Conservation du texte source.")
                    translated_text = source_text # Assurer que la variable a toujours une valeur
                    failed_count += 1
                
                # S'assurer que la cible existe avant d'écrire
                if target is None:
                    target = etree.SubElement(unit, "target")
                target.text = translated_text

            elif target is None:
                # Créer une balise target vide si elle n'existe pas, même pour une source vide
                etree.SubElement(unit, "target")

        self.debug_logger.info("--- Fin de la Traduction Automatique ---")
        self.debug_logger.info(f"Résumé : {translated_count} segments traduits, {failed_count} échecs.")
        return etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True).decode('utf-8')
