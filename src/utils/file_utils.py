#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Utilitaires de gestion de fichiers
Fonctions utilitaires pour la manipulation sécurisée des fichiers

Auteur: L'OréalGPT
Version: 1.0.0
"""

import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import hashlib
import json
import zipfile

class FileUtils:
    """Utilitaires pour la gestion des fichiers"""
    
    def __init__(self, app_data_dir: Path):
        """
        Initialise les utilitaires de fichiers
        
        Args:
            app_data_dir: Répertoire de données de l'application
        """
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = Path(app_data_dir)
        self.temp_dir = self.app_data_dir / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def is_pdf_file(file_path: Path) -> bool:
        """
        Vérifie si un fichier est un PDF valide
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            True si le fichier est un PDF valide
        """
        try:
            if not file_path.exists() or not file_path.is_file():
                return False
            
            # Vérifier l'extension
            if file_path.suffix.lower() != '.pdf':
                return False
            
            # Vérifier la signature du fichier (magic bytes)
            with open(file_path, 'rb') as f:
                header = f.read(5)
                return header == b'%PDF-'
                
        except Exception:
            return False
    
    @staticmethod
    def get_file_size_formatted(file_path: Path) -> str:
        """
        Retourne la taille du fichier formatée
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Taille formatée (ex: "2.3 MB")
        """
        try:
            size_bytes = file_path.stat().st_size
            
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            
            return f"{size_bytes:.1f} TB"
            
        except Exception:
            return "Taille inconnue"
    
    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """
        Calcule le hash MD5 d'un fichier
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            Hash MD5 du fichier
        """
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def create_safe_filename(self, base_name: str, extension: str = "") -> str:
        """
        Crée un nom de fichier sécurisé
        
        Args:
            base_name: Nom de base
            extension: Extension (avec ou sans point)
            
        Returns:
            Nom de fichier sécurisé
        """
        # Caractères interdits dans les noms de fichiers
        forbidden_chars = '<>:"/\\|?*'
        
        # Nettoyer le nom de base
        safe_name = base_name
        for char in forbidden_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Limiter la longueur
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        # Ajouter l'extension si fournie
        if extension:
            if not extension.startswith('.'):
                extension = '.' + extension
            safe_name += extension
        
        return safe_name
    
    def create_unique_filename(self, directory: Path, base_name: str, extension: str = "") -> Path:
        """
        Crée un nom de fichier unique dans un répertoire
        
        Args:
            directory: Répertoire de destination
            base_name: Nom de base
            extension: Extension
            
        Returns:
            Chemin vers le fichier unique
        """
        safe_name = self.create_safe_filename(base_name, extension)
        file_path = directory / safe_name
        
        # Si le fichier n'existe pas, on peut l'utiliser
        if not file_path.exists():
            return file_path
        
        # Sinon, ajouter un numéro
        name_without_ext = file_path.stem
        file_extension = file_path.suffix
        counter = 1
        
        while file_path.exists():
            new_name = f"{name_without_ext}_{counter}{file_extension}"
            file_path = directory / new_name
            counter += 1
        
        return file_path
    
    def create_temp_file(self, suffix: str = "", prefix: str = "pdf_translator_") -> Path:
        """
        Crée un fichier temporaire
        
        Args:
            suffix: Suffixe du fichier
            prefix: Préfixe du fichier
            
        Returns:
            Chemin vers le fichier temporaire
        """
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix=prefix,
            dir=self.temp_dir
        )
        os.close(fd)  # Fermer le descripteur de fichier
        
        return Path(temp_path)
    
    def create_temp_directory(self, prefix: str = "pdf_translator_") -> Path:
        """
        Crée un répertoire temporaire
        
        Args:
            prefix: Préfixe du répertoire
            
        Returns:
            Chemin vers le répertoire temporaire
        """
        temp_dir = tempfile.mkdtemp(
            prefix=prefix,
            dir=self.temp_dir
        )
        
        return Path(temp_dir)
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Nettoie les fichiers temporaires anciens
        
        Args:
            max_age_hours: Âge maximum en heures
        """
        try:
            current_time = datetime.now().timestamp()
            max_age_seconds = max_age_hours * 3600
            
            for item in self.temp_dir.iterdir():
                try:
                    item_age = current_time - item.stat().st_mtime
                    
                    if item_age > max_age_seconds:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                        
                        self.logger.info(f"Fichier temporaire supprimé: {item}")
                        
                except Exception as e:
                    self.logger.warning(f"Erreur lors de la suppression de {item}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage des fichiers temporaires: {e}")
    
    def backup_file(self, source_path: Path, backup_dir: Optional[Path] = None) -> Path:
        """
        Crée une sauvegarde d'un fichier
        
        Args:
            source_path: Fichier source
            backup_dir: Répertoire de sauvegarde (optionnel)
            
        Returns:
            Chemin vers la sauvegarde
        """
        if backup_dir is None:
            backup_dir = self.app_data_dir / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer nom de backup avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
        backup_path = backup_dir / backup_name
        
        # Copier le fichier
        shutil.copy2(source_path, backup_path)
        self.logger.info(f"Sauvegarde créée: {backup_path}")
        
        return backup_path
    
    def validate_pdf_structure(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Valide la structure d'un fichier PDF
        
        Args:
            pdf_path: Chemin vers le PDF
            
        Returns:
            Dictionnaire avec les informations de validation
        """
        validation_result = {
            "is_valid": False,
            "file_size": 0,
            "page_count": 0,
            "has_text": False,
            "has_images": False,
            "is_encrypted": False,
            "pdf_version": "",
            "errors": []
        }
        
        try:
            import fitz  # PyMuPDF
            
            # Vérifications de base
            if not self.is_pdf_file(pdf_path):
                validation_result["errors"].append("Fichier PDF invalide")
                return validation_result
            
            validation_result["file_size"] = pdf_path.stat().st_size
            
            # Ouvrir le PDF avec PyMuPDF
            doc = fitz.open(pdf_path)
            
            validation_result["page_count"] = len(doc)
            validation_result["is_encrypted"] = doc.needs_pass
            # --- FIX: Replaced doc.pdf_version() with metadata lookup ---
            validation_result["pdf_version"] = doc.metadata.get('format', 'Inconnue')
            
            # Vérifier le contenu
            has_text = False
            has_images = False
            
            for page_num in range(min(5, len(doc))):  # Vérifier les 5 premières pages max
                page = doc[page_num]
                
                # Vérifier le texte
                if page.get_text().strip():
                    has_text = True
                
                # Vérifier les images
                if page.get_images():
                    has_images = True
                
                if has_text and has_images:
                    break
            
            validation_result["has_text"] = has_text
            validation_result["has_images"] = has_images
            validation_result["is_valid"] = True
            
            doc.close()
            
        except ImportError:
            validation_result["errors"].append("PyMuPDF non disponible")
        except Exception as e:
            validation_result["errors"].append(f"Erreur lors de la validation: {str(e)}")
        
        return validation_result
    
    def create_export_package(self, session_dir: Path, export_path: Path) -> bool:
        """
        Crée un package d'export complet d'une session
        
        Args:
            session_dir: Répertoire de la session
            export_path: Chemin d'export du package ZIP
            
        Returns:
            True si l'export a réussi
        """
        try:
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in session_dir.rglob('*'):
                    if file_path.is_file():
                        # Chemin relatif dans le ZIP
                        arcname = file_path.relative_to(session_dir)
                        zipf.write(file_path, arcname)
            
            self.logger.info(f"Package d'export créé: {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du package: {e}")
            return False
    
    def extract_export_package(self, package_path: Path, extract_dir: Path) -> bool:
        """
        Extrait un package d'export
        
        Args:
            package_path: Chemin vers le package ZIP
            extract_dir: Répertoire d'extraction
            
        Returns:
            True si l'extraction a réussi
        """
        try:
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(package_path, 'r') as zipf:
                zipf.extractall(extract_dir)
            
            self.logger.info(f"Package extrait vers: {extract_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction du package: {e}")
            return False
    
    def get_available_disk_space(self, path: Path) -> int:
        """
        Retourne l'espace disque disponible en bytes
        
        Args:
            path: Chemin pour vérifier l'espace
            
        Returns:
            Espace disponible en bytes
        """
        try:
            statvfs = os.statvfs(path)
            return statvfs.f_frsize * statvfs.f_bavail
        except AttributeError:
            # Windows
            import shutil
            return shutil.disk_usage(path)[2]
        except Exception:
            return 0
    
    def ensure_sufficient_space(self, path: Path, required_bytes: int) -> bool:
        """
        Vérifie qu'il y a suffisamment d'espace disque
        
        Args:
            path: Chemin à vérifier
            required_bytes: Espace requis en bytes
            
        Returns:
            True s'il y a suffisamment d'espace
        """
        available = self.get_available_disk_space(path)
        margin = required_bytes * 0.1  # Marge de 10%
        return available > (required_bytes + margin)
