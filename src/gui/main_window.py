#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Fenêtre principale
*** VERSION v2.7.0 - Refactoring du flux IA pour la robustesse ***
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import logging
from pathlib import Path
import json
import os
from dataclasses import asdict
from lxml import etree
import copy
from typing import List, Dict

from core.session_manager import SessionManager
from core.pdf_analyzer import PDFAnalyzer
from core.text_extractor import TextExtractor
from core.translation_parser import TranslationParser
from core.auto_translator import AutoTranslator, GOOGLETRANS_AVAILABLE
from utils.font_manager import FontManager
from core.layout_processor import LayoutProcessor
from core.pdf_reconstructor import PDFReconstructor
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo, Paragraph
from gui.font_dialog import FontDialog

# NOUVEAU : Le prompt de l'IA est maintenant géré par le programme
AI_GROUPING_PROMPT = """Votre Rôle :
Vous êtes un expert en analyse de la structure sémantique de documents. Votre unique mission est d'analyser une structure de blocs de texte bruts issue d'un PDF, décrite en JSON, et de déterminer quels blocs doivent être fusionnés pour former des unités logiques (paragraphes, titres, etc.).

[CONTEXTE]
Je vais vous fournir un JSON représentant les blocs de texte bruts d'un document (`text_blocks`). Chaque bloc possède un `id` unique, des coordonnées `bbox` ([x0, y0, x2, y2]), et du contenu textuel.

[MISSION]
En analysant la disposition spatiale (`bbox`), le style et le contenu des blocs, identifiez les groupes de blocs qui doivent être fusionnés.

Pensez aux règles suivantes pour guider votre décision :
- Proximité Verticale : Des blocs très proches verticalement font probablement partie du même paragraphe. Un grand espace vertical suggère une séparation.
- Continuité Logique : Une phrase qui se termine dans un bloc et continue dans le suivant est un candidat évident à la fusion.
- Éléments Distincts : Les titres, les puces de listes, ou les blocs avec un style très différent doivent généralement rester séparés et initier un nouveau groupe.

[FORMAT DE SORTIE]
Votre réponse doit être un unique bloc de code JSON. Ce JSON doit contenir une seule clé de haut niveau : `grouping_instructions`.

La valeur de `grouping_instructions` est une liste. Chaque élément de cette liste est un objet représentant un groupe de blocs à fusionner, avec deux clés :
1.  `ids_to_merge`: Une liste de chaînes de caractères contenant les `id` des blocs à fusionner, dans l'ordre de lecture.
2.  `reason`: Une courte phrase en anglais expliquant pourquoi vous avez décidé de les fusionner (ex: "Continuous paragraph flow", "Title block", "List item").

Si un bloc ne doit être fusionné avec aucun autre, ne l'incluez simplement dans aucune liste `ids_to_merge`.

Exemple de sortie attendue :
```json
{
  "grouping_instructions": [
    {
      "ids_to_merge": ["P1_B2", "P1_B3", "P1_B4"],
      "reason": "These blocks form a single continuous paragraph."
    },
    {
      "ids_to_merge": ["P1_B6", "P1_B7"],
      "reason": "Continuation of a sentence across two blocks."
    }
  ]
}
```

[DONNÉES D'ENTRÉE]
Voici le JSON brut (fichier 0) à traiter :
"""

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
        self.raw_page_objects: List[PageObject] = [] # Pour stocker les données brutes
        
        self.use_ai_flow_var = tk.BooleanVar(value=False)
        
        self._setup_window()
        self._create_widgets()
        self._initialize_managers()
        
    def _setup_window(self):
        self.root.title("PDF Layout Translator v2.7.0")
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
        self._create_ai_interaction_tab()
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
        
        ai_flow_checkbox = ttk.Checkbutton(
            new_project_frame,
            text="Utiliser une IA pour le regroupement sémantique (mode avancé)",
            variable=self.use_ai_flow_var
        )
        ai_flow_checkbox.pack(pady=(15, 0), anchor='w')
        ToolTip(ai_flow_checkbox, "Cochez cette case pour utiliser une IA externe (ex: Gemini, ChatGPT)\n"
                                "afin de déterminer comment regrouper les blocs de texte.")

        self.start_button = ttk.Button(new_project_frame, text="Démarrer l'analyse", command=self._start_new_project)
        self.start_button.pack(pady=(20, 0))

    def _create_analysis_tab(self):
        self.analysis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analysis_frame, text="🔍 Analyse")
        results_frame = ttk.LabelFrame(self.analysis_frame, text="Résultats d'Analyse", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=20)
        self.analysis_text = scrolledtext.ScrolledText(results_frame, state='disabled', height=10)
        self.analysis_text.pack(fill='both', expand=True)
        self.continue_to_translation_button = ttk.Button(self.analysis_frame, text="Continuer vers Traduction", command=lambda: self.notebook.select(self.translation_frame), state='disabled')
        self.continue_to_translation_button.pack(padx=20, pady=10)

    def _create_ai_interaction_tab(self):
        self.ai_frame = ttk.Frame(self.notebook)
        self.notebook.insert(2, self.ai_frame, text="🤖 Interaction IA")

        main_paned = ttk.PanedWindow(self.ai_frame, orient=tk.VERTICAL)
        main_paned.pack(fill='both', expand=True, padx=10, pady=10)

        # Frame du haut : Prompt + Données
        top_frame = ttk.Frame(main_paned)
        main_paned.add(top_frame, weight=3)
        
        prompt_frame = ttk.LabelFrame(top_frame, text="Étape 1 : Prompt à utiliser avec les données", padding=10)
        prompt_frame.pack(fill='both', expand=True, pady=(0, 10))
        self.ai_prompt_text = scrolledtext.ScrolledText(prompt_frame, height=8, wrap='word', relief='flat', background=self.root.cget('bg'))
        self.ai_prompt_text.insert('1.0', AI_GROUPING_PROMPT)
        self.ai_prompt_text.config(state='disabled')
        self.ai_prompt_text.pack(fill='both', expand=True)
        ttk.Button(prompt_frame, text="Copier le Prompt", command=self._copy_prompt_to_clipboard).pack(pady=(5,0))

        input_frame = ttk.LabelFrame(top_frame, text="Étape 2 : Données brutes (Fichier 0) à joindre au prompt", padding=10)
        input_frame.pack(fill='both', expand=True)
        self.ai_input_text = scrolledtext.ScrolledText(input_frame, height=10, wrap='word')
        self.ai_input_text.pack(fill='both', expand=True)

        # Frame du bas : Réponse de l'IA
        bottom_frame = ttk.Frame(main_paned)
        main_paned.add(bottom_frame, weight=2)
        
        output_frame = ttk.LabelFrame(bottom_frame, text="Étape 3 : Collez ici les instructions de regroupement (JSON) de l'IA", padding=10)
        output_frame.pack(fill='both', expand=True)
        self.ai_output_text = scrolledtext.ScrolledText(output_frame, height=10, wrap='word')
        self.ai_output_text.pack(fill='both', expand=True)
        
        process_button = ttk.Button(self.ai_frame, text="Traiter les instructions de l'IA et Générer les Fichiers", command=self._process_gemini_output)
        process_button.pack(pady=10, padx=10)

        self.notebook.hide(self.ai_frame)
    
    def _copy_prompt_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(AI_GROUPING_PROMPT)
        self.status_label.config(text="Prompt copié dans le presse-papiers.")

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
        self.continue_to_layout_button = ttk.Button(self.translation_frame, text="Continuer vers Mise en Page", command=lambda: self.notebook.select(self.layout_frame), state='disabled')
        self.continue_to_layout_button.pack(padx=20, pady=10)

    def _create_layout_tab(self):
        self.layout_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.layout_frame, text="📐 Mise en Page")
        ttk.Button(self.layout_frame, text="Calculer la Mise en Page (Reflow)", command=self._process_layout).pack(padx=20, pady=20)
        results_frame = ttk.LabelFrame(self.layout_frame, text="Rapport de Mise en Page", padding=20)
        results_frame.pack(fill='both', expand=True, padx=20, pady=20)
        self.layout_results_text = scrolledtext.ScrolledText(results_frame, state='disabled')
        self.layout_results_text.pack(fill='both', expand=True)
        self.continue_to_export_button = ttk.Button(self.layout_frame, text="Continuer vers Export", command=lambda: self.notebook.select(self.export_frame), state='disabled')
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
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
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
            self.notebook.hide(self.ai_frame)
            self.notebook.select(self.analysis_frame)
            self._analyze_pdf()
        except Exception as e:
            self.logger.error(f"Erreur création session: {e}", exc_info=True)
            messagebox.showerror("Erreur", f"Erreur lors de la création de la session: {e}")

    def _analyze_pdf(self):
        def thread_target():
            if self.use_ai_flow_var.get():
                self._set_processing(True, "Analyse brute du PDF pour l'IA...")
                try:
                    session_info = self.session_manager.get_session_info(self.current_session_id)
                    pdf_path = Path(session_info.original_pdf_path)
                    
                    self.raw_page_objects = self.pdf_analyzer.analyze_pdf_raw_blocks(pdf_path)
                    raw_data_json = json.dumps([asdict(p) for p in self.raw_page_objects], indent=2)
                    
                    session_dir = self.session_manager.get_session_directory(self.current_session_id)
                    with open(session_dir / "0_raw_analysis.json", "w", encoding="utf-8") as f:
                        f.write(raw_data_json)
                    self.debug_logger.info("Fichier de débogage '0_raw_analysis.json' sauvegardé.")

                    def update_ui_for_ai():
                        self.notebook.add(self.ai_frame)
                        self.notebook.select(self.ai_frame)
                        self.ai_input_text.delete('1.0', tk.END)
                        self.ai_input_text.insert('1.0', raw_data_json)
                        self.ai_output_text.delete('1.0', tk.END)
                        messagebox.showinfo("Action requise", "Les données brutes ont été extraites. Allez dans l'onglet 'Interaction IA' pour continuer.", parent=self.root)
                    
                    self.root.after(0, update_ui_for_ai)

                except Exception as e:
                    self.logger.error(f"Erreur d'analyse brute: {e}", exc_info=True)
                    self.root.after(0, lambda e=e: messagebox.showerror("Erreur d'Analyse Brute", str(e)))
                finally:
                    self._set_processing(False)
            else:
                self._set_processing(True, "Analyse du PDF en cours...")
                try:
                    session_info = self.session_manager.get_session_info(self.current_session_id)
                    pdf_path = Path(session_info.original_pdf_path)
                    page_objects = self.pdf_analyzer.analyze_pdf(pdf_path)
                    session_dir = self.session_manager.get_session_directory(self.current_session_id)
                    dom_path = session_dir / "1_dom_analysis.json"
                    with open(dom_path, "w", encoding="utf-8") as f: json.dump([asdict(p) for p in page_objects], f, indent=2)
                    self.debug_logger.info("Fichier de débogage '1_dom_analysis.json' sauvegardé.")
                    self.root.after(0, self._post_analysis_step, page_objects)
                except Exception as e:
                    self.logger.error(f"Erreur d'analyse: {e}", exc_info=True)
                    self.root.after(0, lambda e=e: messagebox.showerror("Erreur d'Analyse", str(e)))
                finally:
                    self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _process_gemini_output(self):
        gemini_output = self.ai_output_text.get('1.0', tk.END).strip()
        if not gemini_output:
            messagebox.showwarning("Entrée manquante", "Veuillez coller les instructions JSON de l'IA.", parent=self.root)
            return

        def thread_target():
            self._set_processing(True, "Application des instructions de l'IA...")
            try:
                # Étape 1 : Parser les instructions simples de l'IA
                instructions = json.loads(gemini_output)
                
                if not self.raw_page_objects:
                    raise RuntimeError("Les données d'analyse brutes (self.raw_page_objects) n'ont pas été trouvées.")
                
                # Étape 2 : Le programme construit la structure sémantique ("fichier 1")
                semantically_grouped_pages = self.pdf_analyzer.apply_grouping_instructions(
                    self.raw_page_objects, instructions
                )
                
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                dom_path = session_dir / "1_dom_analysis.json"
                with open(dom_path, "w", encoding="utf-8") as f:
                    json.dump([asdict(p) for p in semantically_grouped_pages], f, indent=2)
                self.debug_logger.info("Fichier '1_dom_analysis.json' construit par le programme à partir des instructions de l'IA.")

                # Étape 3 : Le reste du workflow est maintenant standard
                self.root.after(0, self._post_ai_processing, semantically_grouped_pages)

            except json.JSONDecodeError:
                self.logger.error("Erreur de parsing du JSON d'instructions de l'IA.", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror("Erreur de Format", "Le texte collé n'est pas un JSON d'instructions valide.", parent=self.root))
            except Exception as e:
                self.logger.error(f"Erreur lors de l'application des instructions de l'IA: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur Inconnue", str(e), parent=self.root))
            finally:
                self._set_processing(False)

        threading.Thread(target=thread_target, daemon=True).start()
    
    def _post_ai_processing(self, grouped_pages: List[PageObject]):
        """
        Une fois la structure sémantique créée, on enchaîne avec le workflow standard.
        """
        self._set_processing(True, "Génération des fichiers de traduction...")
        try:
            # On génère le XLIFF et les styles à partir de la structure unifiée
            extraction_result = self.text_extractor.create_xliff(grouped_pages, self.source_lang_var.get(), self.target_lang_var.get())
            xliff_content = extraction_result["xliff"]
            styles = extraction_result["styles"]
            session_dir = self.session_manager.get_session_directory(self.current_session_id)
            
            # Sauvegarder les fichiers
            with open(session_dir / "2_xliff_to_translate.xliff", "w", encoding="utf-8") as f: f.write(xliff_content)
            with open(session_dir / "styles.json", "w", encoding="utf-8") as f: json.dump(styles, f, indent=2)
            self.debug_logger.info("Fichiers XLIFF et styles générés après traitement IA.")
            
            # Mettre à jour l'UI pour passer à la traduction
            self.notebook.hide(self.ai_frame)
            self.notebook.select(self.translation_frame)
            self.translation_input.delete('1.0', tk.END)
            self.translation_input.insert('1.0', xliff_content)
            self.open_export_folder_button.config(state='normal')
            messagebox.showinfo("Succès", "La structure sémantique a été appliquée.\nLe fichier XLIFF a été généré et chargé. Vous pouvez maintenant traduire.", parent=self.root)

        except Exception as e:
            self.logger.error(f"Erreur lors de la post-traitement IA: {e}", exc_info=True)
            messagebox.showerror("Erreur", f"Erreur lors de la génération des fichiers de traduction : {e}", parent=self.root)
        finally:
             self._set_processing(False)

    def _post_analysis_step(self, page_objects: List[PageObject]):
        total_blocks = sum(len(p.text_blocks) for p in page_objects)
        total_spans = sum(len(para.spans) for p in page_objects for b in p.text_blocks for para in b.paragraphs)
        summary = f"Analyse terminée.\n- Pages: {len(page_objects)}\n- Blocs de texte: {total_blocks}\n- Segments de style (spans): {total_spans}"
        self.analysis_text.config(state='normal'); self.analysis_text.delete('1.0', tk.END); self.analysis_text.insert('1.0', summary); self.analysis_text.config(state='disabled')
        
        required_fonts = {span.font.name for page in page_objects for block in page.text_blocks for para in block.paragraphs for span in para.spans}
        
        font_report = self.font_manager.check_fonts_availability(list(required_fonts))
        if not font_report['all_available']:
            FontDialog(self.root, self.font_manager, font_report).show()
            
        self.continue_to_translation_button.config(state='normal')
        self.notebook.select(self.analysis_frame)

    def _generate_translation_export(self):
        def thread_target():
            self._set_processing(True, "Génération du fichier XLIFF...")
            try:
                page_objects = self._load_dom_from_file(self.current_session_id, "1_dom_analysis.json")
                extraction_result = self.text_extractor.create_xliff(page_objects, self.source_lang_var.get(), self.target_lang_var.get())
                xliff_content = extraction_result["xliff"]
                styles = extraction_result["styles"]
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                
                xliff_path = session_dir / "2_xliff_to_translate.xliff"
                with open(xliff_path, "w", encoding="utf-8") as f: f.write(xliff_content)
                
                styles_path = session_dir / "styles.json"
                with open(styles_path, "w", encoding="utf-8") as f: json.dump(styles, f, indent=2)

                self.root.after(0, lambda: self.open_export_folder_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", "Fichiers de traduction créés."))
            except Exception as e:
                self.logger.error(f"Erreur d'export XLIFF: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur d'Export", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()
    
    def _auto_translate(self):
        if not self.current_session_id: return messagebox.showerror("Erreur", "Aucune session active.")
        def thread_target():
            self._set_processing(True, "Traduction automatique en cours...")
            try:
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                
                xliff_path = session_dir / "2_xliff_to_translate.xliff"
                if not xliff_path.exists():
                    self.root.after(0, lambda: messagebox.showerror("Erreur", "Fichier XLIFF non trouvé. Veuillez d'abord générer les fichiers."))
                    self._set_processing(False)
                    return
                
                with open(xliff_path, "r", encoding="utf-8") as f:
                    xliff_content = f.read()

                translated_xliff = self.auto_translator.translate_xliff_content(xliff_content, self.target_lang_var.get())
                with open(session_dir / "3_xliff_translated.xliff", "w", encoding="utf-8") as f: f.write(translated_xliff)

                self.root.after(0, lambda: self.translation_input.delete('1.0', tk.END))
                self.root.after(0, lambda: self.translation_input.insert('1.0', translated_xliff))
                self.root.after(0, lambda: messagebox.showinfo("Succès", "Traduction automatique terminée."))
            except Exception as e:
                self.logger.error(f"Erreur de traduction automatique: {e}", exc_info=True)
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
                self.debug_logger.info(f"Fichier de débogage '4_parsed_translations.json' sauvegardé.")
                self.root.after(0, lambda: self.continue_to_layout_button.config(state='normal'))
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"{len(translations)} traductions importées."))
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
                session_dir = self.session_manager.get_session_directory(self.current_session_id)
                page_objects = self._load_dom_from_file(self.current_session_id, "1_dom_analysis.json")
                with open(session_dir / "4_parsed_translations.json", "r", encoding="utf-8") as f:
                    translations = json.load(f)
                
                self.debug_logger.info("Injection des traductions dans le DOM avant le layout...")
                self._prepare_render_version(page_objects, translations)
                
                final_pages = self.layout_processor.process_pages(page_objects)
                
                with open(session_dir / "5_final_layout.json", "w", encoding="utf-8") as f: 
                    json.dump([asdict(p) for p in final_pages], f, indent=2)
                self.debug_logger.info("Fichier de débogage '5_final_layout.json' sauvegardé.")
                
                self.root.after(0, lambda: self.layout_results_text.config(state='normal'))
                self.root.after(0, lambda: self.layout_results_text.delete('1.0', tk.END))
                self.root.after(0, lambda: self.layout_results_text.insert('1.0', "Calcul du reflow terminé."))
                self.root.after(0, lambda: self.layout_results_text.config(state='disabled'))
                self.root.after(0, lambda: self.continue_to_export_button.config(state='normal'))
            except Exception as e:
                self.logger.error(f"Erreur de mise en page: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur de Mise en Page", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _prepare_render_version(self, pages: List[PageObject], translations: Dict[str, str]) -> None:
        self.debug_logger.info("--- Démarrage de _prepare_render_version ---")
        
        span_map = { span.id: span for page in pages for block in page.text_blocks for para in block.paragraphs for span in para.spans }
        self.debug_logger.info(f"  > {len(span_map)} spans au total trouvés dans le DOM.")

        for span in span_map.values():
            span.text = ""

        for para_id, translated_html in translations.items():
            if not translated_html or not translated_html.strip():
                continue

            try:
                if translated_html.strip().startswith('<![CDATA['):
                    translated_html = translated_html.strip()[9:-3]
                
                parser = etree.HTMLParser()
                root = etree.fromstring(f"<div>{translated_html.strip()}</div>", parser)
                
                translated_spans = root.xpath('.//span[@id]')
                if not translated_spans:
                    self.debug_logger.warning(f"  ! Aucun span avec ID trouvé dans la traduction pour le paragraphe {para_id}")
                    continue

                for node in translated_spans:
                    span_id = node.get('id')
                    if span_id in span_map:
                        text_content = (node.text or "") + (node.tail or "").rstrip()
                        span_map[span_id].text = text_content
                        self.debug_logger.info(f"    > Mapping réussi pour {span_id}: '{text_content[:50]}...'")
                    else:
                        self.debug_logger.warning(f"    ! ID de span '{span_id}' trouvé dans la traduction mais pas dans le DOM pour le paragraphe {para_id}")
                        
            except Exception as e:
                self.debug_logger.error(f"  !! Erreur de parsing HTML pour le paragraphe {para_id}: {e}")
                self.debug_logger.error(f"     HTML problématique: {translated_html}")

        self.debug_logger.info("--- Fin de _prepare_render_version ---")

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
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"PDF exporté vers:\n{output_path}"))
            except Exception as e:
                self.logger.error(f"Erreur d'export PDF: {e}", exc_info=True)
                self.root.after(0, lambda e=e: messagebox.showerror("Erreur d'Export", str(e)))
            finally:
                self._set_processing(False)
        threading.Thread(target=thread_target, daemon=True).start()

    def _load_dom_from_file(self, session_id: str, filename: str) -> List[PageObject]:
        session_dir = self.session_manager.get_session_directory(session_id)
        file_path = session_dir / filename
        self.debug_logger.info(f"--- Démarrage de _load_dom_from_file (v2.2 Robuste) pour '{filename}' ---")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pages = []
        for page_data in data:
            page_obj = PageObject(page_number=page_data['page_number'], dimensions=tuple(page_data['dimensions']))

            for block_data in page_data.get('text_blocks', []):
                block_obj = TextBlock(
                    id=block_data['id'],
                    bbox=tuple(block_data['bbox']),
                    alignment=block_data.get('alignment', 0),
                    available_width=block_data.get('available_width', 0.0)
                )

                final_bbox_data = block_data.get('final_bbox')
                if final_bbox_data:
                    block_obj.final_bbox = tuple(final_bbox_data)

                if 'spans' in block_data and any(s.get('final_bbox') for s in block_data['spans']):
                    self.debug_logger.info(f"  > Détection d'un format post-layout pour le bloc {block_obj.id}.")
                    for span_data in block_data['spans']:
                        if not span_data.get('font'): continue # Sécurité
                        font_info = FontInfo(**span_data['font'])
                        span_obj = TextSpan(
                            id=span_data['id'],
                            text=span_data['text'],
                            bbox=tuple(span_data['bbox']),
                            font=font_info
                        )
                        span_final_bbox_data = span_data.get('final_bbox')
                        if span_final_bbox_data:
                            span_obj.final_bbox = tuple(span_final_bbox_data)
                        block_obj.spans.append(span_obj)
                
                elif 'paragraphs' in block_data and block_data['paragraphs']:
                    self.debug_logger.info(f"  > Détection d'un format pré-layout pour le bloc {block_obj.id}.")
                    for para_data in block_data['paragraphs']:
                        if not para_data.get('spans'):
                            self.debug_logger.warning(f"    - Paragraphe JSON vide ignoré dans le bloc {block_obj.id}")
                            continue
                            
                        para_obj = Paragraph(
                            id=para_data['id'],
                            is_list_item=para_data.get('is_list_item', False),
                            list_marker_text=para_data.get('list_marker_text', ""),
                            text_indent=para_data.get('text_indent', 0.0)
                        )
                        for span_data in para_data.get('spans', []):
                            font_info = FontInfo(**span_data['font'])
                            span_obj = TextSpan(
                                id=span_data['id'],
                                text=span_data['text'],
                                bbox=tuple(span_data['bbox']),
                                font=font_info
                            )
                            para_obj.spans.append(span_obj)
                        block_obj.paragraphs.append(para_obj)
                    
                    block_obj.spans = [span for para in block_obj.paragraphs for span in para.spans]

                page_obj.text_blocks.append(block_obj)

            pages.append(page_obj)
        self.debug_logger.info(f"--- Fin de _load_dom_from_file (corrigé v2.2) ---")
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
