#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Fenêtre principale
Interface graphique principale de l'application

Auteur: L'OréalGPT
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Imports des modules core
from core.session_manager import SessionManager, SessionStatus
from core.pdf_analyzer import PDFAnalyzer
from core.text_extractor import TextExtractor
from core.translation_parser import TranslationParser, ValidationLevel
from utils.font_manager import FontManager
from core.layout_processor import LayoutProcessor
from core.pdf_reconstructor import PDFReconstructor

class MainWindow:
    """Fenêtre principale de l'application"""
    
    def __init__(self, root: tk.Tk, config_manager):
        """
        Initialise la fenêtre principale
        
        Args:
            root: Fenêtre racine tkinter
            config_manager: Gestionnaire de configuration
        """
        self.root = root
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Gestionnaires de composants
        self.session_manager: Optional[SessionManager] = None
        self.pdf_analyzer: Optional[PDFAnalyzer] = None
        self.text_extractor: Optional[TextExtractor] = None
        self.translation_parser: Optional[TranslationParser] = None
        self.font_manager: Optional[FontManager] = None
        self.layout_processor: Optional[LayoutProcessor] = None
        self.pdf_reconstructor: Optional[PDFReconstructor] = None
        
        # Variables d'état
        self.current_session_id: Optional[str] = None
        self.current_step = 0  # 0=Accueil, 1=Analyse, 2=Traduction, 3=Mise en page, 4=Export
        self.processing = False
        
        # Configuration de la fenêtre
        self._setup_window()
        
        # Création de l'interface
        self._create_widgets()
        
        # Initialisation des gestionnaires
        self._initialize_managers()
        
        # Chargement des sessions récentes
        self._load_recent_sessions()
        
        self.logger.info("Interface principale initialisée")
    
    def _setup_window(self):
        """Configure la fenêtre principale"""
        # Titre et icône
        self.root.title("PDF Layout Translator v1.0.0")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configuration des couleurs
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 10))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Warning.TLabel', foreground='orange')
        style.configure('Error.TLabel', foreground='red')
        
        # Centrer la fenêtre
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1200x800+{x}+{y}")
    
    def _create_widgets(self):
        """Crée les widgets de l'interface"""
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # En-tête
        self._create_header(main_frame)
        
        # Barre de progression globale
        self._create_progress_bar(main_frame)
        
        # Notebook pour les étapes
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(10, 0))
        
        # Onglets pour chaque étape
        self._create_home_tab()
        self._create_analysis_tab()
        self._create_translation_tab()
        self._create_layout_tab()
        self._create_export_tab()
        
        # Barre de statut
        self._create_status_bar(main_frame)
        
        # Menu
        self._create_menu()
    
    def _create_header(self, parent):
        """Crée l'en-tête de l'application"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 10))
        
        # Titre
        title_label = ttk.Label(header_frame, text="PDF Layout Translator", style='Title.TLabel')
        title_label.pack(side='left')
        
        # Informations de session
        self.session_info_frame = ttk.Frame(header_frame)
        self.session_info_frame.pack(side='right')
        
        self.session_label = ttk.Label(self.session_info_frame, text="Aucune session", style='Status.TLabel')
        self.session_label.pack()
    
    def _create_progress_bar(self, parent):
        """Crée la barre de progression globale"""
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(progress_frame, text="Progression:", style='Subtitle.TLabel').pack(side='left')
        
        self.global_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.global_progress.pack(side='left', padx=(10, 0), fill='x', expand=True)
        
        self.progress_label = ttk.Label(progress_frame, text="Prêt", style='Status.TLabel')
        self.progress_label.pack(side='right', padx=(10, 0))
    
    def _create_home_tab(self):
        """Crée l'onglet d'accueil"""
        self.home_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.home_frame, text="🏠 Accueil")
        
        # Section nouveau projet
        new_project_frame = ttk.LabelFrame(self.home_frame, text="Nouveau Projet", padding=20)
        new_project_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Label(new_project_frame, text="Sélectionnez un fichier PDF à traduire:", style='Subtitle.TLabel').pack(anchor='w')
        
        file_frame = ttk.Frame(new_project_frame)
        file_frame.pack(fill='x', pady=(10, 0))
        
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly')
        self.file_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(file_frame, text="Parcourir...", command=self._browse_pdf_file).pack(side='right', padx=(10, 0))
        
        # Configuration des langues
        lang_frame = ttk.Frame(new_project_frame)
        lang_frame.pack(fill='x', pady=(20, 0))
        
        ttk.Label(lang_frame, text="Langue source:").pack(side='left')
        self.source_lang_var = tk.StringVar(value="auto")
        source_combo = ttk.Combobox(lang_frame, textvariable=self.source_lang_var, 
                                   values=["auto", "fr", "en", "es", "de", "it"], width=8)
        source_combo.pack(side='left', padx=(10, 0))
        
        ttk.Label(lang_frame, text="Langue cible:").pack(side='left', padx=(20, 0))
        self.target_lang_var = tk.StringVar(value="en")
        target_combo = ttk.Combobox(lang_frame, textvariable=self.target_lang_var,
                                   values=["en", "fr", "es", "de", "it", "pt"], width=8)
        target_combo.pack(side='left', padx=(10, 0))
        
        # Bouton démarrer
        self.start_button = ttk.Button(new_project_frame, text="Démarrer l'analyse", 
                                      command=self._start_new_project, style='Accent.TButton')
        self.start_button.pack(pady=(20, 0))
        
        # Section sessions récentes
        recent_frame = ttk.LabelFrame(self.home_frame, text="Sessions Récentes", padding=20)
        recent_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        # Liste des sessions récentes
        self.sessions_tree = ttk.Treeview(recent_frame, columns=('date', 'status', 'progress'), show='tree headings')
        self.sessions_tree.heading('#0', text='Nom')
        self.sessions_tree.heading('date', text='Date')
        self.sessions_tree.heading('status', text='Statut')
        self.sessions_tree.heading('progress', text='Progrès')
        self.sessions_tree.pack(fill='both', expand=True)
        
        # Boutons pour les sessions
        sessions_buttons_frame = ttk.Frame(recent_frame)
        sessions_buttons_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(sessions_buttons_frame, text="Ouvrir", command=self._open_selected_session).pack(side='left')
        ttk.Button(sessions_buttons_frame, text="Supprimer", command=self._delete_selected_session).pack(side='left', padx=(10, 0))
        ttk.Button(sessions_buttons_frame, text="Actualiser", command=self._load_recent_sessions).pack(side='right')
    
    def _create_analysis_tab(self):
        """Crée l'onglet d'analyse"""
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="🔍 Analyse")
        
        # Informations du document
        info_frame = ttk.LabelFrame(self.analysis_frame, text="Informations du Document", padding=20)
        info_frame.pack(fill='x', padx=20, pady=20)
        
        self.doc_info_text = scrolledtext.ScrolledText(info_frame, height=6, state='disabled')
        self.doc_info_text.pack(fill='x')
        
        # Résultats d'analyse
        results_frame = ttk.LabelFrame(self.analysis_frame, text="Résultats d'Analyse", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.analysis_text = scrolledtext.ScrolledText(results_frame, state='disabled')
        self.analysis_text.pack(fill='both', expand=True)
        
        # Boutons
        buttons_frame = ttk.Frame(self.analysis_frame)
        buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.analyze_button = ttk.Button(buttons_frame, text="Analyser le PDF", command=self._analyze_pdf)
        self.analyze_button.pack(side='left')
        
        self.continue_to_translation_button = ttk.Button(buttons_frame, text="Continuer vers Traduction", 
                                                        command=self._continue_to_translation, state='disabled')
        self.continue_to_translation_button.pack(side='right')
    
    def _create_translation_tab(self):
        """Crée l'onglet de traduction"""
        self.translation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.translation_frame, text="🌐 Traduction")
        
        # Instructions
        instructions_frame = ttk.LabelFrame(self.translation_frame, text="Instructions", padding=20)
        instructions_frame.pack(fill='x', padx=20, pady=20)
        
        instructions_text = """1. Cliquez sur "Générer Export" pour créer les fichiers de traduction
2. Utilisez votre IA préférée pour traduire le contenu
3. Copiez la traduction dans la zone ci-dessous
4. Cliquez sur "Valider Traduction" pour continuer"""
        
        ttk.Label(instructions_frame, text=instructions_text, justify='left').pack(anchor='w')
        
        # Boutons d'export
        export_frame = ttk.Frame(self.translation_frame)
        export_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.generate_export_button = ttk.Button(export_frame, text="Générer Export pour Traduction", 
                                               command=self._generate_translation_export)
        self.generate_export_button.pack(side='left')
        
        self.open_export_folder_button = ttk.Button(export_frame, text="Ouvrir Dossier d'Export", 
                                                   command=self._open_export_folder, state='disabled')
        self.open_export_folder_button.pack(side='left', padx=(10, 0))
        
        # Zone de saisie traduction
        input_frame = ttk.LabelFrame(self.translation_frame, text="Traduction de l'IA", padding=20)
        input_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.translation_input = scrolledtext.ScrolledText(input_frame, height=15)
        self.translation_input.pack(fill='both', expand=True)
        
        # Validation
        validation_frame = ttk.Frame(self.translation_frame)
        validation_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.validate_translation_button = ttk.Button(validation_frame, text="Valider Traduction", 
                                                     command=self._validate_translation)
        self.validate_translation_button.pack(side='left')
        
        # Niveau de validation
        ttk.Label(validation_frame, text="Niveau de validation:").pack(side='left', padx=(20, 0))
        self.validation_level_var = tk.StringVar(value="moderate")
        validation_combo = ttk.Combobox(validation_frame, textvariable=self.validation_level_var,
                                       values=["strict", "moderate", "permissive"], width=10)
        validation_combo.pack(side='left', padx=(10, 0))
        
        self.continue_to_layout_button = ttk.Button(validation_frame, text="Continuer vers Mise en Page", 
                                                   command=self._continue_to_layout, state='disabled')
        self.continue_to_layout_button.pack(side='right')
    
    def _create_layout_tab(self):
        """Crée l'onglet de mise en page"""
        self.layout_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.layout_frame, text="📐 Mise en Page")
        
        # Paramètres de mise en page
        settings_frame = ttk.LabelFrame(self.layout_frame, text="Paramètres", padding=20)
        settings_frame.pack(fill='x', padx=20, pady=20)
        
        # Options de mise en page
        self.allow_font_reduction_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Autoriser la réduction de police", 
                       variable=self.allow_font_reduction_var).pack(anchor='w')
        
        self.allow_container_expansion_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Autoriser l'expansion des conteneurs", 
                       variable=self.allow_container_expansion_var).pack(anchor='w')
        
        # Résultats de mise en page
        results_frame = ttk.LabelFrame(self.layout_frame, text="Résultats de Mise en Page", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.layout_results_text = scrolledtext.ScrolledText(results_frame, state='disabled')
        self.layout_results_text.pack(fill='both', expand=True)
        
        # Boutons
        layout_buttons_frame = ttk.Frame(self.layout_frame)
        layout_buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.process_layout_button = ttk.Button(layout_buttons_frame, text="Traiter la Mise en Page", 
                                              command=self._process_layout)
        self.process_layout_button.pack(side='left')
        
        self.preview_layout_button = ttk.Button(layout_buttons_frame, text="Aperçu", 
                                              command=self._preview_layout, state='disabled')
        self.preview_layout_button.pack(side='left', padx=(10, 0))
        
        self.continue_to_export_button = ttk.Button(layout_buttons_frame, text="Continuer vers Export", 
                                                   command=self._continue_to_export, state='disabled')
        self.continue_to_export_button.pack(side='right')
    
    def _create_export_tab(self):
        """Crée l'onglet d'export"""
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="📤 Export")
        
        # Options d'export
        options_frame = ttk.LabelFrame(self.export_frame, text="Options d'Export", padding=20)
        options_frame.pack(fill='x', padx=20, pady=20)
        
        # Nom de fichier
        filename_frame = ttk.Frame(options_frame)
        filename_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(filename_frame, text="Nom de fichier:").pack(side='left')
        self.output_filename_var = tk.StringVar()
        ttk.Entry(filename_frame, textvariable=self.output_filename_var).pack(side='left', fill='x', expand=True, padx=(10, 0))
        
        # Options
        self.create_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Créer une sauvegarde du fichier original", 
                       variable=self.create_backup_var).pack(anchor='w')
        
        self.create_comparison_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Créer un PDF de comparaison", 
                       variable=self.create_comparison_var).pack(anchor='w')
        
        self.optimize_output_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Optimiser le fichier de sortie", 
                       variable=self.optimize_output_var).pack(anchor='w')
        
        # Résultats d'export
        export_results_frame = ttk.LabelFrame(self.export_frame, text="Résultats d'Export", padding=20)
        export_results_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.export_results_text = scrolledtext.ScrolledText(export_results_frame, state='disabled')
        self.export_results_text.pack(fill='both', expand=True)
        
        # Boutons
        export_buttons_frame = ttk.Frame(self.export_frame)
        export_buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.export_pdf_button = ttk.Button(export_buttons_frame, text="Exporter PDF", 
                                           command=self._export_pdf)
        self.export_pdf_button.pack(side='left')
        
        self.open_output_folder_button = ttk.Button(export_buttons_frame, text="Ouvrir Dossier de Sortie", 
                                                   command=self._open_output_folder, state='disabled')
        self.open_output_folder_button.pack(side='left', padx=(10, 0))
        
        self.new_project_button = ttk.Button(export_buttons_frame, text="Nouveau Projet", 
                                            command=self._new_project, state='disabled')
        self.new_project_button.pack(side='right')
    
    def _create_status_bar(self, parent):
        """Crée la barre de statut"""
        status_frame = ttk.Frame(parent, relief='sunken', borderwidth=1)
        status_frame.pack(fill='x', side='bottom')
        
        self.status_label = ttk.Label(status_frame, text="Prêt", style='Status.TLabel')
        self.status_label.pack(side='left', padx=5, pady=2)
        
        # Indicateur de traitement
        self.processing_indicator = ttk.Progressbar(status_frame, length=100, mode='indeterminate')
        self.processing_indicator.pack(side='right', padx=5, pady=2)
    
    def _create_menu(self):
        """Crée le menu de l'application"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu Fichier
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Nouveau Projet...", command=self._browse_pdf_file)
        file_menu.add_command(label="Ouvrir Session...", command=self._open_session_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exporter Session...", command=self._export_session)
        file_menu.add_command(label="Importer Session...", command=self._import_session)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.quit)
        
        # Menu Outils
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Outils", menu=tools_menu)
        tools_menu.add_command(label="Gestionnaire de Polices", command=self._open_font_manager)
        tools_menu.add_command(label="Préférences...", command=self._open_preferences)
        
        # Menu Aide
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="Guide d'utilisation", command=self._show_user_guide)
        help_menu.add_command(label="À propos", command=self._show_about)
    
    def _initialize_managers(self):
        """Initialise les gestionnaires de composants"""
        try:
            app_data_dir = self.config_manager.app_data_dir
            
            self.session_manager = SessionManager(app_data_dir)
            self.pdf_analyzer = PDFAnalyzer()
            self.text_extractor = TextExtractor()
            self.font_manager = FontManager(app_data_dir)
            self.layout_processor = LayoutProcessor(self.config_manager)
            self.pdf_reconstructor = PDFReconstructor(self.config_manager, self.font_manager)
            
            # Gestionnaire de parsing avec niveau par défaut
            validation_level = ValidationLevel.MODERATE
            self.translation_parser = TranslationParser(validation_level)
            
            self.logger.info("Gestionnaires initialisés avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation des gestionnaires: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de l'initialisation: {e}")
    
    def _load_recent_sessions(self):
        """Charge les sessions récentes dans la liste"""
        if not self.session_manager:
            return
        
        # Vider la liste actuelle
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        
        # Charger les sessions
        sessions = self.session_manager.list_sessions()
        
        for session in sessions[-10:]:  # Les 10 plus récentes
            # Formater la date
            try:
                date_obj = datetime.fromisoformat(session.last_modified)
                date_str = date_obj.strftime("%d/%m/%Y %H:%M")
            except:
                date_str = "Date inconnue"
            
            # Calculer le progrès global
            progress = int((session.translation_progress + session.review_progress) * 50)
            
            # Insérer dans la liste
            self.sessions_tree.insert('', 'end', 
                                    text=session.name,
                                    values=(date_str, session.status.value, f"{progress}%"),
                                    tags=(session.id,))
    
    def _browse_pdf_file(self):
        """Ouvre le dialogue de sélection de fichier PDF"""
        filename = filedialog.askopenfilename(
            title="Sélectionner un fichier PDF",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")]
        )
        
        if filename:
            self.file_path_var.set(filename)
            self.start_button.config(state='normal')
    
    def _start_new_project(self):
        """Démarre un nouveau projet"""
        pdf_path = self.file_path_var.get()
        if not pdf_path:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fichier PDF.")
            return
        
        try:
            # Créer une nouvelle session
            session_id = self.session_manager.create_session(
                Path(pdf_path),
                source_lang=self.source_lang_var.get(),
                target_lang=self.target_lang_var.get()
            )
            
            self.current_session_id = session_id
            self._update_session_info()
            
            # --- MODIFICATION : Enchaînement automatique de l'analyse ---
            # Passer à l'onglet d'analyse
            self.notebook.select(1)
            self._update_global_progress(1, "Session créée, démarrage de l'analyse...")
            
            # Lancer l'analyse automatiquement
            self._analyze_pdf()
            
        except Exception as e:
            self.logger.error(f"Erreur création session: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la création de la session: {e}")
    
    def _analyze_pdf(self):
        """Lance l'analyse du PDF"""
        if not self.current_session_id:
            messagebox.showwarning("Attention", "Aucune session active.")
            return
        
        def analyze_thread():
            try:
                self._set_processing(True, "Analyse du PDF en cours...")
                
                session_info = self.session_manager.get_session_info(self.current_session_id)
                pdf_path = Path(session_info.original_pdf_path)
                
                # Analyser le PDF
                analysis_data = self.pdf_analyzer.analyze_pdf(pdf_path)
                
                # Sauvegarder les résultats
                self.session_manager.save_analysis_data(analysis_data, self.current_session_id)
                self.session_manager.update_session_status(SessionStatus.READY_FOR_TRANSLATION, self.current_session_id)
                
                # Mettre à jour l'interface
                self.root.after(0, self._display_analysis_results, analysis_data)
                self._update_global_progress(2, "Analyse terminée")
                
            except Exception as e:
                self.logger.error(f"Erreur analyse PDF: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors de l'analyse: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def _display_analysis_results(self, analysis_data: Dict[str, Any]):
        """Affiche les résultats d'analyse"""
        # Informations du document
        doc_info = analysis_data['document_info']
        info_text = f"""Pages: {doc_info['page_count']}
Version PDF: {doc_info['pdf_version']}
Contient des liens: {'Oui' if doc_info['has_links'] else 'Non'}
Contient des formulaires: {'Oui' if doc_info['has_forms'] else 'Non'}"""
        
        self._update_text_widget(self.doc_info_text, info_text)
        
        # Résultats détaillés
        stats = analysis_data['statistics']
        results_text = f"""STATISTIQUES D'ANALYSE

Éléments de texte: {stats['total_text_elements']}
Caractères total: {stats['total_characters']:,}
Mots total: {stats['total_words']:,}
Mots par élément (moyenne): {stats['average_words_per_element']:.1f}

DISTRIBUTION DU CONTENU:
"""
        
        for content_type, count in stats['content_type_distribution'].items():
            results_text += f"  {content_type}: {count}\n"
        
        results_text += f"\nPOLICES UTILISÉES:\n"
        for font in analysis_data['fonts_used'][:5]:  # Les 5 plus utilisées
            results_text += f"  {font['name']} ({font['page_count']} pages)\n"
        
        results_text += f"\nCOMPLEXITÉ DE TRADUCTION: {stats['translation_complexity']}"
        
        self._update_text_widget(self.analysis_text, results_text)
        
        # Activer le bouton suivant
        self.continue_to_translation_button.config(state='normal')
    
    def _continue_to_translation(self):
        """Passe à l'étape de traduction"""
        self.notebook.select(2)  # Onglet Traduction
        self._update_global_progress(3, "Prêt pour la traduction")
    
    def _generate_translation_export(self):
        """Génère les fichiers d'export pour la traduction"""
        if not self.current_session_id:
            return
        
        def export_thread():
            try:
                self._set_processing(True, "Génération de l'export...")
                
                # Charger les données d'analyse
                analysis_data = self.session_manager.load_analysis_data(self.current_session_id)
                if not analysis_data:
                    raise ValueError("Données d'analyse non trouvées")
                
                # Extraire pour traduction
                extraction_data = self.text_extractor.extract_for_translation(
                    analysis_data,
                    source_lang=self.source_lang_var.get(),
                    target_lang=self.target_lang_var.get()
                )
                
                # Créer le package d'export
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                export_dir = session_dir / "exports"
                
                files_created = self.text_extractor.create_export_package(extraction_data, export_dir)
                
                # Mettre à jour l'interface
                self.root.after(0, lambda: self._show_export_success(export_dir, files_created))
                
            except Exception as e:
                self.logger.error(f"Erreur génération export: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors de la génération: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=export_thread, daemon=True).start()
    
    def _show_export_success(self, export_dir: Path, files_created: Dict[str, Path]):
        """Affiche le succès de l'export"""
        message = f"Export généré avec succès dans :\n{export_dir}\n\nFichiers créés:\n"
        for file_type, file_path in files_created.items():
            message += f"  • {file_path.name}\n"
        
        messagebox.showinfo("Export Généré", message)
        self.open_export_folder_button.config(state='normal')
        self._export_folder = export_dir
    
    def _open_export_folder(self):
        """Ouvre le dossier d'export"""
        if hasattr(self, '_export_folder'):
            import os
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(self._export_folder)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{self._export_folder}"')
            else:  # Linux
                os.system(f'xdg-open "{self._export_folder}"')
    
    def _validate_translation(self):
        """Valide la traduction saisie"""
        translation_content = self.translation_input.get('1.0', tk.END).strip()
        if not translation_content:
            messagebox.showwarning("Attention", "Veuillez saisir la traduction.")
            return
        
        def validate_thread():
            try:
                self._set_processing(True, "Validation de la traduction...")
                
                # Charger les données d'extraction
                analysis_data = self.session_manager.load_analysis_data(self.current_session_id)
                extraction_data = self.text_extractor.extract_for_translation(analysis_data)
                
                # Configurer le niveau de validation
                level_map = {
                    'strict': ValidationLevel.STRICT,
                    'moderate': ValidationLevel.MODERATE,
                    'permissive': ValidationLevel.PERMISSIVE
                }
                self.translation_parser.validation_level = level_map[self.validation_level_var.get()]
                
                # Parser et valider
                parse_report = self.translation_parser.parse_translated_content(
                    translation_content, extraction_data
                )
                
                # Afficher les résultats
                self.root.after(0, lambda: self._show_validation_results(parse_report))
                
                # Si succès, sauvegarder et continuer
                if parse_report.result.value in ['success', 'partial']:
                    validated_translations = self.translation_parser.export_validated_translations(parse_report)
                    
                    # Sauvegarder dans la session
                    session_dir = self.session_manager.get_session_directory(self.current_session_id)
                    with open(session_dir / "validated_translations.json", 'w', encoding='utf-8') as f:
                        json.dump(validated_translations, f, indent=2, ensure_ascii=False)
                    
                    self.session_manager.update_session_status(SessionStatus.READY_FOR_LAYOUT, self.current_session_id)
                    self.root.after(0, lambda: self.continue_to_layout_button.config(state='normal'))
                
            except Exception as e:
                self.logger.error(f"Erreur validation traduction: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors de la validation: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=validate_thread, daemon=True).start()
    
    def _show_validation_results(self, parse_report):
        """Affiche les résultats de validation"""
        if parse_report.result.value == 'success':
            icon = "✅"
            message = "Traduction validée avec succès!"
        elif parse_report.result.value == 'partial':
            icon = "⚠️"
            message = "Traduction partiellement validée."
        else:
            icon = "❌"
            message = "Échec de la validation de la traduction."
        
        details = f"""{message}

Éléments traités: {parse_report.parsed_elements}/{parse_report.total_elements}
Facteur d'expansion moyen: {parse_report.overall_expansion_factor:.2f}x

Recommandations:
"""
        for rec in parse_report.recommendations:
            details += f"  • {rec}\n"
        
        messagebox.showinfo(f"Validation {icon}", details)
    
    def _continue_to_layout(self):
        """Passe à l'étape de mise en page"""
        self.notebook.select(3)  # Onglet Mise en Page
        self._update_global_progress(4, "Prêt pour la mise en page")
    
    def _process_layout(self):
        """Traite la mise en page"""
        if not self.current_session_id:
            return
        
        def layout_thread():
            try:
                self._set_processing(True, "Traitement de la mise en page...")
                
                # Charger les données nécessaires
                analysis_data = self.session_manager.load_analysis_data(self.current_session_id)
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                
                with open(session_dir / "validated_translations.json", 'r', encoding='utf-8') as f:
                    validated_translations = json.load(f)
                
                # Traiter la mise en page
                layout_result = self.layout_processor.process_layout(
                    validated_translations, analysis_data
                )
                
                # Sauvegarder les résultats
                with open(session_dir / "layout_result.json", 'w', encoding='utf-8') as f:
                    json.dump(layout_result, f, indent=2, ensure_ascii=False)
                
                # Mettre à jour l'interface
                self.root.after(0, lambda: self._display_layout_results(layout_result))
                
                self.session_manager.update_session_status(SessionStatus.READY_FOR_EXPORT, self.current_session_id)
                
            except Exception as e:
                self.logger.error(f"Erreur traitement mise en page: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors du traitement: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=layout_thread, daemon=True).start()
    
    def _display_layout_results(self, layout_result: Dict[str, Any]):
        """Affiche les résultats de mise en page"""
        quality = layout_result['quality_metrics']
        
        results_text = f"""RÉSULTATS DE MISE EN PAGE

Qualité globale: {quality['overall_quality']:.2f} ({quality['quality_level']})
Préservation des polices: {quality['font_size_preservation']:.2f}
Préservation des dimensions: {quality['bbox_preservation']:.2f}

Éléments traités: {len(layout_result['element_layouts'])}
Éléments avec problèmes: {quality['elements_with_issues']}
Solutions appliquées: {quality['total_solutions_applied']}

RECOMMANDATIONS:
"""
        
        for rec in layout_result['recommendations']:
            results_text += f"  • {rec}\n"
        
        self._update_text_widget(self.layout_results_text, results_text)
        
        # Activer les boutons
        self.preview_layout_button.config(state='normal')
        self.continue_to_export_button.config(state='normal')
    
    def _continue_to_export(self):
        """Passe à l'étape d'export"""
        self.notebook.select(4)  # Onglet Export
        self._update_global_progress(5, "Prêt pour l'export")
        
        # Suggérer un nom de fichier
        if self.current_session_id:
            session_info = self.session_manager.get_session_info(self.current_session_id)
            if session_info:
                base_name = Path(session_info.original_pdf_name).stem
                suggested_name = f"{base_name}_traduit.pdf"
                self.output_filename_var.set(suggested_name)
    
    def _export_pdf(self):
        """Exporte le PDF final"""
        output_filename = self.output_filename_var.get().strip()
        if not output_filename:
            messagebox.showwarning("Attention", "Veuillez spécifier un nom de fichier.")
            return
        
        def export_thread():
            try:
                self._set_processing(True, "Export du PDF en cours...")
                
                # Préparer les chemins
                session_info = self.session_manager.get_session_info(self.current_session_id)
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                
                original_pdf_path = Path(session_info.original_pdf_path)
                output_pdf_path = original_pdf_path.parent / output_filename
                
                # Charger les données
                with open(session_dir / "layout_result.json", 'r', encoding='utf-8') as f:
                    layout_data = json.load(f)
                
                with open(session_dir / "validated_translations.json", 'r', encoding='utf-8') as f:
                    validated_translations = json.load(f)
                
                # Reconstruire le PDF
                reconstruction_result = self.pdf_reconstructor.reconstruct_pdf(
                    original_pdf_path, layout_data, validated_translations, output_pdf_path,
                    preserve_original=self.create_backup_var.get()
                )
                
                # Créer PDF de comparaison si demandé
                if self.create_comparison_var.get() and reconstruction_result.success:
                    comparison_path = output_pdf_path.parent / f"{output_pdf_path.stem}_comparaison.pdf"
                    self.pdf_reconstructor.create_comparison_pdf(
                        original_pdf_path, output_pdf_path, comparison_path
                    )
                
                # Mettre à jour l'interface
                self.root.after(0, lambda: self._show_export_results(reconstruction_result, output_pdf_path))
                
                if reconstruction_result.success:
                    self.session_manager.update_session_status(SessionStatus.COMPLETED, self.current_session_id)
                
            except Exception as e:
                self.logger.error(f"Erreur export PDF: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors de l'export: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=export_thread, daemon=True).start()
    
    def _show_export_results(self, result, output_path: Path):
        """Affiche les résultats d'export"""
        if result.success:
            icon = "✅"
            message = "Export réussi!"
        else:
            icon = "❌"
            message = "Export échoué."
        
        results_text = f"""{message}

Fichier de sortie: {output_path.name}
Temps de traitement: {result.processing_time:.1f}s
Pages traitées: {result.pages_processed}
Éléments traités: {result.elements_processed}
Score de qualité: {result.quality_score:.2f}

Taille originale: {result.file_size_original / 1024 / 1024:.1f} MB
Taille finale: {result.file_size_output / 1024 / 1024:.1f} MB

Erreurs: {len(result.errors)}
Avertissements: {len(result.warnings)}
"""
        
        if result.errors:
            results_text += "\nERREURS:\n"
            for error in result.errors[:5]:  # Limiter à 5
                results_text += f"  • {error}\n"
        
        self._update_text_widget(self.export_results_text, results_text)
        
        if result.success:
            self.open_output_folder_button.config(state='normal')
            self.new_project_button.config(state='normal')
            self._output_folder = output_path.parent
            
            messagebox.showinfo(f"Export {icon}", f"PDF exporté avec succès !\n\n{output_path}")
    
    def _open_output_folder(self):
        """Ouvre le dossier de sortie"""
        if hasattr(self, '_output_folder'):
            import os
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(self._output_folder)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{self._output_folder}"')
            else:  # Linux
                os.system(f'xdg-open "{self._output_folder}"')
    
    def _new_project(self):
        """Démarre un nouveau projet"""
        # Réinitialiser l'interface
        self.current_session_id = None
        self.notebook.select(0)  # Onglet Accueil
        self._update_global_progress(0, "Prêt")
        
        # Réinitialiser les boutons
        self._reset_interface()
        
        # Actualiser les sessions récentes
        self._load_recent_sessions()
    
    # Méthodes utilitaires
    
    def _update_session_info(self):
        """Met à jour l'affichage des informations de session"""
        if self.current_session_id and self.session_manager:
            session_info = self.session_manager.get_session_info(self.current_session_id)
            if session_info:
                self.session_label.config(text=f"Session: {session_info.name}")
        else:
            self.session_label.config(text="Aucune session")
    
    def _update_global_progress(self, step: int, status: str):
        """Met à jour la progression globale"""
        self.current_step = step
        progress_value = (step / 5) * 100
        self.global_progress['value'] = progress_value
        self.progress_label.config(text=status)
    
    def _set_processing(self, processing: bool, status: str = ""):
        """Active/désactive l'indicateur de traitement"""
        self.processing = processing
        
        if processing:
            self.processing_indicator.start()
            if status:
                self.status_label.config(text=status)
        else:
            self.processing_indicator.stop()
            self.status_label.config(text="Prêt")
    
    def _update_text_widget(self, widget, text: str):
        """Met à jour un widget de texte"""
        widget.config(state='normal')
        widget.delete('1.0', tk.END)
        widget.insert('1.0', text)
        widget.config(state='disabled')
    
    def _reset_interface(self):
        """Remet l'interface à zéro"""
        # Réinitialiser les widgets
        self.file_path_var.set("")
        self.translation_input.delete('1.0', tk.END)
        self.output_filename_var.set("")
        
        # Réinitialiser les boutons
        buttons_to_disable = [
            self.continue_to_translation_button,
            self.continue_to_layout_button,
            self.continue_to_export_button,
            self.preview_layout_button,
            self.open_export_folder_button,
            self.open_output_folder_button,
            self.new_project_button
        ]
        
        for button in buttons_to_disable:
            button.config(state='disabled')
    
    # Méthodes de menu (stubs pour l'instant)
    
    def _open_session_dialog(self):
        """Ouvre le dialogue de sélection de session"""
        messagebox.showinfo("Information", "Fonctionnalité à implémenter")
    
    def _export_session(self):
        """Exporte une session"""
        messagebox.showinfo("Information", "Fonctionnalité à implémenter")
    
    def _import_session(self):
        """Importe une session"""
        messagebox.showinfo("Information", "Fonctionnalité à implémenter")
    
    def _open_font_manager(self):
        """Ouvre le gestionnaire de polices"""
        messagebox.showinfo("Information", "Fonctionnalité à implémenter")
    
    def _open_preferences(self):
        """Ouvre les préférences"""
        messagebox.showinfo("Information", "Fonctionnalité à implémenter")
    
    def _show_user_guide(self):
        """Affiche le guide utilisateur"""
        messagebox.showinfo("Information", "Fonctionnalité à implémenter")
    
    def _show_about(self):
        """Affiche les informations de l'application"""
        about_text = """PDF Layout Translator v1.0.0

Application de traduction de documents PDF
avec préservation de la mise en page.

Développé par L'OréalGPT
© 2024 L'Oréal"""
        
        messagebox.showinfo("À propos", about_text)
    
    def _open_selected_session(self):
        """Ouvre la session sélectionnée"""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une session.")
            return
        
        # Récupérer l'ID de la session depuis les tags
        item = self.sessions_tree.item(selection[0])
        session_id = item['tags'][0] if item['tags'] else None
        
        if session_id and self.session_manager.load_session(session_id):
            self.current_session_id = session_id
            self._update_session_info()
            messagebox.showinfo("Succès", "Session chargée avec succès!")
        else:
            messagebox.showerror("Erreur", "Impossible de charger la session.")
    
    def _delete_selected_session(self):
        """Supprime la session sélectionnée"""
        selection = self.sessions_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une session.")
            return
        
        if messagebox.askyesno("Confirmation", "Êtes-vous sûr de vouloir supprimer cette session ?"):
            item = self.sessions_tree.item(selection[0])
            session_id = item['tags'][0] if item['tags'] else None
            
            if session_id and self.session_manager.delete_session(session_id):
                self._load_recent_sessions()
                messagebox.showinfo("Succès", "Session supprimée avec succès.")
            else:
                messagebox.showerror("Erreur", "Impossible de supprimer la session.")
    
    def _preview_layout(self):
        """Affiche un aperçu de la mise en page"""
        messagebox.showinfo("Aperçu", "Fonctionnalité d'aperçu à implémenter")
