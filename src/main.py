#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Point d'entrée principal
Application de traduction de PDFs avec préservation de la mise en page

Auteur: L'OréalGPT
Version: 1.0.0
"""

# import sys
# import os
import traceback
import logging
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# Ajouter le répertoire src au path pour les imports
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration du logging
def setup_logging():
    """Configure le système de logging"""
    app_data_dir = get_app_data_directory()
    log_dir = app_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "pdf_translator.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def get_app_data_directory():
    """Retourne le répertoire de données de l'application"""
    if sys.platform == "win32":
        app_data = Path(os.environ.get('APPDATA', ''))
    elif sys.platform == "darwin":  # macOS
        app_data = Path.home() / "Library" / "Application Support"
    else:  # Linux
        app_data = Path.home() / ".local" / "share"
    
    return app_data / "PDF-Layout-Translator"

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    required_modules = [
        'fitz',  # PyMuPDF
        'reportlab',
        'PIL',  # Pillow
        'fontTools'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        error_msg = f"Modules manquants: {', '.join(missing_modules)}\n"
        error_msg += "Veuillez installer les dépendances avec:\n"
        error_msg += "pip install -r requirements.txt"
        messagebox.showerror("Dépendances manquantes", error_msg)
        return False
    
    return True

def handle_exception(exc_type, exc_value, exc_traceback):
    """Gestionnaire global d'exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger = logging.getLogger(__name__)
    logger.error("Exception non gérée", exc_info=(exc_type, exc_value, exc_traceback))
    
    error_msg = f"Une erreur inattendue s'est produite:\n\n"
    error_msg += f"{exc_type.__name__}: {exc_value}\n\n"
    error_msg += "Consultez le fichier de log pour plus de détails."
    
    messagebox.showerror("Erreur", error_msg)

def create_app_structure():
    """Crée la structure de dossiers de l'application"""
    app_data_dir = get_app_data_directory()
    
    directories = [
        app_data_dir / "config",
        app_data_dir / "sessions",
        app_data_dir / "temp",
        app_data_dir / "fonts" / "custom_fonts",
        app_data_dir / "logs",
        app_data_dir / "exports"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def main():
    """Fonction principale de l'application"""
    try:
        # Configuration initiale
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Démarrage de PDF Layout Translator")
        
        # Vérifier les dépendances
        if not check_dependencies():
            sys.exit(1)
        
        # Créer la structure de l'application
        create_app_structure()
        
        # Configurer le gestionnaire d'exceptions global
        sys.excepthook = handle_exception
        
        # Importer et lancer l'interface graphique
        try:
            from gui.main_window import MainWindow
            from utils.config_manager import ConfigManager
            
            # Initialiser la configuration
            config_manager = ConfigManager()
            logger.info("Configuration chargée")
            
            # Créer la fenêtre principale
            root = tk.Tk()
            app = MainWindow(root, config_manager)
            
            logger.info("Interface graphique initialisée")
            
            # Démarrer l'application
            root.mainloop()
            
        except ImportError as e:
            error_msg = f"Erreur d'import: {e}\n"
            error_msg += "Vérifiez que tous les modules sont présents."
            messagebox.showerror("Erreur d'import", error_msg)
            logger.error(f"Erreur d'import: {e}")
            sys.exit(1)
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du démarrage: {e}")
            sys.exit(1)
    
    except Exception as e:
        # Fallback si même le logging échoue
        print(f"Erreur critique: {e}")
        print(traceback.format_exc())
        if 'tk' in sys.modules:
            try:
                messagebox.showerror("Erreur critique", f"Erreur critique: {e}")
            except:
                pass
        sys.exit(1)

if __name__ == "__main__":
    # Vérification de la version Python
    if sys.version_info < (3, 8):
        print("Python 3.8 ou supérieur requis")
        sys.exit(1)
    
    main()

