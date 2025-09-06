#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Fenêtre principale
Interface graphique principale de l'application.

Auteur: L'OréalGPT
Version: 2.0.7 (Correction de la régression du FontDialog et des bugs de traduction)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import logging
from pathlib import Path
from typing import List, Dict
import json
import os
from dataclasses import asdict

from core.session_manager import SessionManager
from core.pdf_analyzer import PDFAnalyzer
from core.text_extractor import TextExtractor
from core.translation_parser import TranslationParser
from core.auto_translator import AutoTranslator, GOOGLETRANS_AVAILABLE
from utils.font_manager import FontManager
from core.layout_processor import LayoutProcessor
from core.pdf_reconstructor import PDFReconstructor
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo
from gui.font_dialog import FontDialog

class MainWindow:
    def __init__(self, root: tk.Tk, config_manager):
        self.root = root
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        
        self.session_manager = None
        self.font_manager = None
        self.pdf_analyzer = None
        self.text_extractor = None
        self.translation_parser = None
        self.auto_translator = None
        self.layout_processor = None
        self.pdf_reconstructor = None
        
        self.current_session_id = None
        self.processing = False
        
        self._setup_window()
        self._create_widgets()
        self._initialize_managers()
        
    def _setup_window(self):
        self.root.title("PDF Layout Translator v2.0.7")
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
            self.auto_translator = AutoTranslator()
            self.layout_processor = LayoutProcessor(self.font_manager)
            self.pdf_reconstructor = PDFReconstructor(self.font_manager)
            self.logger.info("Gestionnaires initialisés avec succès")
        except Exception as e:
            self.logger.error(f"Erreur d'initialisation: {e}", exc_info=True)
            messagebox.showerror("Erreur Critique", f"Erreur d'initialisation: {e}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self._create_header(main_frame)
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
        self.session_label = ttk.Label(header_frame, text="Aucune session")
        self.session_label.pack(side='right')

    def _create_home_tab(self):
        self.home_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.home_frame, text="🏠 Accueil")
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
        self.target_lang_var = tk.StringVar(value="fr")
        ttk.Combobox(lang_frame, textvariable=self.target_lang_var, values=["fr", "en", "es", "de", "it"], width=8).pack(side='left', padx=(10, 0))
        self.start_button = ttk.Button(new_project_frame, text="Démarrer l'analyse", command=self._start_new_project)
        self.start_button.pack(pady=(20, 0))

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
        instructions_text = "Option 1 (Automatique) : Cliquez sur 'Traduire Automatiquement'.\n" \
                            "Option 2 (Manuelle) : Cliquez sur 'Générer Fichier XLIFF', traduisez-le, puis collez le résultat ci-dessous.\n\n" \
                            "Enfin, cliquez sur 'Importer et Valider la Traduction'."
        ttk.Label(instructions_frame, text=instructions_text, justify='left').pack(anchor='w')
        actions_frame = ttk.Frame(self.translation_frame)
        actions_frame.pack(fill='x', padx=20, pady=(0, 20))
        self.auto_translate_button = ttk.Button(actions_frame, text="Traduire Automatiquement (Google)", command=self._auto_translate)
        self.auto_translate_button.pack(side='left', padx=(0, 10))
        ttk.Button(actions_frame, text="Générer Fichier de Traduction (XLIFF)", command=self._generate_translation_export).pack(side='left')
        self.open_export_folder_button = ttk.Button(actions_frame, text="Ouvrir le dossier de session", command=self._open_session_folder, state='disabled')
        self.open_export_folder_button.pack(side='left', padx=(10, 0))
        if not GOOGLETRANS_AVAILABLE:
            self.auto_translate_button.config(state='disabled')
            ToolTip(self.auto_translate_button, "Dépendances manquantes. Installez avec :\npip install googletrans==4.0.0-rc1 lxml")
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

    def _setup_debug_logger(self, session_id: str):
        session_dir = self.session_manager.get_session_directory(session_id)
        if session_dir:
            handler = logging.FileHandler(session_dir / "debug_session_trace.log", mode='w', encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
            if self.debug_logger.hasHandlers(): self.debug_logger.handlers.clear()
            self.debug_logger.addHandler(handler)
            self.debug_logger.setLevel(logging.INFO)
            self.debug_logger.propagate = False
            self.debug_logger.info(f"--- Début de la trace de débogage pour la session {session_id} ---")

    def _start_new_project(self):
        pdf_path = self.file_path_var.get()
        if not pdf_path: return messagebox.showwarning("Attention", "Veuillez sélectionner un fichier PDF.")
        try:
            session_id = self.session_manager.create_session(Path(pdf_path))
            self.current_session_id = session_id
            self._setup_debug_logger(session_id)
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
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                dom_path = session_dir / "1_dom_analysis.json"
                with open(dom_path, "w", encoding="utf-8") as f: json.dump([asdict(p) for p in page_objects], f, indent=2)
                self.debug_logger.info(f"Fichier de débogage '1_dom_analysis.json' sauvegardé.")
                self.root.after(0, self._post_analysis_step, page_objects)
            except Exception as e:
                self.logger.error(f"Erreur d'analyse: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur d'Analyse", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _post_analysis_step(self, page_objects: List[PageObject]):
        total_blocks = sum(len(p.text_blocks) for p in page_objects)
        total_spans = sum(len(b.spans) for p in page_objects for b in p.text_blocks)
        summary = f"Analyse terminée.\n- Pages: {len(page_objects)}\n- Blocs de texte: {total_blocks}\n- Segments de style (spans): {total_spans}"
        self.analysis_text.config(state='normal'); self.analysis_text.delete('1.0', tk.END); self.analysis_text.insert('1.0', summary); self.analysis_text.config(state='disabled')
        
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
                page_objects = self._load_dom_from_file(self.current_session_id, "1_dom_analysis.json")
                xliff_content = self.text_extractor.create_xliff(page_objects, self.source_lang_var.get(), self.target_lang_var.get())
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                xliff_path = session_dir / "2_xliff_to_translate.xliff"
                with open(xliff_path, "w", encoding="utf-8") as f: f.write(xliff_content)
                self.debug_logger.info(f"Fichier de débogage '2_xliff_to_translate.xliff' sauvegardé.")
                self.root.after(0, lambda: self.open_export_folder_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"Fichier '2_xliff_to_translate.xliff' créé dans le dossier de la session."))
            except Exception as e:
                self.logger.error(f"Erreur d'export XLIFF: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur d'Export", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()
    
    def _auto_translate(self):
        if not self.current_session_id: return messagebox.showerror("Erreur", "Aucune session active.")
        def thread_target():
            self._set_processing(True, "Lancement de la traduction automatique...")
            try:
                self.debug_logger.info("--- Début du processus de Traduction Automatique ---")
                
                self.debug_logger.info("Étape 1/4: Chargement du DOM...")
                page_objects = self._load_dom_from_file(self.current_session_id, "1_dom_analysis.json")
                
                self.debug_logger.info("Étape 2/4: Génération du XLIFF source...")
                xliff_content = self.text_extractor.create_xliff(page_objects, self.source_lang_var.get(), self.target_lang_var.get())
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                
                self.debug_logger.info(" -> Écriture du fichier de débogage '2_xliff_to_translate.xliff'...")
                with open(session_dir / "2_xliff_to_translate.xliff", "w", encoding="utf-8") as f: f.write(xliff_content)
                self.debug_logger.info(" -> Fichier sauvegardé.")

                self.debug_logger.info("Étape 3/4: Appel du service de traduction...")
                translated_xliff = self.auto_translator.translate_xliff_content(xliff_content, self.target_lang_var.get())
                self.debug_logger.info(f" -> Service de traduction terminé. Type de retour: {type(translated_xliff).__name__}.")

                # BLINDAGE : Vérifier explicitement si le retour est None AVANT d'écrire
                if translated_xliff is None:
                    raise ValueError("Le module de traduction a retourné une valeur None inattendue.")

                self.debug_logger.info(" -> Écriture du fichier de débogage '3_xliff_translated.xliff'...")
                with open(session_dir / "3_xliff_translated.xliff", "w", encoding="utf-8") as f: f.write(translated_xliff)
                self.debug_logger.info(" -> Fichier sauvegardé.")

                self.debug_logger.info("Étape 4/4: Affichage du résultat dans l'interface.")
                self.root.after(0, lambda: self.translation_input.delete('1.0', tk.END))
                self.root.after(0, lambda: self.translation_input.insert('1.0', translated_xliff))
                self.root.after(0, lambda: messagebox.showinfo("Succès", "Traduction automatique terminée et insérée dans le champ de texte."))
                self.debug_logger.info("--- Processus de Traduction Automatique terminé avec succès. ---")

            except Exception as e:
                self.logger.error(f"Erreur de traduction automatique: {e}", exc_info=True)
                self.debug_logger.error(f"--- ERREUR FATALE pendant la traduction automatique ---", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur de Traduction", str(e)))
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
                with open(session_dir / "4_parsed_translations.json", "w", encoding="utf-8") as f: json.dump(translations, f, indent=2)
                self.debug_logger.info(f"Fichier de débogage '4_parsed_translations.json' sauvegardé avec {len(translations)} éléments.")
                self.root.after(0, lambda: self.continue_to_layout_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"{len(translations)} traductions importées avec succès."))
            except Exception as e:
                self.logger.error(f"Erreur de validation: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur de Validation", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _process_layout(self):
        def thread_target():
            self._set_processing(True, "Calcul de la mise en page...")
            try:
                self.debug_logger.info("--- Début du Traitement de la Mise en Page ---")
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                self.debug_logger.info("Étape 1/3: Chargement des données (DOM original et traductions)...")
                page_objects = self._load_dom_from_file(self.current_session_id, "1_dom_analysis.json")
                with open(session_dir / "4_parsed_translations.json", "r", encoding="utf-8") as f:
                    translations = json.load(f)
                self.debug_logger.info("Étape 2/3: Préparation de la 'Version à Rendre'...")
                render_version = self._prepare_render_version(page_objects, translations)
                self.debug_logger.info("Étape 3/3: Lancement du calcul de reflow (LayoutProcessor)...")
                final_pages = self.layout_processor.process_pages(render_version)
                with open(session_dir / "5_final_layout.json", "w", encoding="utf-8") as f: json.dump([asdict(p) for p in final_pages], f, indent=2)
                self.debug_logger.info("Fichier de débogage '5_final_layout.json' sauvegardé.")
                self.root.after(0, lambda: self.layout_results_text.config(state='normal'))
                self.root.after(0, lambda: self.layout_results_text.delete('1.0', tk.END))
                self.root.after(0, lambda: self.layout_results_text.insert('1.0', "Calcul du reflow terminé. Prêt pour l'export."))
                self.root.after(0, lambda: self.layout_results_text.config(state='disabled'))
                self.root.after(0, lambda: self.continue_to_export_button.config(state='normal'))
            except Exception as e:
                self.logger.error(f"Erreur de mise en page: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur de Mise en Page", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()
        
# Dans PDF-Layout-Translator-main/src/gui/main_window.py

    def _prepare_render_version(self, pages: List[PageObject], translations: Dict[str, str]) -> List[PageObject]:
        import copy
        render_pages = copy.deepcopy(pages)
        for page in render_pages:
            for block in page.text_blocks:
                for span in block.spans:
                    # On applique la traduction à chaque span individuellement.
                    # Le texte original est remplacé par le texte traduit.
                    translated_text = translations.get(span.id)
                    if translated_text is not None and translated_text.strip():
                        span.text = translated_text
                    elif span.text.strip():
                        # Si pas de traduction, on garde le texte original pour ne pas créer de "trous"
                        pass
        self.debug_logger.info("'Version à Rendre' créée : le texte de chaque segment est maintenant final.")
        return render_pages

    def _export_pdf(self):
        output_filename = self.output_filename_var.get().strip()
        if not output_filename: return messagebox.showwarning("Attention", "Veuillez spécifier un nom de fichier.")
        def thread_target():
            self._set_processing(True, "Génération du PDF final...")
            try:
                final_pages = self._load_dom_from_file(self.current_session_id, "5_final_layout.json")
                session_info = self.session_manager.get_session_info(self.current_session_id)
                original_pdf_path = Path(session_info.original_pdf_path)
                output_path = original_pdf_path.parent / output_filename
                self.pdf_reconstructor.render_pages(final_pages, output_path)
                self._output_folder = output_path.parent
                self.root.after(0, lambda: self.open_output_folder_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"Le PDF final a été exporté avec succès:\n{output_path}"))
            except Exception as e:
                self.logger.error(f"Erreur d'export PDF: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur d'Export", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _load_dom_from_file(self, session_id: str, filename: str) -> List[PageObject]:
        session_dir = self.session_manager.get_session_directory(session_id)
        file_path = session_dir / filename
        with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
        pages = []
        for page_data in data:
            page_obj = PageObject(**{k:v for k,v in page_data.items() if k not in ['text_blocks', 'image_blocks']})
            if 'text_blocks' in page_data:
                for block_data in page_data['text_blocks']:
                    block_obj = TextBlock(**{k:v for k,v in block_data.items() if k != 'spans'})
                    for span_data in block_data['spans']:
                        font_info = FontInfo(**span_data['font'])
                        span_obj = TextSpan(**{k:v for k,v in span_data.items() if k != 'font'}, font=font_info)
                        block_obj.spans.append(span_obj)
                    page_obj.text_blocks.append(block_obj)
            pages.append(page_obj)
        return pages

    def _open_session_folder(self):
        if self.current_session_id:
            session_dir = self.session_manager.get_session_directory(self.current_session_id)
            if session_dir and session_dir.exists(): os.startfile(session_dir)

    def _open_output_folder(self):
        if hasattr(self, '_output_folder') and self._output_folder.exists(): os.startfile(self._output_folder)
        
    def _load_recent_sessions(self): pass
    def _open_selected_session(self): messagebox.showinfo("Info", "La reprise de session sera implémentée dans une future version.")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tooltip_window = None
        widget.bind("<Enter>", self.show_tooltip); widget.bind("<Leave>", self.hide_tooltip)
    def show_tooltip(self, event):
        if self.tooltip_window or not self.text: return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25; y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True); tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
    def hide_tooltip(self, event):
        if self.tooltip_window: self.tooltip_window.destroy()
        self.tooltip_window = None



