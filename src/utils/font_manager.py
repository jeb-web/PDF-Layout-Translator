#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de polices
*** VERSION CORRIGÉE - Logique de mapping simple et robuste ***
"""
import os
import logging
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from fontTools.ttLib import TTFont, TTLibError

if platform.system() == "Windows":
    import winreg

class FontManager:
    def __init__(self, app_data_dir: Path):
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = app_data_dir
        self.font_mappings_file = self.app_data_dir / "config" / "font_mappings.json"
        
        self.system_fonts: Dict[str, Path] = {}
        self.font_mappings: Dict[str, str] = {} # Dictionnaire simple: original -> remplacement
        
        self._scan_system_fonts()
        self._load_font_mappings()
        
        self.logger.info(f"FontManager initialisé: {len(self.system_fonts)} polices système trouvées.")

    def _scan_system_fonts(self):
        font_paths = set()
        if platform.system() == "Windows":
            font_dir = Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts'
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
                    i = 0
                    while True:
                        try:
                            _, file_name, _ = winreg.EnumValue(key, i)
                            font_path = Path(file_name) if Path(file_name).is_absolute() else font_dir / file_name
                            if font_path.exists():
                                font_paths.add(font_path)
                            i += 1
                        except OSError: break
            except Exception as e: self.logger.error(f"Erreur d'accès au registre: {e}")

        for font_dir in self._get_system_font_directories():
            for ext in ('*.ttf', '*.otf', '*.ttc'):
                for font_file in font_dir.rglob(ext):
                    font_paths.add(font_file)
        
        for path in font_paths:
            self._process_font_file(path)

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
            if 'ttc' in str(font_path).lower():
                 for i in range(len(font_collection.reader.fonts)):
                    font = TTFont(font_path, fontNumber=i, lazy=True)
                    self._add_font_from_metadata(font, font_path)
            else:
                self._add_font_from_metadata(font_collection, font_path)
        except (TTLibError, Exception) as e:
            self.logger.debug(f"Impossible de traiter le fichier de police {font_path}: {e}")

    def _add_font_from_metadata(self, font: TTFont, font_path: Path):
        name_table = font.get('name')
        if not name_table: return
        
        full_name = name_table.getBestFullName()
        if full_name and full_name not in self.system_fonts:
            self.system_fonts[full_name] = font_path

    def get_all_available_fonts(self) -> List[str]:
        return sorted(list(self.system_fonts.keys()))

    def check_fonts_availability(self, required_fonts: List[str]) -> Dict[str, Any]:
        missing_fonts = {font for font in set(required_fonts) if font not in self.system_fonts}
        suggestions = {font: self._suggest_alternatives(font) for font in missing_fonts}
        return {'missing_fonts': sorted(list(missing_fonts)), 'suggestions': suggestions, 'all_available': not missing_fonts}

    def _suggest_alternatives(self, missing_font: str) -> List[Dict[str, Any]]:
        # La suggestion de base reste Arial si disponible
        if "Arial" in self.system_fonts: return [{'font_name': "Arial"}]
        available = self.get_all_available_fonts()
        return [{'font_name': available[0] if available else "Helvetica"}]
        
    def create_font_mapping(self, original_font: str, replacement_font_name: str):
        self.font_mappings[original_font] = replacement_font_name
        self._save_font_mappings()

    def get_font_mapping(self, original_font: str) -> Optional[str]:
        return self.font_mappings.get(original_font)

    def get_replacement_font_path(self, original_font_name: str) -> Optional[Path]:
        # Logique de remplacement simple
        replacement_name = self.get_font_mapping(original_font_name) or original_font_name
        
        if replacement_name in self.system_fonts:
            return self.system_fonts[replacement_name]

        # Fallback
        self.logger.warning(f"Police '{original_font_name}' (ou son remplacement '{replacement_name}') non trouvée. Utilisation d'Arial.")
        if "Arial" in self.system_fonts:
             return self.system_fonts["Arial"]
        
        if self.system_fonts:
            return next(iter(self.system_fonts.values()))
            
        return None

    def _load_font_mappings(self):
        if self.font_mappings_file.exists():
            try:
                with open(self.font_mappings_file, 'r', encoding='utf-8') as f:
                    self.font_mappings = json.load(f)
            except Exception as e: self.logger.warning(f"Impossible de charger les mappings: {e}")

    def _save_font_mappings(self):
        self.font_mappings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.font_mappings_file, 'w', encoding='utf-8') as f:
                json.dump(self.font_mappings, f, indent=2)
        except Exception as e: self.logger.error(f"Impossible de sauvegarder les mappings: {e}")
