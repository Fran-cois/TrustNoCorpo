# Makefile minimal et portable pour projets LaTeX
# Usage:
#   make            -> compile le PDF (cible `pdf`)
#   make pdf        -> même chose
#   make view       -> ouvre le PDF (macOS `open`)
#   make watch      -> compilation continue si latexmk présent
#   make clean      -> supprime fichiers auxiliaires
#   make distclean  -> supprime tout le répertoire de sortie

# Nom du fichier principal .tex (modifiable à la ligne de commande)
# Par défaut, utiliser l'exemple fourni
MAIN ?= test-crypto.tex

# Répertoire de sortie
OUTDIR ?= build

# Moteur LaTeX par défaut (utilisé si latexmk absent)
# Changer par défaut pour lualatex comme demandé
LATEX_ENGINE ?= lualatex

# Commande CLI installée via pip
TRUSTNOCORPO ?= trustnocorpo

# Variables de cryptage/traçabilité
CLASSIFICATION ?=
GENERATION_INFO := $(shell echo "$$USER@$$HOSTNAME" | base64 | tr -d '\n')
GENERATION_TIME := $(shell date '+%Y-%m-%d %H:%M:%S %Z' | base64 | tr -d '\n')
BUILD_HASH := $(shell echo "$(GENERATION_INFO)$(GENERATION_TIME)" | shasum -a 256 | cut -d' ' -f1 | head -c 16)

# (Les anciens scripts Python séparés ne sont plus nécessaires; la CLI gère tout)

# PDF Password (can be overridden)
PDF_PASSWORD ?=

# Watermark and footer options
# Example: make WATERMARK="CONFIDENTIAL" FOOTER_FP=yes
WATERMARK ?=
FOOTER_FP ?= no
ONLY_PASSWORD ?= no

# Derived CLI flags
BUILD_FLAGS := --classification="$(CLASSIFICATION)" --output-dir="$(OUTDIR)"
BUILD_FLAGS += $(if $(WATERMARK),--watermark="$(WATERMARK)",)
BUILD_FLAGS += $(if $(filter yes true 1,$(FOOTER_FP)),--footer-fingerprint,)
BUILD_FLAGS += $(if $(filter yes true 1,$(ONLY_PASSWORD)),--only-password,)

# Options latexmk (si présent)
LATEXMK := $(shell command -v latexmk 2>/dev/null || true)
# Force latexmk to use lualatex for PDF generation
# latexmk: -pdflatex="lualatex %O %S" tells latexmk to run lualatex when it would
# otherwise call pdflatex. Keep -pdf to produce PDF output.
LATEXMK_OPTS ?= -pdf -pdflatex="lualatex %O %S" -silent -interaction=nonstopmode -synctex=1
LATEXMK_OUTDIR := -outdir=$(OUTDIR)

# Fichier PDF final
PDF := $(OUTDIR)/$(basename $(notdir $(MAIN))).pdf

.PHONY: all init pdf view watch clean distclean check-tools
all: pdf

init:
	@$(TRUSTNOCORPO) init >/dev/null || { echo "❌ Initialization failed"; exit 1; }

pdf: init
	@mkdir -p "$(OUTDIR)"
	@$(TRUSTNOCORPO) build "$(MAIN)" $(BUILD_FLAGS) || { echo "❌ Build failed"; exit 1; }

view: pdf
	@echo "Opening $(PDF)"
	@open "$(PDF)"

watch:
	@sh -c 'if [ -n "$(LATEXMK)" ]; then latexmk -pvc $(LATEXMK_OPTS) -outdir="$(OUTDIR)" "$(MAIN)"; else echo "latexmk required for watch mode. Install it (TeX Live/MacTeX) or use \"make pdf\" repeatedly."; fi'

# Verify required tools are installed
check-tools:
	@echo "🔍 Checking LaTeX toolchain..."
	@command -v lualatex >/dev/null 2>&1 && echo "✅ lualatex found: $$(command -v lualatex)" || { echo "❌ lualatex not found. Install MacTeX or TinyTeX, then ensure /Library/TeX/texbin is on PATH."; exit 1; }
	@command -v latexmk >/dev/null 2>&1 && echo "✅ latexmk found: $$(command -v latexmk)" || echo "⚠️ latexmk not found (optional; build will use lualatex directly)"
	@echo "Done."

clean:
	@echo "Removing common auxiliary files from $(OUTDIR)"
	@find $(OUTDIR) -type f \( -name "*.aux" -o -name "*.log" -o -name "*.toc" -o -name "*.out" -o -name "*.lof" -o -name "*.lot" -o -name "*.fls" -o -name "*.fdb_latexmk" -o -name "*.synctex.gz" -o -name "*.bbl" -o -name "*.blg" \) -delete || true

distclean: 
	@echo "Removing $(OUTDIR) entirely"
	@rm -rf "$(OUTDIR)"

# Utilisation recommandée:
#   make MAIN=paper.tex       # compile paper.tex
#   make pdf && make view
#   make CLASSIFICATION="FOR ALICE EYES ONLY" pdf    # compile avec classification
#   make CLASSIFICATION="RESTRICTED ACCESS" pdf      # autre exemple
# Remarques:
# - Ce Makefile crée le dossier $(OUTDIR) et y place les fichiers de sortie.
# - Préfère latexmk si disponible; sinon utilise $(LATEX_ENGINE).
# - Pour bibliographies plus avancées (biber, biblatex) adaptez la section fallback.
# - Le système de cryptage intègre des informations de traçabilité dans le PDF.

