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
import os
import platform

# Imports des modules core
from core.session_manager import SessionManager, SessionStatus
from core.pdf_analyzer import PDFAnalyzer
from core.text_extractor import TextExtractor
from core.translation_parser import TranslationParser, ValidationLevel
from utils.font_manager import FontManager
from core.layout_processor import LayoutProcessor
from core.pdf_reconstructor import PDFReconstructor
from gui.font_dialog import FontDialog

class MainWindow:
    """Fenêtre principale de l'application"""
    
    def __init__(self, root: tk.Tk, config_manager):
        self.root = root
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        self.session_manager: Optional[SessionManager] = None
        self.pdf_analyzer: Optional[PDFAnalyzer] = None
        self.text_extractor: Optional[TextExtractor] = None
        self.translation_parser: Optional[TranslationParser] = None
        self.font_manager: Optional[FontManager] = None
        self.layout_processor: Optional[LayoutProcessor] = None
        self.pdf_reconstructor: Optional[PDFReconstructor] = None
        
        self.current_session_id: Optional[str] = None
        self.current_step = 0
        self.processing = False
        
        self._setup_window()
        self._create_widgets()
        self._initialize_managers()
        self._load_recent_sessions()
        
        self.logger.info("Interface principale initialisée")
    
    def _setup_window(self):
        self.root.title("PDF Layout Translator v1.0.0")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 10))
        
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (800 // 2)
        self.root.geometry(f"1200x800+{x}+{y}")
        
    def _create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self._create_header(main_frame)
        self._create_progress_bar(main_frame)
        
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(10, 0))
        
        self._create_home_tab()
        self._create_analysis_tab()
        self._create_translation_tab()
        self._create_layout_tab()
        self._create_export_tab()
        
        self._create_status_bar(main_frame)
        self._create_menu()
    
    def _create_header(self, parent):
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(header_frame, text="PDF Layout Translator", style='Title.TLabel').pack(side='left')
        
        self.session_label = ttk.Label(header_frame, text="Aucune session", style='Status.TLabel')
        self.session_label.pack(side='right')
    
    def _create_progress_bar(self, parent):
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(progress_frame, text="Progression:", style='Subtitle.TLabel').pack(side='left')
        
        self.global_progress = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.global_progress.pack(side='left', padx=(10, 0), fill='x', expand=True)
        
        self.progress_label = ttk.Label(progress_frame, text="Prêt", style='Status.TLabel')
        self.progress_label.pack(side='right', padx=(10, 0))

    def _create_home_tab(self):
        self.home_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.home_frame, text="🏠 Accueil")
        
        new_project_frame = ttk.LabelFrame(self.home_frame, text="Nouveau Projet", padding=20)
        new_project_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Label(new_project_frame, text="Sélectionnez un fichier PDF à traduire:", style='Subtitle.TLabel').pack(anchor='w')
        
        file_frame = ttk.Frame(new_project_frame)
        file_frame.pack(fill='x', pady=(10, 0))
        
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly')
        self.file_entry.pack(side='left', fill='x', expand=True)
        
        ttk.Button(file_frame, text="Parcourir...", command=self._browse_pdf_file).pack(side='right', padx=(10, 0))
        
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
        
        self.start_button = ttk.Button(new_project_frame, text="Démarrer l'analyse", 
                                      command=self._start_new_project)
        self.start_button.pack(pady=(20, 0))
        
        recent_frame = ttk.LabelFrame(self.home_frame, text="Sessions Récentes", padding=20)
        recent_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.sessions_tree = ttk.Treeview(recent_frame, columns=('date', 'status', 'progress'), show='tree headings')
        self.sessions_tree.heading('#0', text='Nom')
        self.sessions_tree.heading('date', text='Date')
        self.sessions_tree.heading('status', text='Statut')
        self.sessions_tree.heading('progress', text='Progrès')
        self.sessions_tree.pack(fill='both', expand=True)
        
        sessions_buttons_frame = ttk.Frame(recent_frame)
        sessions_buttons_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(sessions_buttons_frame, text="Ouvrir", command=self._open_selected_session).pack(side='left')
        ttk.Button(sessions_buttons_frame, text="Supprimer", command=self._delete_selected_session).pack(side='left', padx=(10, 0))
        ttk.Button(sessions_buttons_frame, text="Actualiser", command=self._load_recent_sessions).pack(side='right')
    
    def _create_analysis_tab(self):
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="🔍 Analyse")
        
        info_frame = ttk.LabelFrame(self.analysis_frame, text="Informations du Document", padding=20)
        info_frame.pack(fill='x', padx=20, pady=20)
        
        self.doc_info_text = scrolledtext.ScrolledText(info_frame, height=6, state='disabled')
        self.doc_info_text.pack(fill='x')
        
        results_frame = ttk.LabelFrame(self.analysis_frame, text="Résultats d'Analyse", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.analysis_text = scrolledtext.ScrolledText(results_frame, state='disabled')
        self.analysis_text.pack(fill='both', expand=True)
        
        buttons_frame = ttk.Frame(self.analysis_frame)
        buttons_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.analyze_button = ttk.Button(buttons_frame, text="Relancer l'Analyse", command=self._analyze_pdf)
        self.analyze_button.pack(side='left')
        
        self.continue_to_translation_button = ttk.Button(buttons_frame, text="Continuer vers Traduction", 
                                                        command=self._continue_to_translation, state='disabled')
        self.continue_to_translation_button.pack(side='right')
    
    def _create_translation_tab(self):
        self.translation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.translation_frame, text="🌐 Traduction")
        
        instructions_frame = ttk.LabelFrame(self.translation_frame, text="Instructions", padding=20)
        instructions_frame.pack(fill='x', padx=20, pady=20)
        
        instructions_text = """1. Cliquez sur "Générer Export" pour créer les fichiers de traduction...\n2. Utilisez votre IA préférée pour traduire...\n3. Copiez la traduction...\n4. Cliquez sur "Valider Traduction"..."""
        
        ttk.Label(instructions_frame, text=instructions_text, justify='left').pack(anchor='w')
        
        export_frame = ttk.Frame(self.translation_frame)
        export_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.generate_export_button = ttk.Button(export_frame, text="Générer Export pour Traduction", 
                                               command=self._generate_translation_export)
        self.generate_export_button.pack(side='left')
        
        self.open_export_folder_button = ttk.Button(export_frame, text="Ouvrir Dossier d'Export", 
                                                   command=self._open_export_folder, state='disabled')
        self.open_export_folder_button.pack(side='left', padx=(10, 0))
        
        input_frame = ttk.LabelFrame(self.translation_frame, text="Traduction de l'IA", padding=20)
        input_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.translation_input = scrolledtext.ScrolledText(input_frame, height=15)
        self.translation_input.pack(fill='both', expand=True)
        
        validation_frame = ttk.Frame(self.translation_frame)
        validation_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        self.validate_translation_button = ttk.Button(validation_frame, text="Valider Traduction", 
                                                     command=self._validate_translation)
        self.validate_translation_button.pack(side='left')
        
        ttk.Label(validation_frame, text="Niveau de validation:").pack(side='left', padx=(20, 0))
        self.validation_level_var = tk.StringVar(value="moderate")
        validation_combo = ttk.Combobox(validation_frame, textvariable=self.validation_level_var,
                                       values=["strict", "moderate", "permissive"], width=10)
        validation_combo.pack(side='left', padx=(10, 0))
        
        self.continue_to_layout_button = ttk.Button(validation_frame, text="Continuer vers Mise en Page", 
                                                   command=self._continue_to_layout, state='disabled')
        self.continue_to_layout_button.pack(side='right')

    def _create_layout_tab(self):
        self.layout_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.layout_frame, text="📐 Mise en Page")
        
        settings_frame = ttk.LabelFrame(self.layout_frame, text="Paramètres", padding=20)
        settings_frame.pack(fill='x', padx=20, pady=20)
        
        self.allow_font_reduction_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Autoriser la réduction de police", 
                       variable=self.allow_font_reduction_var).pack(anchor='w')
        
        self.allow_container_expansion_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Autoriser l'expansion des conteneurs", 
                       variable=self.allow_container_expansion_var).pack(anchor='w')
        
        results_frame = ttk.LabelFrame(self.layout_frame, text="Résultats de Mise en Page", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.layout_results_text = scrolledtext.ScrolledText(results_frame, state='disabled')
        self.layout_results_text.pack(fill='both', expand=True)
        
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
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="📤 Export")
        
        options_frame = ttk.LabelFrame(self.export_frame, text="Options d'Export", padding=20)
        options_frame.pack(fill='x', padx=20, pady=20)
        
        filename_frame = ttk.Frame(options_frame)
        filename_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(filename_frame, text="Nom de fichier:").pack(side='left')
        self.output_filename_var = tk.StringVar()
        ttk.Entry(filename_frame, textvariable=self.output_filename_var).pack(side='left', fill='x', expand=True, padx=(10, 0))
        
        self.create_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Créer une sauvegarde du fichier original", 
                       variable=self.create_backup_var).pack(anchor='w')
        
        self.create_comparison_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Créer un PDF de comparaison", 
                       variable=self.create_comparison_var).pack(anchor='w')
        
        self.optimize_output_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Optimiser le fichier de sortie", 
                       variable=self.optimize_output_var).pack(anchor='w')
        
        export_results_frame = ttk.LabelFrame(self.export_frame, text="Résultats d'Export", padding=20)
        export_results_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.export_results_text = scrolledtext.ScrolledText(export_results_frame, state='disabled')
        self.export_results_text.pack(fill='both', expand=True)
        
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
        status_frame = ttk.Frame(parent, relief='sunken', borderwidth=1)
        status_frame.pack(fill='x', side='bottom')
        
        self.status_label = ttk.Label(status_frame, text="Prêt", style='Status.TLabel')
        self.status_label.pack(side='left', padx=5, pady=2)
        
        self.processing_indicator = ttk.Progressbar(status_frame, length=100, mode='indeterminate')
        self.processing_indicator.pack(side='right', padx=5, pady=2)
    
    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Nouveau Projet...", command=self._new_project)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="À propos", command=self._show_about)

    def _initialize_managers(self):
        try:
            app_data_dir = self.config_manager.app_data_dir
            
            self.session_manager = SessionManager(app_data_dir)
            self.pdf_analyzer = PDFAnalyzer()
            self.text_extractor = TextExtractor()
            self.font_manager = FontManager(app_data_dir)
            self.layout_processor = LayoutProcessor(self.config_manager)
            self.pdf_reconstructor = PDFReconstructor(self.config_manager, self.font_manager)
            
            validation_level = ValidationLevel.MODERATE
            self.translation_parser = TranslationParser(validation_level)
            
            self.logger.info("Gestionnaires initialisés avec succès")
            
        except Exception as e:
            self.logger.error(f"Erreur init: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de l'initialisation: {e}")

    def _load_recent_sessions(self):
        if not self.session_manager:
            return
        
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        
        sessions = self.session_manager.list_sessions()
        
        for session in sessions[-10:]:
            try:
                date_obj = datetime.fromisoformat(session.last_modified)
                date_str = date_obj.strftime("%d/%m/%Y %H:%M")
            except:
                date_str = "Date inconnue"
            
            progress = int((session.translation_progress + session.review_progress) * 50)
            
            self.sessions_tree.insert('', 'end', 
                                    text=session.name,
                                    values=(date_str, session.status.value, f"{progress}%"),
                                    tags=(session.id,))
    
    def _browse_pdf_file(self):
        filename = filedialog.askopenfilename(
            title="Sélectionner un fichier PDF",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")]
        )
        
        if filename:
            self.file_path_var.set(filename)
            self.start_button.config(state='normal')
    
    def _start_new_project(self):
        pdf_path = self.file_path_var.get()
        if not pdf_path:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fichier PDF.")
            return
        
        try:
            session_id = self.session_manager.create_session(
                Path(pdf_path),
                source_lang=self.source_lang_var.get(),
                target_lang=self.target_lang_var.get()
            )
            
            self.current_session_id = session_id
            self._update_session_info()
            
            self.notebook.select(1)
            self._update_global_progress(1, "Session créée, démarrage de l'analyse...")
            
            self._analyze_pdf()
            
        except Exception as e:
            self.logger.error(f"Erreur création session: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la création de la session: {e}")
    
    def _analyze_pdf(self):
        if not self.current_session_id:
            messagebox.showwarning("Attention", "Aucune session active.")
            return
        
        def analyze_thread():
            try:
                self._set_processing(True, "Analyse du PDF en cours...")
                
                session_info = self.session_manager.get_session_info(self.current_session_id)
                pdf_path = Path(session_info.original_pdf_path)
                
                analysis_data = self.pdf_analyzer.analyze_pdf(pdf_path)
                
                self.session_manager.save_analysis_data(analysis_data, self.current_session_id)
                self.session_manager.update_session_status(SessionStatus.READY_FOR_TRANSLATION, self.current_session_id)
                
                self.root.after(0, self._post_analysis_step, analysis_data)
                
            except Exception as e:
                self.logger.error(f"Erreur analyse PDF: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur lors de l'analyse: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def _display_analysis_results(self, analysis_data: Dict[str, Any]):
        doc_info = analysis_data['document_info']
        info_text = f"Pages: {doc_info['page_count']}\nVersion PDF: {doc_info['pdf_version']}"
        
        self._update_text_widget(self.doc_info_text, info_text)
        
        stats = analysis_data['statistics']
        results_text = f"Éléments de texte: {stats['total_text_elements']}\nCaractères total: {stats['total_characters']}"
        
        self._update_text_widget(self.analysis_text, results_text)
        
        self.continue_to_translation_button.config(state='normal')
    
    def _continue_to_translation(self):
        self.notebook.select(2)
        self._update_global_progress(3, "Prêt pour la traduction")
    
    def _generate_translation_export(self):
        if not self.current_session_id: return
        
        def export_thread():
            try:
                self._set_processing(True, "Génération de l'export...")
                
                analysis_data = self.session_manager.load_analysis_data(self.current_session_id)
                if not analysis_data: raise ValueError("Données d'analyse non trouvées")
                
                extraction_data = self.text_extractor.extract_for_translation(analysis_data)
                
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                with open(session_dir / "extraction_data.json", 'w', encoding='utf-8') as f:
                    json.dump(extraction_data, f, indent=2, ensure_ascii=False)
                
                export_dir = session_dir / "exports"
                files_created = self.text_extractor.create_export_package(extraction_data, export_dir)
                
                self.root.after(0, lambda: self._show_export_success(export_dir, files_created))
            except Exception as e:
                self.logger.error(f"Erreur export: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=export_thread, daemon=True).start()

    def _validate_translation(self):
        translation_content = self.translation_input.get('1.0', tk.END).strip()
        if not translation_content: return
        
        def validate_thread():
            try:
                self._set_processing(True, "Validation...")
                
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                with open(session_dir / "extraction_data.json", 'r', encoding='utf-8') as f:
                    extraction_data = json.load(f)
                
                parse_report = self.translation_parser.parse_translated_content(translation_content, extraction_data)
                
                self.root.after(0, lambda: self._show_validation_results(parse_report))
                
                if parse_report.result.value in ['success', 'partial']:
                    validated_translations = self.translation_parser.export_validated_translations(parse_report)
                    with open(session_dir / "validated_translations.json", 'w', encoding='utf-8') as f:
                        json.dump(validated_translations, f, indent=2)
                    self.session_manager.update_session_status(SessionStatus.READY_FOR_LAYOUT, self.current_session_id)
                    self.root.after(0, lambda: self.continue_to_layout_button.config(state='normal'))
            except Exception as e:
                self.logger.error(f"Erreur validation: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=validate_thread, daemon=True).start()

    def _process_layout(self):
        if not self.current_session_id: return
        
        def layout_thread():
            try:
                self._set_processing(True, "Traitement de la mise en page...")
                
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                
                with open(session_dir / "analysis_data.json", 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                
                with open(session_dir / "validated_translations.json", 'r', encoding='utf-8') as f:
                    validated_translations = json.load(f)
                
                layout_result = self.layout_processor.process_layout(
                    validated_translations, analysis_data
                )
                
                with open(session_dir / "layout_result.json", 'w', encoding='utf-8') as f:
                    json.dump(layout_result, f, indent=2)
                
                self.root.after(0, lambda: self._display_layout_results(layout_result))
                self.session_manager.update_session_status(SessionStatus.READY_FOR_EXPORT, self.current_session_id)
                
            except Exception as e:
                self.logger.error(f"Erreur traitement layout: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=layout_thread, daemon=True).start()
    
    def _export_pdf(self):
        output_filename = self.output_filename_var.get().strip()
        if not output_filename: return
        
        def export_thread():
            try:
                self._set_processing(True, "Export en cours...")
                
                s_info = self.session_manager.get_session_info(self.current_session_id)
                s_dir = self.session_manager.get_session_directory(self.current_session_id)
                
                pdf_path = Path(s_info.original_pdf_path)
                out_path = pdf_path.parent / output_filename
                
                with open(s_dir / "layout_result.json", 'r', encoding='utf-8') as f: layout = json.load(f)
                with open(s_dir / "validated_translations.json", 'r', encoding='utf-8') as f: validated = json.load(f)
                
                result = self.pdf_reconstructor.reconstruct_pdf(pdf_path, layout, validated, out_path)
                
                self.root.after(0, lambda: self._show_export_results(result, out_path))
                
                if result.success: self.session_manager.update_session_status(SessionStatus.COMPLETED, self.current_session_id)
            except Exception as e:
                self.logger.error(f"Erreur export: {e}")
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur", f"Erreur: {e}"))
            finally:
                self._set_processing(False)
        
        threading.Thread(target=export_thread, daemon=True).start()

    def _open_selected_session(self):
        selection = self.sessions_tree.selection()
        if not selection: return
        item = self.sessions_tree.item(selection[0]); session_id = item['tags'][0]
        if not (session_id and self.session_manager.load_session(session_id)):
            messagebox.showerror("Erreur", "Impossible de charger la session."); return
        self.current_session_id = session_id; self._update_session_info(); messagebox.showinfo("Succès", "Session chargée ! Reprise du travail...")
        session_info = self.session_manager.get_session_info(session_id); session_dir = self.session_manager.get_session_directory(session_id); status = session_info.status
        try:
            analysis_data = self.session_manager.load_analysis_data(session_id)
            if analysis_data: self._display_analysis_results(analysis_data)
            
            if status in [SessionStatus.READY_FOR_TRANSLATION, SessionStatus.TRANSLATING, SessionStatus.READY_FOR_REVIEW, SessionStatus.REVIEWING]:
                self.notebook.select(2); self._update_global_progress(3, "Prêt pour la traduction")
            elif status in [SessionStatus.READY_FOR_LAYOUT, SessionStatus.PROCESSING_LAYOUT]:
                 self.continue_to_layout_button.config(state='normal'); self.notebook.select(3); self._update_global_progress(4, "Prêt pour la mise en page")
            elif status in [SessionStatus.READY_FOR_EXPORT, SessionStatus.COMPLETED]:
                 layout_result_path = session_dir / "layout_result.json"
                 if layout_result_path.exists():
                     with open(layout_result_path, 'r', encoding='utf-8') as f: self._display_layout_results(json.load(f))
                 self.notebook.select(4); self._update_global_progress(5, "Prêt pour l'export"); self._set_suggested_output_filename()
            else: self.notebook.select(1)
        except Exception as e:
            self.logger.error(f"Erreur lors de la reprise de session: {e}"); messagebox.showerror("Erreur de Reprise", f"Impossible de restaurer l'état: {e}"); self.notebook.select(0)

    def _set_suggested_output_filename(self):
        if self.current_session_id:
            s_info = self.session_manager.get_session_info(self.current_session_id)
            if s_info: self.output_filename_var.set(f"{Path(s_info.original_pdf_name).stem}_traduit.pdf")

    def _show_export_success(self, export_dir, files_created): messagebox.showinfo("Export Généré", f"Export généré avec succès dans:\n{export_dir}")
    def _open_export_folder(self):
        if hasattr(self, '_export_folder'):
            if platform.system() == "Windows": os.startfile(self._export_folder)
            else: os.system(f'open "{self._export_folder}"')
    def _show_validation_results(self, report): messagebox.showinfo("Validation", f"{report.result.value.capitalize()}: {report.parsed_elements}/{report.total_elements} éléments traités.")
    def _continue_to_layout(self): self.notebook.select(3); self._update_global_progress(4, "Prêt pour mise en page")
    def _display_layout_results(self, result): self._update_text_widget(self.layout_results_text, f"Qualité: {result['quality_metrics']['quality_level']}"); self.continue_to_export_button.config(state='normal')
    def _continue_to_export(self): self.notebook.select(4); self._update_global_progress(5, "Prêt pour l'export"); self._set_suggested_output_filename()
    
    def _show_export_results(self, result, path):
        if result.success:
            message = f"Rapport: {result.elements_processed} éléments traités, {result.elements_ignored} ignorés."
            if result.warnings:
                message += f"\n\nAvertissements:\n" + "\n".join(result.warnings[:3])
            self._update_text_widget(self.export_results_text, f"{message}\nFichier: {path}")
            self.new_project_button.config(state='normal')
        else:
            self._update_text_widget(self.export_results_text, f"ÉCHEC DE L'EXPORT.\nErreur: {result.errors[0]}")

    def _new_project(self): self.current_session_id=None; self.notebook.select(0); self._update_global_progress(0, "Prêt"); self._reset_interface(); self._load_recent_sessions()
    def _update_session_info(self): self.session_label.config(text=f"Session: {self.session_manager.get_session_info(self.current_session_id).name}" if self.current_session_id else "Aucune session")
    def _update_global_progress(self, step, status): self.global_progress['value'] = (step/5)*100; self.progress_label.config(text=status)
    def _set_processing(self, state, status=""): self.status_label.config(text=status if state else "Prêt"); self.processing_indicator.start() if state else self.processing_indicator.stop()
    def _update_text_widget(self, widget, text): widget.config(state='normal'); widget.delete('1.0', tk.END); widget.insert('1.0', text); widget.config(state='disabled')
    def _reset_interface(self): self.file_path_var.set(''); self.translation_input.delete('1.0', tk.END); self.output_filename_var.set(''); [btn.config(state='disabled') for btn in [self.continue_to_translation_button, self.continue_to_layout_button, self.continue_to_export_button, self.new_project_button]]
    def _show_about(self): messagebox.showinfo("À propos", "PDF Layout Translator v1.0.0")
    def _delete_selected_session(self):
        if not self.sessions_tree.selection(): return
        if messagebox.askyesno("Confirmation", "Supprimer cette session ?"):
            session_id = self.sessions_tree.item(self.sessions_tree.selection()[0])['tags'][0]
            if self.session_manager.delete_session(session_id): self._load_recent_sessions()
    
    def _preview_layout(self):
        messagebox.showinfo("Info", "Pas encore implémenté")
