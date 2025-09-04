#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Gestionnaire de sessions
Gestion des sessions de travail de traduction

Auteur: L'OréalGPT
Version: 1.0.0
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

class SessionStatus(Enum):
    """État d'une session de travail"""
    CREATED = "created"
    ANALYZING = "analyzing"
    READY_FOR_TRANSLATION = "ready_for_translation"
    TRANSLATING = "translating"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWING = "reviewing"
    READY_FOR_LAYOUT = "ready_for_layout"
    PROCESSING_LAYOUT = "processing_layout"
    READY_FOR_EXPORT = "ready_for_export"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class SessionInfo:
    """Informations d'une session"""
    id: str
    name: str
    created_at: str
    last_modified: str
    status: SessionStatus
    original_pdf_path: str
    original_pdf_name: str
    original_pdf_size: int
    source_language: str
    target_language: str
    page_count: int
    text_elements_count: int
    translation_progress: float  # 0.0 à 1.0
    review_progress: float  # 0.0 à 1.0
    has_backup: bool
    notes: str

class SessionManager:
    """Gestionnaire des sessions de traduction"""
    
    def __init__(self, app_data_dir: Path, file_utils=None):
        """
        Initialise le gestionnaire de sessions
        
        Args:
            app_data_dir: Répertoire de données de l'application
            file_utils: Instance de FileUtils (optionnel)
        """
        self.logger = logging.getLogger(__name__)
        self.app_data_dir = Path(app_data_dir)
        self.sessions_dir = self.app_data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Importer FileUtils si pas fourni
        if file_utils is None:
            from utils.file_utils import FileUtils
            self.file_utils = FileUtils(app_data_dir)
        else:
            self.file_utils = file_utils
        
        self.current_session: Optional[str] = None
        self.session_cache: Dict[str, SessionInfo] = {}
        
        # Charger les sessions existantes
        self._load_existing_sessions()
        
        self.logger.info("SessionManager initialisé")
    
    def _load_existing_sessions(self):
        """Charge les informations des sessions existantes"""
        try:
            for session_dir in self.sessions_dir.iterdir():
                if session_dir.is_dir():
                    session_info = self._load_session_info(session_dir)
                    if session_info:
                        self.session_cache[session_info.id] = session_info
            
            self.logger.info(f"{len(self.session_cache)} sessions chargées")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des sessions: {e}")
    
    def _load_session_info(self, session_dir: Path) -> Optional[SessionInfo]:
        """
        Charge les informations d'une session depuis son répertoire
        
        Args:
            session_dir: Répertoire de la session
            
        Returns:
            Informations de la session ou None si erreur
        """
        try:
            info_file = session_dir / "session_info.json"
            if not info_file.exists():
                return None
            
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convertir en SessionInfo
            return SessionInfo(
                id=data['id'],
                name=data['name'],
                created_at=data['created_at'],
                last_modified=data['last_modified'],
                status=SessionStatus(data['status']),
                original_pdf_path=data['original_pdf_path'],
                original_pdf_name=data['original_pdf_name'],
                original_pdf_size=data['original_pdf_size'],
                source_language=data['source_language'],
                target_language=data['target_language'],
                page_count=data['page_count'],
                text_elements_count=data['text_elements_count'],
                translation_progress=data.get('translation_progress', 0.0),
                review_progress=data.get('review_progress', 0.0),
                has_backup=data.get('has_backup', False),
                notes=data.get('notes', '')
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de {session_dir}: {e}")
            return None
    
    def create_session(self, pdf_path: Path, name: Optional[str] = None, 
                      source_lang: str = "auto", target_lang: str = "en") -> str:
        """
        Crée une nouvelle session de travail
        
        Args:
            pdf_path: Chemin vers le PDF source
            name: Nom de la session (optionnel)
            source_lang: Langue source
            target_lang: Langue cible
            
        Returns:
            ID de la session créée
        """
        try:
            # Générer un ID unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"session_{timestamp}"
            
            # Nom par défaut si non fourni
            if name is None:
                name = f"Traduction - {pdf_path.stem}"
            
            # Créer le répertoire de session
            session_dir = self.sessions_dir / session_id
            session_dir.mkdir(exist_ok=True)
            
            # Valider le PDF
            pdf_validation = self.file_utils.validate_pdf_structure(pdf_path)
            if not pdf_validation["is_valid"]:
                raise ValueError(f"PDF invalide: {pdf_validation['errors']}")
            
            # Créer les informations de session
            session_info = SessionInfo(
                id=session_id,
                name=name,
                created_at=datetime.now().isoformat(),
                last_modified=datetime.now().isoformat(),
                status=SessionStatus.CREATED,
                original_pdf_path=str(pdf_path.absolute()),
                original_pdf_name=pdf_path.name,
                original_pdf_size=pdf_validation["file_size"],
                source_language=source_lang,
                target_language=target_lang,
                page_count=pdf_validation["page_count"],
                text_elements_count=0,  # Sera mis à jour après analyse
                translation_progress=0.0,
                review_progress=0.0,
                has_backup=False,
                notes=""
            )
            
            # Sauvegarder les informations
            self._save_session_info(session_dir, session_info)
            
            # Copier le PDF original dans la session
            original_copy = session_dir / f"original_{pdf_path.name}"
            shutil.copy2(pdf_path, original_copy)
            
            # Ajouter au cache
            self.session_cache[session_id] = session_info
            self.current_session = session_id
            
            self.logger.info(f"Session créée: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création de session: {e}")
            raise
    
    def _save_session_info(self, session_dir: Path, session_info: SessionInfo):
        """Sauvegarde les informations de session"""
        info_file = session_dir / "session_info.json"
        
        # Convertir en dictionnaire avec enum vers string
        data = asdict(session_info)
        data['status'] = session_info.status.value
        
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_session(self, session_id: str) -> bool:
        """
        Charge une session existante
        
        Args:
            session_id: ID de la session à charger
            
        Returns:
            True si chargement réussi
        """
        try:
            if session_id not in self.session_cache:
                session_dir = self.sessions_dir / session_id
                if session_dir.exists():
                    session_info = self._load_session_info(session_dir)
                    if session_info:
                        self.session_cache[session_id] = session_info
                    else:
                        return False
                else:
                    return False
            
            self.current_session = session_id
            self.logger.info(f"Session chargée: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement de session {session_id}: {e}")
            return False
    
    def get_session_info(self, session_id: Optional[str] = None) -> Optional[SessionInfo]:
        """
        Retourne les informations d'une session
        
        Args:
            session_id: ID de la session (current si None)
            
        Returns:
            Informations de la session
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None:
            return None
        
        return self.session_cache.get(session_id)
    
    def update_session_status(self, status: SessionStatus, session_id: Optional[str] = None):
        """
        Met à jour le statut d'une session
        
        Args:
            status: Nouveau statut
            session_id: ID de la session (current si None)
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None or session_id not in self.session_cache:
            return
        
        session_info = self.session_cache[session_id]
        session_info.status = status
        session_info.last_modified = datetime.now().isoformat()
        
        # Sauvegarder
        session_dir = self.sessions_dir / session_id
        self._save_session_info(session_dir, session_info)
        
        self.logger.info(f"Session {session_id} - Statut mis à jour: {status.value}")
    
    def update_progress(self, translation_progress: Optional[float] = None,
                       review_progress: Optional[float] = None,
                       session_id: Optional[str] = None):
        """
        Met à jour les progrès de traduction/relecture
        
        Args:
            translation_progress: Progrès de traduction (0.0-1.0)
            review_progress: Progrès de relecture (0.0-1.0)
            session_id: ID de la session (current si None)
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None or session_id not in self.session_cache:
            return
        
        session_info = self.session_cache[session_id]
        
        if translation_progress is not None:
            session_info.translation_progress = max(0.0, min(1.0, translation_progress))
        
        if review_progress is not None:
            session_info.review_progress = max(0.0, min(1.0, review_progress))
        
        session_info.last_modified = datetime.now().isoformat()
        
        # Sauvegarder
        session_dir = self.sessions_dir / session_id
        self._save_session_info(session_dir, session_info)
    
    def save_analysis_data(self, analysis_data: Dict[str, Any], session_id: Optional[str] = None):
        """
        Sauvegarde les données d'analyse PDF
        
        Args:
            analysis_data: Données d'analyse
            session_id: ID de la session (current si None)
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None:
            return
        
        session_dir = self.sessions_dir / session_id
        analysis_file = session_dir / "analysis_data.json"
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        # Mettre à jour le nombre d'éléments texte
        if session_id in self.session_cache:
            text_count = len(analysis_data.get('text_elements', []))
            self.session_cache[session_id].text_elements_count = text_count
            self.session_cache[session_id].last_modified = datetime.now().isoformat()
            
            self._save_session_info(session_dir, self.session_cache[session_id])
        
        self.logger.info(f"Données d'analyse sauvegardées pour {session_id}")
    
    def load_analysis_data(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Charge les données d'analyse PDF
        
        Args:
            session_id: ID de la session (current si None)
            
        Returns:
            Données d'analyse ou None
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None:
            return None
        
        session_dir = self.sessions_dir / session_id
        analysis_file = session_dir / "analysis_data.json"
        
        try:
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Erreur lors du chargement des données d'analyse: {e}")
        
        return None
    
    def save_translation_export(self, export_data: str, session_id: Optional[str] = None) -> Path:
        """
        Sauvegarde l'export de traduction
        
        Args:
            export_data: Données d'export formatées
            session_id: ID de la session (current si None)
            
        Returns:
            Chemin vers le fichier d'export
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None:
            raise ValueError("Aucune session active")
        
        session_dir = self.sessions_dir / session_id
        export_file = session_dir / "translation_export.md"
        
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write(export_data)
        
        self.logger.info(f"Export de traduction sauvegardé pour {session_id}")
        return export_file
    
    def save_translation_import(self, import_data: str, session_id: Optional[str] = None):
        """
        Sauvegarde les données de traduction importées
        
        Args:
            import_data: Données de traduction importées
            session_id: ID de la session (current si None)
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None:
            return
        
        session_dir = self.sessions_dir / session_id
        import_file = session_dir / "translation_import.md"
        
        with open(import_file, 'w', encoding='utf-8') as f:
            f.write(import_data)
        
        # Sauvegarder aussi en JSON après parsing
        parsed_file = session_dir / "parsed_translations.json"
        # Le parsing sera fait par translation_parser
        
        self.logger.info(f"Import de traduction sauvegardé pour {session_id}")
    
    def get_session_directory(self, session_id: Optional[str] = None) -> Optional[Path]:
        """
        Retourne le répertoire d'une session
        
        Args:
            session_id: ID de la session (current si None)
            
        Returns:
            Chemin vers le répertoire de session
        """
        if session_id is None:
            session_id = self.current_session
        
        if session_id is None:
            return None
        
        return self.sessions_dir / session_id
    
    def list_sessions(self) -> List[SessionInfo]:
        """
        Retourne la liste de toutes les sessions
        
        Returns:
            Liste des informations de sessions
        """
        return list(self.session_cache.values())
    
    def delete_session(self, session_id: str, create_backup: bool = True) -> bool:
        """
        Supprime une session
        
        Args:
            session_id: ID de la session à supprimer
            create_backup: Créer une sauvegarde avant suppression
            
        Returns:
            True si suppression réussie
        """
        try:
            session_dir = self.sessions_dir / session_id
            
            if not session_dir.exists():
                return False
            
            # Créer backup si demandé
            if create_backup:
                backup_dir = self.app_data_dir / "backups" / "deleted_sessions"
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{session_id}_{timestamp}.zip"
                
                self.file_utils.create_export_package(session_dir, backup_path)
            
            # Supprimer le répertoire
            shutil.rmtree(session_dir)
            
            # Retirer du cache
            if session_id in self.session_cache:
                del self.session_cache[session_id]
            
            # Réinitialiser la session courante si c'était celle-ci
            if self.current_session == session_id:
                self.current_session = None
            
            self.logger.info(f"Session supprimée: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression de {session_id}: {e}")
            return False
    
    def cleanup_old_sessions(self, max_age_days: int = 90):
        """
        Nettoie les sessions anciennes
        
        Args:
            max_age_days: Âge maximum en jours
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            sessions_to_delete = []
            
            for session_info in self.session_cache.values():
                last_modified = datetime.fromisoformat(session_info.last_modified)
                if last_modified < cutoff_date and session_info.status == SessionStatus.COMPLETED:
                    sessions_to_delete.append(session_info.id)
            
            for session_id in sessions_to_delete:
                self.delete_session(session_id, create_backup=True)
            
            self.logger.info(f"{len(sessions_to_delete)} sessions anciennes nettoyées")
            
        except Exception as e:
            self.logger.error(f"Erreur lors du nettoyage des sessions: {e}")