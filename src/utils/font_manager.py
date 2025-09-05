#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de polices
Gestion des polices, détection, remplacement et installation

Auteur: L'OréalGPT
Version: 1.0.3 (Logique 1 pour 1 propre)
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
        self.full_name_to_path: Dict[str, Path] = {}
        self.font_mappings: Dict[str, FontMapping] = {}
        self._scanned_files = set()
        
        self._scan_system_fonts()
        self._load_font_mappings()
        
        self.logger.info(f"FontManager initialisé: {len(self.full_name_to_path)} styles de polices trouvés.")

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
            full_name = f"{family_name} {style_name}"
            self.full_name_to_path[full_name] = font_path

    def get_all_available_fonts(self) -> List[str]:
        return sorted(list(self.full_name_to_path.keys()))

    def check_fonts_availability(self, required_fonts: List[str]) -> Dict[str, Any]:
        # Comparaison simple et directe
        available_fonts_set = {name.lower().replace(" ", "").replace("-", "") for name in self.get_all_available_fonts()}
        missing_fonts = set()
        for font_name in set(required_fonts):
            clean_name = font_name.lower().replace(" ", "").replace("-", "")
            if clean_name not in available_fonts_set:
                missing_fonts.add(font_name)
        suggestions = {font: self._suggest_alternatives(font) for font in missing_fonts}
        return {'missing_fonts': list(missing_fonts), 'suggestions': suggestions, 'all_available': not missing_fonts}

    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        # Logique de suggestion simple, pourrait être améliorée
        if "Arial Regular" in self.full_name_to_path:
            return [{'font_name': "Arial Regular"}]
        return [{'font_name': "Helvetica"}] # Fallback ultime
        
    def create_font_mapping(self, original_font: str, replacement_font_name: str):
        self.font_mappings[original_font] = FontMapping(original_font, replacement_font_name)
        self._save_font_mappings()

    def get_replacement_font_path(self, original_font_name: str) -> Optional[Path]:
        """
        Trouve le chemin vers le fichier de police de remplacement avec une logique de fallback.
        Logique 1 pour 1 simple.
        """
        # Priorité 1: Le choix exact de l'utilisateur
        mapping = self.font_mappings.get(original_font_name)
        if mapping:
            replacement_name = mapping.replacement_font_name
            path = self.full_name_to_path.get(replacement_name)
            if path:
                self.logger.info(f"Mapping 1 pour 1 appliqué : '{original_font_name}' -> '{replacement_name}'")
                return path
            else:
                self.logger.warning(f"Le mapping pour '{original_font_name}' pointe vers une police inconnue : '{replacement_name}'. Passage au fallback.")

        # Priorité 2: Fallback (Arial si possible, sinon n'importe quelle police)
        if "Arial Regular" in self.full_name_to_path:
             return self.full_name_to_path["Arial Regular"]
        
        if self.full_name_to_path:
            fallback_path = next(iter(self.full_name_to_path.values()))
            self.logger.warning(f"Aucune police de remplacement trouvée pour '{original_font_name}'. Utilisation de l'ultime recours : {fallback_path.name}")
            return fallback_path
            
        self.logger.error(f"Aucune police de remplacement trouvée pour '{original_font_name}' et aucune police système n'est disponible.")
        return None

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
                serializable_data = {
                    key: value.__dict__ for key, value in self.font_mappings.items()
                }
                json.dump(serializable_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Impossible de sauvegarder les mappings de police: {e}")
