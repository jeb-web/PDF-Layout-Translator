#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de polices
Gestion des polices, détection, remplacement et installation

Auteur: L'OréalGPT
Version: 1.0.1 (Correction de la recherche de police)
"""

import os
import logging
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from fontTools.ttLib import TTFont, TTLibError
import json

if platform.system() == "Windows":
    import winreg

@dataclass
class FontStyle:
    path: Path
    
@dataclass
class FontFamily:
    name: str
    styles: Dict[str, FontStyle] = field(default_factory=dict)

@dataclass
class FontMapping:
    original_font: str
    replacement_font_name: str

class FontManager:
    def __init__(self, app_data_dir: Path):
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = app_data_dir
        self.font_mappings_file = self.app_data_dir / "config" / "font_mappings.json"
        
        self.font_families: Dict[str, FontFamily] = {}
        # NOUVEAU : Dictionnaire de recherche directe pour la performance et la fiabilité
        self.full_name_to_path: Dict[str, Path] = {}
        self.font_mappings: Dict[str, FontMapping] = {}
        self._scanned_files = set()
        
        self._scan_system_fonts()
        self._load_font_mappings()
        
        self.logger.info(f"FontManager initialisé: {len(self.font_families)} familles, {len(self.full_name_to_path)} styles de polices trouvés.")

    def _scan_system_fonts(self):
        if platform.system() == "Windows":
            self._scan_fonts_from_registry()
        self._scan_fonts_from_folders()

    def _scan_fonts_from_registry(self):
        font_dir = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts'
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
                i = 0
                while True:
                    try:
                        _, file_name, _ = winreg.EnumValue(key, i)
                        font_path = Path(file_name) if Path(file_name).is_absolute() else font_dir / file_name
                        if font_path.exists() and font_path not in self._scanned_files:
                            self._process_font_file(font_path)
                            self._scanned_files.add(font_path)
                        i += 1
                    except OSError: break
        except Exception as e:
            self.logger.error(f"Erreur d'accès au registre: {e}")

    def _scan_fonts_from_folders(self):
        font_extensions = {'.ttf', '.otf', '.ttc'}
        for font_dir in self._get_system_font_directories():
            for font_file in font_dir.rglob('*'):
                if font_file.suffix.lower() in font_extensions and font_file not in self._scanned_files:
                    self._process_font_file(font_file)
                    self._scanned_files.add(font_file)

    def _get_system_font_directories(self) -> List[Path]:
        dirs = []
        if platform.system() == 'Windows':
            dirs.extend([Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts', 
                         Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Windows' / 'Fonts'])
        elif platform.system() == 'darwin':
            dirs.extend([Path('/System/Library/Fonts'), Path('/Library/Fonts'), Path.home() / 'Library' / 'Fonts'])
        else:
            dirs.extend([Path('/usr/share/fonts'), Path('/usr/local/share/fonts'), Path.home() / '.fonts'])
        return [d for d in dirs if d.exists()]

    def _process_font_file(self, font_path: Path):
        try:
            font_collection = TTFont(font_path, lazy=True)
            if hasattr(font_collection, 'reader') and 'ttc' in font_collection.reader.file.name.lower():
                for i in range(len(font_collection.reader.fonts)):
                    font = TTFont(font_path, fontNumber=i, lazy=True)
                    self._add_font_from_metadata(font, font_path)
            else:
                self._add_font_from_metadata(font_collection, font_path)
        except (TTLibError, Exception): pass

    def _add_font_from_metadata(self, font: TTFont, font_path: Path):
        name_table = font['name']
        family_name, style_name = None, None
        for record in name_table.names:
            if record.nameID == 1: family_name = record.toUnicode()
            elif record.nameID == 2: style_name = record.toUnicode()
        if family_name and style_name:
            if family_name not in self.font_families:
                self.font_families[family_name] = FontFamily(name=family_name)
            self.font_families[family_name].styles[style_name] = FontStyle(path=font_path)
            
            # NOUVEAU : Remplir le dictionnaire de recherche directe
            full_name = f"{family_name} {style_name}"
            self.full_name_to_path[full_name] = font_path

    def get_all_available_fonts(self) -> List[str]:
        # MODIFIÉ : Utiliser les clés du dictionnaire direct pour garantir la cohérence
        return sorted(list(self.full_name_to_path.keys()))

    def check_fonts_availability(self, required_fonts: List[str]) -> Dict[str, Any]:
        available_fonts_list = self.get_all_available_fonts()
        available_fonts_lower = {name.lower() for name in available_fonts_list}
        missing_fonts = set()
        for font_name in set(required_fonts):
            if font_name.lower() not in available_fonts_lower:
                missing_fonts.add(font_name)
        suggestions = {font: self._suggest_alternatives(font) for font in missing_fonts}
        return {'missing_fonts': list(missing_fonts), 'suggestions': suggestions, 'all_available': not missing_fonts}

    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        # La logique de suggestion peut être améliorée, mais pour l'instant, c'est suffisant
        return [{'font_name': "Arial Regular"}]
        
    def create_font_mapping(self, original_font: str, replacement_font_name: str):
        self.font_mappings[original_font] = FontMapping(original_font, replacement_font_name)
        self._save_font_mappings()

    # --- MÉTHODE ENTIÈREMENT RÉÉCRITE POUR ÊTRE PLUS FIABLE ---
    def get_replacement_font_path(self, original_font_name: str) -> Optional[Path]:
        """
        Trouve le chemin vers le fichier de police de remplacement avec une logique de fallback.
        """
        # Priorité 1: Le choix exact de l'utilisateur
        mapping = self.font_mappings.get(original_font_name)
        if mapping:
            replacement_name = mapping.replacement_font_name
            # Utiliser notre dictionnaire de recherche directe
            path = self.full_name_to_path.get(replacement_name)
            if path:
                self.logger.info(f"Mapping utilisateur appliqué : '{original_font_name}' -> '{replacement_name}'")
                return path
            else:
                self.logger.warning(f"Le mapping pour '{original_font_name}' pointe vers une police inconnue : '{replacement_name}'")

        # Priorité 2: Suggestion intelligente (fallback si aucun mapping n'est défini ou valide)
        style_hints = self._get_style_hints(original_font_name)
        common_families = ["Arial", "Calibri", "Times New Roman", "Verdana"]
        for family in common_families:
            path = self._find_best_style_in_family(family, style_hints)
            if path:
                self.logger.info(f"Fallback intelligent pour '{original_font_name}' -> police de la famille '{family}'")
                return path
        
        # Ultime recours : la première police disponible
        if self.full_name_to_path:
            fallback_path = next(iter(self.full_name_to_path.values()))
            self.logger.warning(f"Aucune police de remplacement trouvée pour '{original_font_name}'. Utilisation de l'ultime recours : {fallback_path.name}")
            return fallback_path
            
        self.logger.error(f"Aucune police de remplacement trouvée pour '{original_font_name}' et aucune police système n'est disponible.")
        return None

    def _find_best_style_in_family(self, family_name: str, style_hints: List[str]) -> Optional[Path]:
        """Cherche le meilleur style correspondant dans une famille donnée."""
        if family_name in self.font_families:
            family_styles = self.font_families[family_name].styles
            
            # Tenter de trouver une correspondance
            for style_name, style_obj in family_styles.items():
                style_lower = style_name.lower()
                if all(hint in style_lower for hint in style_hints):
                    return style_obj.path
                    
            # Si aucun style ne correspond, prendre "Regular" ou le premier disponible
            if "Regular" in family_styles:
                return family_styles["Regular"].path
            elif family_styles:
                return next(iter(family_styles.values())).path
        return None

    def _get_style_hints(self, font_name: str) -> List[str]:
        """Extrait des indices de style (bold, italic) du nom de la police."""
        hints = []
        name_lower = font_name.lower()
        if 'bold' in name_lower: hints.append('bold')
        if 'italic' in name_lower or 'oblique' in name_lower: hints.append('italic')
        if not hints:
            hints.append('regular') # Indice par défaut
        return hints

    # --- Les fonctions suivantes sont inchangées ---

    def _load_font_mappings(self):
        if self.font_mappings_file.exists():
            try:
                with open(self.font_mappings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for original, mapping_data in data.items():
                        self.font_mappings[original] = FontMapping(
                            original_font=mapping_data['original_font'],
                            replacement_font_name=mapping_data['replacement_font_name']
                        )
            except Exception as e:
                self.logger.warning(f"Impossible de charger les mappings de police: {e}")

    def _save_font_mappings(self):
        self.font_mappings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.font_mappings_file, 'w', encoding='utf-8') as f:
                # S'assurer que les données sont sérialisables en JSON
                serializable_data = {
                    key: value.__dict__ for key, value in self.font_mappings.items()
                }
                json.dump(serializable_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Impossible de sauvegarder les mappings de police: {e}")
