# 📄 PDF Layout Translator

[![Build Status](https://github.com/loreal/pdf-layout-translator/workflows/Build%20and%20Release/badge.svg)](https://github.com/loreal/pdf-layout-translator/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/loreal/pdf-layout-translator/releases)

Une application de traduction de documents PDF qui **préserve parfaitement la mise en page originale**. Traduis tes documents tout en gardant la structure visuelle, les polices et la disposition des éléments intacts.

![PDF Layout Translator Screenshot](docs/images/main-interface.png)

## ✨ Fonctionnalités Principales

### 🔍 **Analyse Intelligente**
- **Détection automatique** de la structure du document (titres, paragraphes, listes, tableaux)
- **Extraction précise** du texte avec préservation du contexte
- **Analyse des polices** utilisées et gestion des remplacements
- **Évaluation de la complexité** de traduction

### 🌐 **Traduction Flexible**
- **Interface avec IA externe** : utilise ChatGPT, Claude, Gemini ou toute autre IA
- **Export structuré** : génère automatiquement les prompts et fichiers pour l'IA
- **Validation intelligente** : détecte les erreurs et incohérences
- **Gestion manuelle** : interface d'édition élément par élément

### 📐 **Préservation de Mise en Page**
- **Calcul automatique** des ajustements nécessaires
- **Gestion de l'expansion/contraction** du texte traduit
- **Solutions intelligentes** : réduction de police, extension de conteneurs, etc.
- **Prévisualisation en temps réel** avec comparaison avant/après

### 🔧 **Gestion Avancée des Polices**
- **Détection des polices manquantes** avec suggestions de remplacement
- **Support des polices personnalisées** (installation automatique)
- **Mappings persistants** pour les futures traductions
- **Validation des licences** pour usage commercial

### 📤 **Export Professionnel**
- **Reconstruction complète** du PDF avec qualité optimale
- **Préservation des éléments** : images, annotations, liens, formulaires
- **PDF de comparaison** côte à côte pour validation
- **Optimisation automatique** de la taille du fichier

## 🖼️ Aperçu de l'Interface

<details>
<summary>📱 Voir les captures d'écran</summary>

### Interface Principale
![Interface Principale](docs/images/main-window.png)

### Gestionnaire de Traductions
![Gestionnaire de Traductions](docs/images/translation-manager.png)

### Prévisualisation Comparée
![Prévisualisation](docs/images/preview-comparison.png)

### Gestion des Polices
![Gestion des Polices](docs/images/font-manager.png)

</details>

## 🚀 Installation Rapide

### Option 1 : Téléchargement Direct (Recommandé)

1. **Rendez-vous sur la page [Releases](https://github.com/loreal/pdf-layout-translator/releases)**
2. **Téléchargez** la version correspondant à votre système :
   - 🪟 **Windows** : `PDF-Layout-Translator-windows-installer.exe`
   - 🍎 **macOS** : `PDF-Layout-Translator.dmg`
   - 🐧 **Linux** : `PDF-Layout-Translator.AppImage`

3. **Installez** en suivant les instructions de votre système

### Option 2 : Installation Python
