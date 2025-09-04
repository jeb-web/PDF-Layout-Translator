#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Script d'installation et de compilation
Configuration pour l'installation et la création d'exécutables

Auteur: L'OréalGPT
Version: 1.0.0
"""

import sys
import os
import shutil
from pathlib import Path
from setuptools import setup, find_packages
import subprocess

# Informations sur le projet
PROJECT_NAME = "pdf-layout-translator"
VERSION = "1.0.0"
DESCRIPTION = "Application de traduction de documents PDF avec préservation de la mise en page"
LONG_DESCRIPTION = """
PDF Layout Translator est une application de traduction de documents PDF qui préserve
la mise en page originale. Elle permet de traduire des documents tout en maintenant
la structure visuelle, les polices et la disposition des éléments.

Fonctionnalités principales :
- Analyse approfondie de la structure PDF
- Extraction intelligente du texte pour traduction
- Interface de gestion des traductions
- Reconstruction du PDF avec mise en page préservée
- Support des polices personnalisées
- Prévisualisation avec comparaison avant/après
"""

AUTHOR = "L'OréalGPT"
AUTHOR_EMAIL = "loreal.gpt@example.com"
URL = "https://github.com/loreal/pdf-layout-translator"

# Dépendances principales
INSTALL_REQUIRES = [
    # PDF Processing
    "PyMuPDF>=1.23.14",
    "reportlab>=4.0.7",
    "pypdf>=3.17.4",
    
    # Font Management
    "fonttools>=4.47.0",
    "pillow>=10.1.0",
    
    # Text Processing
    "regex>=2023.10.3",
    "chardet>=5.2.0",
    
    # File Management
    "pathlib2>=2.3.7",
    "send2trash>=1.8.2",
    
    # JSON/Config validation
    "jsonschema>=4.20.0",
    
    # GUI enhancements (optionnel)
    "tkinterdnd2>=0.4.1",
]

# Dépendances de développement
DEV_REQUIRES = [
    "pytest>=7.4.3",
    "pytest-cov>=4.1.0",
    "black>=23.12.0",
    "flake8>=6.1.0",
    "mypy>=1.8.0",
    "sphinx>=7.2.0",
    "sphinx-rtd-theme>=2.0.0",
]

# Dépendances pour la compilation
BUILD_REQUIRES = [
    "pyinstaller>=6.3.0",
    "auto-py-to-exe>=2.43.0",  # Interface graphique pour PyInstaller
]

# Classification PyPI
CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: End Users/Desktop",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Office/Business",
    "Topic :: Text Processing",
    "Topic :: Multimedia :: Graphics :: Viewers",
    "Topic :: Software Development :: Internationalization",
]

# Points d'entrée
ENTRY_POINTS = {
    "console_scripts": [
        "pdf-layout-translator=src.main:main",
        "plt=src.main:main",
    ],
    "gui_scripts": [
        "pdf-layout-translator-gui=src.main:main",
    ],
}

# Fichiers de données à inclure
PACKAGE_DATA = {
    "src": [
        "assets/*",
        "assets/icons/*",
        "assets/templates/*",
        "config/*.json",
        "config/*.yaml",
    ]
}

# Fichiers supplémentaires
DATA_FILES = [
    ("share/pdf-layout-translator/docs", ["README.md", "LICENSE", "CHANGELOG.md"]),
    ("share/pdf-layout-translator/examples", []),
]

def get_version():
    """Récupère la version depuis le fichier de version ou git"""
    version_file = Path("src") / "__version__.py"
    
    if version_file.exists():
        with open(version_file, 'r') as f:
            exec(f.read())
            return locals().get('__version__', VERSION)
    
    # Fallback vers git si disponible
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return VERSION

def create_version_file():
    """Crée un fichier de version"""
    version_file = Path("src") / "__version__.py"
    version_content = f'''"""Version information for PDF Layout Translator"""

__version__ = "{get_version()}"
__author__ = "{AUTHOR}"
__email__ = "{AUTHOR_EMAIL}"
__url__ = "{URL}"
'''
    
    with open(version_file, 'w') as f:
        f.write(version_content)

def check_dependencies():
    """Vérifie que les dépendances système sont installées"""
    missing_deps = []
    
    # Vérifier Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 ou supérieur requis")
        sys.exit(1)
    
    # Vérifier les dépendances système optionnelles
    system_deps = {
        "git": "Git (optionnel pour versioning)",
        "pandoc": "Pandoc (optionnel pour documentation)",
    }
    
    for cmd, description in system_deps.items():
        try:
            subprocess.run([cmd, "--version"], 
                         capture_output=True, 
                         check=True)
            print(f"✅ {description}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"⚠️  {description} - non trouvé")
            missing_deps.append(cmd)
    
    return missing_deps

def build_executable():
    """Construit l'exécutable avec PyInstaller"""
    print("🔨 Construction de l'exécutable...")
    
    # Configuration PyInstaller
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Analyse des imports
a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/assets', 'assets'),
        ('src/config', 'config'),
        ('README.md', '.'),
        ('LICENSE', '.'),
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'PIL._tkinter_finder',
        'fitz',
        'reportlab',
        'fontTools',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filtrer les fichiers inutiles
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF-Layout-Translator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/assets/icons/app_icon.ico' if os.path.exists('src/assets/icons/app_icon.ico') else None,
)

