#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Fenêtre principale
Interface graphique principale de l'application.

Auteur: L'OréalGPT
Version: 2.0.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
from dataclasses import asdict

# Imports de la nouvelle architecture
from core.session_manager import SessionManager, SessionStatus
from core.pdf_analyzer import PDFAnalyzer
from core.text_extractor import TextExtractor
from core.translation_parser import TranslationParser
from utils.font_manager import FontManager
from core.layout_processor import LayoutProcessor
from core.pdf_reconstructor import PDFReconstructor
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo
from gui.font_dialog import FontDialog

class MainWindow:
    """Fenêtre principale de l'application"""
    
    def __init__(self, root: tk.Tk, config_manager):
        self.root = root
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialisation des managers
        self.session_manager: Optional[SessionManager] = None
        self.font_manager: Optional[FontManager] = None
        self.pdf_analyzer: Optional[PDFAnalyzer] = None
        self.text_extractor: Optional[TextExtractor] = None
        self.translation_parser: Optional[TranslationParser] = None
        self.layout_processor: Optional[LayoutProcessor] = None
        self.pdf_reconstructor: Optional[PDFReconstructor] = None
        
        self.current_session_id: Optional[str] = None
        self.processing = False
        
        self._setup_window()
        self._create_widgets()
        self._initialize_managers()
        self._load_recent_sessions()
        
        self.logger.info("Interface principale v2 initialisée")
    
    def _setup_window(self):
        self.root.title("PDF Layout Translator v2.0.0")
        self.root.geometry("1200x800")
        self.root.minsize(900, 700)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))

    def _initialize_managers(self):
        try:
            app_data_dir = self.config_manager.app_data_dir
            self.session_manager = SessionManager(app_data_dir)
            self.font_manager = FontManager(app_data_dir)
            self.pdf_analyzer = PDFAnalyzer()
            self.text_extractor = TextExtractor()
            self.translation_parser = TranslationParser()
            self.layout_processor = LayoutProcessor(self.font_manager)
            self.pdf_reconstructor = PDFReconstructor(self.font_manager)
            self.logger.info("Gestionnaires de l'architecture v2 initialisés avec succès")
        except Exception as e:
            self.logger.error(f"Erreur d'initialisation des managers: {e}", exc_info=True)
            messagebox.showerror("Erreur Critique", f"Erreur lors de l'initialisation des managers: {e}")

    def _create_widgets(self):
        # La création des widgets reste similaire visuellement
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self._create_header(main_frame)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(10, 0))
        self._create_home_tab()
        self._create_analysis_tab()
        self._create_translation_tab() # Sera mise à jour avec les nouvelles instructions
        self._create_layout_tab()
        self._create_export_tab()
        self._create_status_bar(main_frame)
        self._create_menu()

    def _create_header(self, parent):
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(header_frame, text="PDF Layout Translator", style='Title.TLabel').pack(side='left')
        self.session_label = ttk.Label(header_frame, text="Aucune session")
        self.session_label.pack(side='right')

    def _create_home_tab(self):
        self.home_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.home_frame, text="🏠 Accueil")
        # Le contenu de cet onglet reste le même que précédemment
        new_project_frame = ttk.LabelFrame(self.home_frame, text="Nouveau Projet", padding=20)
        new_project_frame.pack(fill='x', padx=20, pady=20)
        ttk.Label(new_project_frame, text="Sélectionnez un fichier PDF à traduire:").pack(anchor='w')
        file_frame = ttk.Frame(new_project_frame)
        file_frame.pack(fill='x', pady=(10, 0))
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly').pack(side='left', fill='x', expand=True)
        ttk.Button(file_frame, text="Parcourir...", command=self._browse_pdf_file).pack(side='right', padx=(10, 0))
        lang_frame = ttk.Frame(new_project_frame)
        lang_frame.pack(fill='x', pady=(20, 0))
        ttk.Label(lang_frame, text="Langue source:").pack(side='left')
        self.source_lang_var = tk.StringVar(value="en")
        ttk.Combobox(lang_frame, textvariable=self.source_lang_var, values=["en", "fr", "es", "de", "it"], width=8).pack(side='left', padx=(10, 0))
        ttk.Label(lang_frame, text="Langue cible:").pack(side='left', padx=(20, 0))
        self.target_lang_var = tk.StringVar(value="fr") # Par défaut fr
        ttk.Combobox(lang_frame, textvariable=self.target_lang_var, values=["fr", "en", "es", "de", "it"], width=8).pack(side='left', padx=(10, 0))
        self.start_button = ttk.Button(new_project_frame, text="Démarrer l'analyse", command=self._start_new_project)
        self.start_button.pack(pady=(20, 0))
        recent_frame = ttk.LabelFrame(self.home_frame, text="Sessions Récentes", padding=20)
        recent_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        self.sessions_tree = ttk.Treeview(recent_frame, columns=('date', 'status'), show='tree headings')
        self.sessions_tree.heading('#0', text='Nom'); self.sessions_tree.heading('date', text='Date'); self.sessions_tree.heading('status', text='Statut')
        self.sessions_tree.pack(fill='both', expand=True)
        ttk.Button(recent_frame, text="Ouvrir", command=self._open_selected_session).pack(side='left', pady=(10,0))

    def _create_analysis_tab(self):
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="🔍 Analyse")
        results_frame = ttk.LabelFrame(self.analysis_frame, text="Résultats d'Analyse", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=20)
        self.analysis_text = scrolledtext.ScrolledText(results_frame, state='disabled', height=10)
        self.analysis_text.pack(fill='both', expand=True)
        self.continue_to_translation_button = ttk.Button(self.analysis_frame, text="Continuer vers Traduction", command=lambda: self.notebook.select(2), state='disabled')
        self.continue_to_translation_button.pack(padx=20, pady=10)

    def _create_translation_tab(self):
        self.translation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.translation_frame, text="🌐 Traduction")
        
        instructions_frame = ttk.LabelFrame(self.translation_frame, text="Instructions", padding=20)
        instructions_frame.pack(fill='x', padx=20, pady=20)
        instructions_text = "1. Cliquez sur 'Générer Fichier de Traduction (XLIFF)' pour créer le fichier à traduire.\n" \
                            "2. Ouvrez ce fichier avec un éditeur de texte ou un outil de TAO et remplissez les balises <target>.\n" \
                            "3. Collez le contenu du fichier XLIFF traduit ci-dessous.\n" \
                            "4. Cliquez sur 'Importer et Valider la Traduction'."
        ttk.Label(instructions_frame, text=instructions_text, justify='left').pack(anchor='w')

        export_frame = ttk.Frame(self.translation_frame)
        export_frame.pack(fill='x', padx=20, pady=(0, 20))
        ttk.Button(export_frame, text="Générer Fichier de Traduction (XLIFF)", command=self._generate_translation_export).pack(side='left')
        self.open_export_folder_button = ttk.Button(export_frame, text="Ouvrir le dossier", command=self._open_export_folder, state='disabled')
        self.open_export_folder_button.pack(side='left', padx=(10, 0))

        input_frame = ttk.LabelFrame(self.translation_frame, text="Coller le contenu du XLIFF traduit ici", padding=20)
        input_frame.pack(fill='both', expand=True, padx=20, pady=0)
        self.translation_input = scrolledtext.ScrolledText(input_frame)
        self.translation_input.pack(fill='both', expand=True)

        self.validate_translation_button = ttk.Button(self.translation_frame, text="Importer et Valider la Traduction", command=self._validate_translation)
        self.validate_translation_button.pack(padx=20, pady=10)
        self.continue_to_layout_button = ttk.Button(self.translation_frame, text="Continuer vers Mise en Page", command=lambda: self.notebook.select(3), state='disabled')
        self.continue_to_layout_button.pack(padx=20, pady=10)

    def _create_layout_tab(self):
        self.layout_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.layout_frame, text="📐 Mise en Page")
        ttk.Button(self.layout_frame, text="Calculer la Mise en Page (Reflow)", command=self._process_layout).pack(padx=20, pady=20)
        results_frame = ttk.LabelFrame(self.layout_frame, text="Rapport de Mise en Page", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=20)
        self.layout_results_text = scrolledtext.ScrolledText(results_frame, state='disabled')
        self.layout_results_text.pack(fill='both', expand=True)
        self.continue_to_export_button = ttk.Button(self.layout_frame, text="Continuer vers Export", command=lambda: self.notebook.select(4), state='disabled')
        self.continue_to_export_button.pack(padx=20, pady=10)

    def _create_export_tab(self):
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="📤 Export")
        filename_frame = ttk.Frame(self.export_frame, padding=20)
        filename_frame.pack(fill='x')
        ttk.Label(filename_frame, text="Nom de fichier de sortie:").pack(side='left')
        self.output_filename_var = tk.StringVar()
        ttk.Entry(filename_frame, textvariable=self.output_filename_var).pack(side='left', fill='x', expand=True, padx=(10, 0))
        self.export_pdf_button = ttk.Button(self.export_frame, text="Exporter le PDF Final", command=self._export_pdf)
        self.export_pdf_button.pack(padx=20, pady=20)
        self.open_output_folder_button = ttk.Button(self.export_frame, text="Ouvrir le dossier de sortie", command=self._open_output_folder, state='disabled')
        self.open_output_folder_button.pack(padx=20, pady=10)

    def _create_status_bar(self, parent):
        status_frame = ttk.Frame(parent, relief='sunken', borderwidth=1)
        status_frame.pack(fill='x', side='bottom')
        self.status_label = ttk.Label(status_frame, text="Prêt")
        self.status_label.pack(side='left', padx=5, pady=2)
        self.processing_indicator = ttk.Progressbar(status_frame, length=100, mode='indeterminate')
        self.processing_indicator.pack(side='right', padx=5, pady=2)

    def _create_menu(self):
        # Le menu reste le même
        pass

    def _browse_pdf_file(self):
        filename = filedialog.askopenfilename(title="Sélectionner un fichier PDF", filetypes=[("Fichiers PDF", "*.pdf")])
        if filename: self.file_path_var.set(filename)

    def _set_processing(self, is_processing, status_text=""):
        self.processing = is_processing
        if is_processing:
            self.status_label.config(text=status_text)
            self.processing_indicator.start()
        else:
            self.status_label.config(text="Prêt")
            self.processing_indicator.stop()

    # --- NOUVELLE CHAÎNE DE TRAITEMENT ---

    def _start_new_project(self):
        pdf_path = self.file_path_var.get()
        if not pdf_path: return messagebox.showwarning("Attention", "Veuillez sélectionner un fichier PDF.")
        try:
            session_id = self.session_manager.create_session(Path(pdf_path))
            self.current_session_id = session_id
            self.session_label.config(text=f"Session: {Path(pdf_path).name}")
            self.notebook.select(1)
            self._analyze_pdf()
        except Exception as e:
            self.logger.error(f"Erreur création session: {e}", exc_info=True)
            messagebox.showerror("Erreur", f"Erreur lors de la création de la session: {e}")

    def _analyze_pdf(self):
        def thread_target():
            self._set_processing(True, "Analyse du PDF en cours...")
            try:
                session_info = self.session_manager.get_session_info(self.current_session_id)
                pdf_path = Path(session_info.original_pdf_path)
                page_objects = self.pdf_analyzer.analyze_pdf(pdf_path)
                
                # Sauvegarder le DOM
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                with open(session_dir / "dom_analysis.json", "w", encoding="utf-8") as f:
                    json.dump([asdict(p) for p in page_objects], f, indent=2)

                self.root.after(0, self._post_analysis_step, page_objects)
            except Exception as e:
                self.logger.error(f"Erreur d'analyse: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror("Erreur d'Analyse", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _post_analysis_step(self, page_objects: List[PageObject]):
        # Afficher le résumé
        total_blocks = sum(len(p.text_blocks) for p in page_objects)
        total_spans = sum(len(b.spans) for p in page_objects for b in p.text_blocks)
        summary = f"Analyse terminée.\n- Pages: {len(page_objects)}\n- Blocs de texte: {total_blocks}\n- Segments de style (spans): {total_spans}"
        self.analysis_text.config(state='normal')
        self.analysis_text.delete('1.0', tk.END)
        self.analysis_text.insert('1.0', summary)
        self.analysis_text.config(state='disabled')

        # Gérer les polices
        required_fonts = {span.font.name for page in page_objects for block in page.text_blocks for span in block.spans}
        font_report = self.font_manager.check_fonts_availability(list(required_fonts))
        if not font_report['all_available']:
            FontDialog(self.root, self.font_manager, font_report).show()

        self.continue_to_translation_button.config(state='normal')
        self.notebook.select(1)

    def _generate_translation_export(self):
        def thread_target():
            self._set_processing(True, "Génération du fichier XLIFF...")
            try:
                page_objects = self._load_dom_from_file(self.current_session_id, "dom_analysis.json")
                xliff_content = self.text_extractor.create_xliff(page_objects, self.source_lang_var.get(), self.target_lang_var.get())
                
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                export_dir = session_dir / "export"
                export_dir.mkdir(exist_ok=True)
                xliff_path = export_dir / "translation.xliff"
                with open(xliff_path, "w", encoding="utf-8") as f:
                    f.write(xliff_content)

                self._export_folder = export_dir
                self.root.after(0, lambda: self.open_export_folder_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"Fichier 'translation.xliff' créé dans le dossier de la session."))
            except Exception as e:
                self.logger.error(f"Erreur d'export XLIFF: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror("Erreur d'Export", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _validate_translation(self):
        xliff_content = self.translation_input.get('1.0', tk.END).strip()
        if not xliff_content: return messagebox.showwarning("Attention", "Le champ de traduction est vide.")
        
        def thread_target():
            self._set_processing(True, "Importation des traductions...")
            try:
                translations = self.translation_parser.parse_xliff(xliff_content)
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                with open(session_dir / "parsed_translations.json", "w", encoding="utf-8") as f:
                    json.dump(translations, f, indent=2)

                self.root.after(0, lambda: self.continue_to_layout_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"{len(translations)} traductions importées avec succès."))
            except Exception as e:
                self.logger.error(f"Erreur de validation: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror("Erreur de Validation", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _process_layout(self):
        def thread_target():
            self._set_processing(True, "Calcul de la mise en page...")
            try:
                page_objects = self._load_dom_from_file(self.current_session_id, "dom_analysis.json")
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                with open(session_dir / "parsed_translations.json", "r", encoding="utf-8") as f:
                    translations = json.load(f)

                final_pages = self.layout_processor.process_pages(page_objects, translations)

                with open(session_dir / "final_layout.json", "w", encoding="utf-8") as f:
                    json.dump([asdict(p) for p in final_pages], f, indent=2)
                
                self.root.after(0, lambda: self.layout_results_text.config(state='normal'))
                self.root.after(0, lambda: self.layout_results_text.insert('1.0', "Calcul du reflow terminé. Prêt pour l'export."))
                self.root.after(0, lambda: self.layout_results_text.config(state='disabled'))
                self.root.after(0, lambda: self.continue_to_export_button.config(state='normal'))
            except Exception as e:
                self.logger.error(f"Erreur de mise en page: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror("Erreur de Mise en Page", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _export_pdf(self):
        output_filename = self.output_filename_var.get().strip()
        if not output_filename: return messagebox.showwarning("Attention", "Veuillez spécifier un nom de fichier.")

        def thread_target():
            self._set_processing(True, "Génération du PDF final...")
            try:
                final_pages = self._load_dom_from_file(self.current_session_id, "final_layout.json")
                session_info = self.session_manager.get_session_info(self.current_session_id)
                original_pdf_path = Path(session_info.original_pdf_path)
                output_path = original_pdf_path.parent / output_filename
                
                self.pdf_reconstructor.render_pages(final_pages, output_path)

                self._output_folder = output_path.parent
                self.root.after(0, lambda: self.open_output_folder_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"Le PDF final a été exporté avec succès:\n{output_path}"))
            except Exception as e:
                self.logger.error(f"Erreur d'export PDF: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror("Erreur d'Export", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    # --- Fonctions utilitaires ---

    def _load_dom_from_file(self, session_id: str, filename: str) -> List[PageObject]:
        """Charge et reconstruit la liste de PageObject à partir d'un fichier JSON."""
        session_dir = self.session_manager.get_session_directory(session_id)
        file_path = session_dir / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        pages = []
        for page_data in data:
            page_obj = PageObject(**{k:v for k,v in page_data.items() if k != 'text_blocks'})
            for block_data in page_data['text_blocks']:
                block_obj = TextBlock(**{k:v for k,v in block_data.items() if k != 'spans'})
                for span_data in block_data['spans']:
                    font_info = FontInfo(**span_data['font'])
                    span_obj = TextSpan(**{k:v for k,v in span_data.items() if k != 'font'}, font=font_info)
                    block_obj.spans.append(span_obj)
                page_obj.text_blocks.append(block_obj)
            pages.append(page_obj)
        return pages

    def _open_export_folder(self):
        if hasattr(self, '_export_folder') and self._export_folder.exists():
            os.startfile(self._export_folder)

    def _open_output_folder(self):
        if hasattr(self, '_output_folder') and self._output_folder.exists():
            os.startfile(self._output_folder)

    # --- Fonctions de session (simplifiées) ---
    def _load_recent_sessions(self):
        # A implémenter si nécessaire
        pass
    def _open_selected_session(self):
        # A implémenter si nécessaire, plus complexe avec la nouvelle architecture
        messagebox.showinfo("Info", "La reprise de session sera implémentée dans une future version.")
