#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de configuration
Gestion des préférences utilisateur et configuration de l'application

Auteur: L'OréalGPT
Version: 1.0.0
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class ConfigManager:
    """Gestionnaire de configuration de l'application"""
    
    def __init__(self, app_data_dir: Optional[Path] = None):
        """
        Initialise le gestionnaire de configuration
        
        Args:
            app_data_dir: Répertoire de données de l'app (optionnel)
        """
        self.logger = logging.getLogger(__name__)
        
        # Déterminer le répertoire de données
        if app_data_dir is None:
            self.app_data_dir = self._get_app_data_directory()
        else:
            self.app_data_dir = Path(app_data_dir)
        
        # Chemins des fichiers de configuration
        self.config_dir = self.app_data_dir / "config"
        self.config_file = self.config_dir / "user_preferences.json"
        self.font_mappings_file = self.config_dir / "font_mappings.json"
        self.recent_sessions_file = self.config_dir / "recent_sessions.json"
        
        # S'assurer que le répertoire existe
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Charger la configuration
        self.config = self._load_config()
        self.font_mappings = self._load_font_mappings()
        self.recent_sessions = self._load_recent_sessions()
        
        self.logger.info("ConfigManager initialisé")
    
    def _get_app_data_directory(self) -> Path:
        """Détermine le répertoire de données selon l'OS"""
        import sys
        
        if sys.platform == "win32":
            app_data = Path(os.environ.get('APPDATA', ''))
        elif sys.platform == "darwin":  # macOS
            app_data = Path.home() / "Library" / "Application Support"
        else:  # Linux
            app_data = Path.home() / ".local" / "share"
        
        return app_data / "PDF-Layout-Translator"
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        return {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "language": {
                "interface": "fr",
                "default_source": "auto",
                "default_target": "en"
            },
            "translation": {
                "provider": "manual",  # manual, deepl, google, azure
                "batch_size": 50,
                "preserve_formatting": True,
                "quality_check": True
            },
            "layout": {
                "prefer_font_size_reduction": True,
                "max_font_size_reduction": 2,  # points
                "max_overflow_tolerance": 5,  # pixels
                "auto_expand_containers": False,
                "preserve_line_spacing": True,
                "min_line_height_ratio": 1.2
            },
            "fonts": {
                "fallback_font": "Arial",
                "auto_substitute": True,
                "embed_fonts": True,
                "check_font_licensing": True
            },
            "interface": {
                "window_width": 1200,
                "window_height": 800,
                "theme": "default",
                "show_tooltips": True,
                "auto_save_interval": 300,  # secondes
                "preview_quality": "medium"
            },
            "export": {
                "default_format": "pdf",
                "compression": "medium",
                "embed_metadata": True,
                "create_backup": True
            },
            "advanced": {
                "debug_mode": False,
                "log_level": "INFO",
                "temp_cleanup": True,
                "multithread_processing": True,
                "max_memory_usage": 512  # MB
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Charge la configuration depuis le fichier"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # Fusionner avec la config par défaut pour nouvelles options
                default_config = self._get_default_config()
                merged_config = self._merge_configs(default_config, user_config)
                
                self.logger.info("Configuration utilisateur chargée")
                return merged_config
            else:
                # Première utilisation, créer config par défaut
                default_config = self._get_default_config()
                self._save_config(default_config)
                self.logger.info("Configuration par défaut créée")
                return default_config
                
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de la config: {e}")
            # Retourner config par défaut en cas d'erreur
            return self._get_default_config()
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Fusionne récursivement les configurations"""
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _load_font_mappings(self) -> Dict[str, str]:
        """Charge les correspondances de polices"""
        try:
            if self.font_mappings_file.exists():
                with open(self.font_mappings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des mappings de polices: {e}")
        
        return {}
    
    def _load_recent_sessions(self) -> list:
        """Charge la liste des sessions récentes"""
        try:
            if self.recent_sessions_file.exists():
                with open(self.recent_sessions_file, 'r', encoding='utf-8') as f:
                    sessions = json.load(f)
                    # Garder seulement les 10 plus récentes
                    return sessions[-10:]
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des sessions récentes: {e}")
        
        return []
    
    def get(self, key_path: str, default=None):
        """
        Récupère une valeur de configuration par chemin
        
        Args:
            key_path: Chemin vers la clé (ex: "layout.max_overflow_tolerance")
            default: Valeur par défaut si clé non trouvée
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Définit une valeur de configuration par chemin
        
        Args:
            key_path: Chemin vers la clé (ex: "layout.max_overflow_tolerance")
            value: Nouvelle valeur
        """
        keys = key_path.split('.')
        config_ref = self.config
        
        # Naviguer jusqu'à l'avant-dernière clé
        for key in keys[:-1]:
            if key not in config_ref:
                config_ref[key] = {}
            config_ref = config_ref[key]
        
        # Définir la valeur finale
        config_ref[keys[-1]] = value
        
        # Sauvegarder automatiquement
        self.save()
    
    def save(self):
        """Sauvegarde la configuration"""
        try:
            self._save_config(self.config)
            self._save_font_mappings()
            self._save_recent_sessions()
            self.logger.info("Configuration sauvegardée")
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde: {e}")
    
    def _save_config(self, config: Dict[str, Any]):
        """Sauvegarde le fichier de configuration principal"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _save_font_mappings(self):
        """Sauvegarde les correspondances de polices"""
        with open(self.font_mappings_file, 'w', encoding='utf-8') as f:
            json.dump(self.font_mappings, f, indent=2)
    
    def _save_recent_sessions(self):
        """Sauvegarde la liste des sessions récentes"""
        with open(self.recent_sessions_file, 'w', encoding='utf-8') as f:
            json.dump(self.recent_sessions, f, indent=2)
    
    def add_font_mapping(self, original_font: str, replacement_font: str):
        """Ajoute une correspondance de police"""
        self.font_mappings[original_font] = replacement_font
        self._save_font_mappings()
        self.logger.info(f"Mapping de police ajouté: {original_font} -> {replacement_font}")
    
    def get_font_mapping(self, font_name: str) -> Optional[str]:
        """Récupère le remplacement pour une police"""
        return self.font_mappings.get(font_name)
    
    def add_recent_session(self, session_info: Dict[str, Any]):
        """Ajoute une session à la liste des récentes"""
        # Éviter les doublons
        session_id = session_info.get('id')
        self.recent_sessions = [s for s in self.recent_sessions if s.get('id') != session_id]
        
        # Ajouter à la fin
        self.recent_sessions.append(session_info)
        
        # Garder seulement les 10 plus récentes
        self.recent_sessions = self.recent_sessions[-10:]
        
        self._save_recent_sessions()
    
    def get_recent_sessions(self) -> list:
        """Retourne la liste des sessions récentes"""
        return self.recent_sessions.copy()
    
    def remove_recent_session(self, session_id: str):
        """Supprime une session de la liste des récentes"""
        self.recent_sessions = [s for s in self.recent_sessions if s.get('id') != session_id]
        self._save_recent_sessions()
    
    def reset_to_defaults(self):
        """Remet la configuration aux valeurs par défaut"""
        self.config = self._get_default_config()
        self.font_mappings = {}
        self.recent_sessions = []
        self.save()
        self.logger.info("Configuration remise aux valeurs par défaut")
    
    def export_config(self, export_path: Path):
        """Exporte la configuration vers un fichier"""
        export_data = {
            "config": self.config,
            "font_mappings": self.font_mappings,
            "export_date": datetime.now().isoformat()
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    def import_config(self, import_path: Path):
        """Importe une configuration depuis un fichier"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "config" in import_data:
                self.config = self._merge_configs(self._get_default_config(), import_data["config"])
            
            if "font_mappings" in import_data:
                self.font_mappings.update(import_data["font_mappings"])
            
            self.save()
            self.logger.info(f"Configuration importée depuis {import_path}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'import de configuration: {e}")
            raise