# Cibles de cryptage spécialisées
.PHONY: confidential restricted secret setup-user user-info reset-user db-info db-reset protect-pdf unprotect-pdf

# Targets spéciaux pour les utilisateurs
setup-user:
	@echo "🔐 Setting up user encryption keys..."
	@$(TRUSTNOCORPO) keys --generate || echo "⚠️  User setup failed"

user-info:
	@echo "👤 User encryption information:"
	@$(TRUSTNOCORPO) keys --info || echo "⚠️  User info failed (setup required: make setup-user)"

reset-user:
	@echo "🗑️  Resetting user encryption keys..."
	@$(TRUSTNOCORPO) keys --reset || echo "⚠️  User reset failed"

# Targets de classification spécialisés avec protection PDF
confidential: CLASSIFICATION=CONFIDENTIAL
confidential: PROTECT_PDF=yes
confidential: pdf

secret: CLASSIFICATION=SECRET
secret: PROTECT_PDF=yes
secret: pdf

top-secret: CLASSIFICATION=TOP SECRET
top-secret: PROTECT_PDF=yes
top-secret: pdf

for-eyes-only: CLASSIFICATION=FOR $(USER) EYES ONLY
for-eyes-only: PROTECT_PDF=yes
for-eyes-only: pdf

# Gestion de la base de données
db-info:
	@echo "📊 System information:"
	@$(TRUSTNOCORPO) info || echo "⚠️  Info failed"

db-reset:
	@echo "🗑️  Database reset is not automated via Makefile."
	@echo "   If you really want to reset, remove the project's .trustnocorpo/builds.db file manually."
	@echo "   Warning: this is destructive and will remove all audit entries."

# Protection PDF post-build
protect-pdf:
	@if [ -f "$(PDF)" ]; then \
		echo "🔒 Protecting existing PDF..."; \
		$(TRUSTNOCORPO) protect "$(PDF)" --build-hash="$(BUILD_HASH)" --classification="$(CLASSIFICATION)" || echo "⚠️  PDF protection failed"; \
	else \
		echo "❌ PDF not found: $(PDF)"; \
		exit 1; \
	fi

# Déprotection PDF (pour tests)
unprotect-pdf:
	@if [ -f "$(PDF)" ]; then \
		echo "🔓 Attempting to unprotect PDF..."; \
		$(TRUSTNOCORPO) protect --unprotect "$(PDF)" --build-hash="$(BUILD_HASH)" || echo "⚠️  PDF unprotection failed"; \
	else \
		echo "❌ PDF not found: $(PDF)"; \
		exit 1; \
	fi
confidential:
	@$(MAKE) CLASSIFICATION="CONFIDENTIAL" pdf

restricted:
	@$(MAKE) CLASSIFICATION="RESTRICTED ACCESS" pdf

secret:
	@$(MAKE) CLASSIFICATION="SECRET" pdf

eyes-only:
	@if [ -z "$(FOR)" ]; then echo "Usage: make eyes-only FOR=USERNAME"; exit 1; fi
	@$(MAKE) CLASSIFICATION="FOR $(FOR) EYES ONLY" pdf

# Debug crypto info
debug-crypto:
	@echo "Generation Info (base64): $(GENERATION_INFO)"
	@echo "Decoded: $$(echo '$(GENERATION_INFO)' | base64 -d)"
	@echo "Generation Time (base64): $(GENERATION_TIME)"
	@echo "Decoded: $$(echo '$(GENERATION_TIME)' | base64 -d)"
	@echo "Build Hash: $(BUILD_HASH)"

# Database management
install-deps:
	@echo "Installing Python dependencies..."
	@pip3 install -r requirements.txt

db-list:
	@$(DB_MANAGER) list

db-stats:
	@$(DB_MANAGER) stats

db-show:
	@if [ -z "$(HASH)" ]; then echo "Usage: make db-show HASH=<build_hash>"; exit 1; fi
	@$(DB_MANAGER) show $(HASH)

db-verify:
	@if [ -z "$(HASH)" ]; then echo "Usage: make db-verify HASH=<build_hash>"; exit 1; fi
	@$(DB_MANAGER) verify $(HASH)

db-export:
	@$(DB_MANAGER) export -o builds_backup_$$(date +%Y%m%d_%H%M%S).json
	@echo "Base de données exportée"

# Audit de sécurité complet
security-audit:
	@python3 security_audit.py

# Aide pour les commandes de base de données
db-help:
	@echo "=== Commandes de gestion de base de données ==="
	@echo "make db-list              # Liste des builds récents"
	@echo "make db-stats             # Statistiques générales"
	@echo "make db-show HASH=xxx     # Détails d'un build"
	@echo "make db-verify HASH=xxx   # Vérifier l'intégrité"
	@echo "make db-export            # Sauvegarder la base"
	@echo "make security-audit       # Audit de sécurité complet"
	@echo "make install-deps         # Installer les dépendances Python"