# Pour macOS, créer un bundle .app
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='PDF Layout Translator.app',
        icon='src/assets/icons/app_icon.icns' if os.path.exists('src/assets/icons/app_icon.icns') else None,
        bundle_identifier='com.loreal.pdf-layout-translator',
        info_plist={
            'CFBundleDisplayName': 'PDF Layout Translator',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
'''
    
    # Écrire le fichier spec
    spec_file = Path("pdf_translator.spec")
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    try:
        # Exécuter PyInstaller
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)]
        result = subprocess.run(cmd, check=True)
        
        print("✅ Exécutable créé avec succès!")
        print(f"📁 Fichier de sortie: dist/PDF-Layout-Translator{'.exe' if sys.platform == 'win32' else ''}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la construction: {e}")
        return False
    finally:
        # Nettoyer les fichiers temporaires
        if spec_file.exists():
            spec_file.unlink()

def create_installer():
    """Crée un installateur pour Windows"""
    if sys.platform != 'win32':
        print("⚠️  Installateur Windows uniquement supporté sur Windows")
        return False
    
    print("📦 Création de l'installateur Windows...")
    
    # Configuration Inno Setup (si disponible)
    inno_script = '''[Setup]
AppName=PDF Layout Translator
AppVersion=1.0.0
AppPublisher=L'Oréal
DefaultDirName={autopf}\\PDF Layout Translator
DefaultGroupName=PDF Layout Translator
OutputDir=dist\\installer
OutputBaseFilename=PDF-Layout-Translator-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\\PDF-Layout-Translator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\\PDF Layout Translator"; Filename: "{app}\\PDF-Layout-Translator.exe"
Name: "{group}\\{cm:UninstallProgram,PDF Layout Translator}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\\PDF Layout Translator"; Filename: "{app}\\PDF-Layout-Translator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\\PDF-Layout-Translator.exe"; Description: "{cm:LaunchProgram,PDF Layout Translator}"; Flags: nowait postinstall skipifsilent
'''
    
    inno_file = Path("installer.iss")
    with open(inno_file, 'w', encoding='utf-8') as f:
        f.write(inno_script)
    
    try:
        # Chercher Inno Setup
        inno_paths = [
            "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
            "C:\\Program Files\\Inno Setup 6\\ISCC.exe",
        ]
        
        inno_exe = None
        for path in inno_paths:
            if Path(path).exists():
                inno_exe = path
                break
        
        if not inno_exe:
            print("⚠️  Inno Setup non trouvé. Téléchargez-le depuis https://jrsoftware.org/isinfo.php")
            return False
        
        # Compiler l'installateur
        cmd = [inno_exe, str(inno_file)]
        result = subprocess.run(cmd, check=True)
        
        print("✅ Installateur créé avec succès!")
        print("📁 Fichier: dist/installer/PDF-Layout-Translator-Setup.exe")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la création de l'installateur: {e}")
        return False
    finally:
        if inno_file.exists():
            inno_file.unlink()

def clean_build():
    """Nettoie les fichiers de build"""
    print("🧹 Nettoyage des fichiers de build...")
    
    dirs_to_clean = [
        "build",
        "dist",
        "src.egg-info",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    ]
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            if dir_path.is_dir():
                shutil.rmtree(dir_path)
            else:
                dir_path.unlink()
            print(f"🗑️  Supprimé: {dir_name}")
    
    # Nettoyer les fichiers .pyc récursivement
    for pyc_file in Path(".").rglob("*.pyc"):
        pyc_file.unlink()
    
    print("✅ Nettoyage terminé")

def run_tests():
    """Exécute les tests"""
    print("🧪 Exécution des tests...")
    
    try:
        # Installer pytest si nécessaire
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest"], 
                      capture_output=True, check=True)
        
        # Exécuter les tests
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
        result = subprocess.run(cmd, check=True)
        
        print("✅ Tous les tests passent!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Échec des tests: {e}")
        return False
    except FileNotFoundError:
        print("⚠️  Répertoire tests/ non trouvé")
        return True

def main():
    """Fonction principale pour les commandes de build"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Script de build pour PDF Layout Translator")
    parser.add_argument("command", nargs="?", default="install",
                       choices=["install", "build", "installer", "test", "clean", "dev", "check"],
                       help="Commande à exécuter")
    parser.add_argument("--dev", action="store_true", help="Installation en mode développement")
    parser.add_argument("--user", action="store_true", help="Installation utilisateur uniquement")
    
    args = parser.parse_args()
    
    if args.command == "check":
        print("🔍 Vérification des dépendances...")
        missing = check_dependencies()
        if not missing:
            print("✅ Toutes les dépendances système sont disponibles")
        return
    
    elif args.command == "clean":
        clean_build()
        return
    
    elif args.command == "test":
        success = run_tests()
        sys.exit(0 if success else 1)
    
    elif args.command == "build":
        print("🔨 Construction de l'application...")
        
        # Vérifier les dépendances
        check_dependencies()
        
        # Créer le fichier de version
        create_version_file()
        
        # Construire l'exécutable
        success = build_executable()
        
        if success and sys.platform == "win32":
            # Proposer de créer l'installateur
            response = input("\n💡 Créer un installateur Windows? (y/N): ")
            if response.lower() in ['y', 'yes', 'oui']:
                create_installer()
        
        return
    
    elif args.command == "installer":
        if not Path("dist/PDF-Layout-Translator.exe").exists():
            print("❌ Exécutable non trouvé. Exécutez d'abord 'python setup.py build'")
            sys.exit(1)
        
        success = create_installer()
        sys.exit(0 if success else 1)
    
    elif args.command == "dev":
        args.dev = True
    
    # Installation normale avec setuptools
    print(f"📦 Installation de {PROJECT_NAME} v{get_version()}")
    
    # Créer le fichier de version
    create_version_file()

if __name__ == "__main__":
    # Si appelé avec des arguments, exécuter les commandes de build
    if len(sys.argv) > 1 and sys.argv[1] in ["build", "installer", "test", "clean", "check"]:
        main()
    else:
        # Installation normale avec setuptools
        create_version_file()
        
        setup(
            name=PROJECT_NAME,
            version=get_version(),
            description=DESCRIPTION,
            long_description=LONG_DESCRIPTION,
            long_description_content_type="text/markdown",
            author=AUTHOR,
            author_email=AUTHOR_EMAIL,
            url=URL,
            
            packages=find_packages(include=["src", "src.*"]),
            package_dir={"": "."},
            package_data=PACKAGE_DATA,
            data_files=DATA_FILES,
            
            python_requires=">=3.8",
            install_requires=INSTALL_REQUIRES,
            extras_require={
                "dev": DEV_REQUIRES,
                "build": BUILD_REQUIRES,
                "all": DEV_REQUIRES + BUILD_REQUIRES,
            },
            
            entry_points=ENTRY_POINTS,
            
            classifiers=CLASSIFIERS,
            keywords="pdf translation layout preservation document processing",
            
            zip_safe=False,
            include_package_data=True,
            
            # Métadonnées étendues
            project_urls={
                "Bug Reports": f"{URL}/issues",
                "Source": URL,
                "Documentation": f"{URL}/docs",
            },
        )