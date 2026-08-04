PYTHON = python3
SCRIPTS_DIR = scripts
PUBLIC_DIR = public
DATA_DIR = data
PDF_SRC_DIR = $(DATA_DIR)/pdfs
KITCHEN_CARS_SRC = $(DATA_DIR)/kitchencars
DEST_DIR = static
PDFS_DEST_DIR = $(DEST_DIR)/daily
FACILITIES_JSON = $(SCRIPTS_DIR)/facilities.json
BASE_URL := $(shell hugo config | grep -i "^baseurl" | awk '{print $$3}' | tr -d "'" | sed 's|/$$||')

# Output files
KITCHEN_CARS_RAW = $(KITCHEN_CARS_SRC)/raw.html
KITCHEN_CARS_JSON = $(KITCHEN_CARS_SRC)/scraped.json

# PDF files and their corresponding parsed JSON files
PDF_FILES = $(wildcard $(PDF_SRC_DIR)/*.pdf)
PARSED_JSONS = $(patsubst $(PDF_SRC_DIR)/%.pdf, $(DATA_DIR)/cafeterias/%.json, $(PDF_FILES))

.PHONY: all fetch_pdf fetch_kitchencar parse_pdf parse_kitchencar generate serve clean test help css stale_api

all: css generate

help:
	@echo "Usage:"
	@echo "  make css               Build Tailwind CSS"
	@echo "  make fetch_pdf         Fetch latest cafeteria PDFs from university website"
	@echo "  make fetch_kitchencar  Fetch latest kitchen car HTML"
	@echo "  make parse_pdf         Parse all PDFs in $(PDF_SRC_DIR) to JSON"
	@echo "  make parse_kitchencar  Scrape kitchen car HTML to JSON"
	@echo "  make generate          Run the full pipeline (parse and generate API)"
	@echo "  make serve             Start a local development server on port 8000"
	@echo "  make test              Run cafeteria parser tests"
	@echo "  make stale_api         List deployed API files that are no longer generated"
	@echo "  make clean             Remove temporary files"

# 1. Fetching
fetch_pdf:
	@mkdir -p $(PDF_SRC_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/fetch_cafeteria_pdf.py -o $(PDF_SRC_DIR)

fetch_cafeteria: fetch_pdf

fetch_kitchencar:
	@mkdir -p $(KITCHEN_CARS_SRC)
	$(PYTHON) $(SCRIPTS_DIR)/fetch_kitchen_cars.py -o $(KITCHEN_CARS_RAW)

# 2. Parsing
parse_pdf: $(PARSED_JSONS)

$(DATA_DIR)/cafeterias/%.json: $(PDF_SRC_DIR)/%.pdf
	@mkdir -p $(DATA_DIR)/cafeterias
	$(PYTHON) $(SCRIPTS_DIR)/parse_cafeteria_pdf.py $< -o $@

parse_kitchencar: $(KITCHEN_CARS_JSON)

$(KITCHEN_CARS_JSON): $(KITCHEN_CARS_RAW)
	@mkdir -p $(KITCHEN_CARS_SRC)
	$(PYTHON) $(SCRIPTS_DIR)/scrape_kitchen_cars.py $(KITCHEN_CARS_RAW) $(KITCHEN_CARS_JSON)

# 3. Generating
generate: parse_pdf parse_kitchencar
	@mkdir -p $(PDFS_DEST_DIR)
	@cp -n $(PDF_SRC_DIR)/*.pdf $(PDFS_DEST_DIR)/ 2>/dev/null || true
	@cp $(FACILITIES_JSON) $(DEST_DIR)/assets
	@cp $(PDF_SRC_DIR)/.metadata.json $(PDFS_DEST_DIR)/ 2>/dev/null || true
	$(PYTHON) $(SCRIPTS_DIR)/generator.py \
		--cafeteria-dir $(DATA_DIR)/cafeterias \
		--kitchen-cars $(KITCHEN_CARS_JSON) \
		--kitchen-cars-archive $(DATA_DIR)/kitchen_cars_past.json \
		--master $(FACILITIES_JSON) \
		--base-url $(BASE_URL) \
		-o $(DEST_DIR)

css:
	npx @tailwindcss/cli -i assets/css/main.css -o static/css/compiled.css --minify

build_html: css
	hugo --minify

serve:
# 	$(PYTHON) -m http.server 8000 -d $(PUBLIC_DIR)
	hugo server

# Utilities
clean:
	rm -rf $(DATA_DIR)

test:
	$(PYTHON) $(SCRIPTS_DIR)/test_cafeteria_parser.py

# Compare the deployed API against what `make generate` produces.
stale_api:
	@git fetch -q origin gh-pages
	$(PYTHON) $(SCRIPTS_DIR)/find_stale_api.py -o $(DEST_DIR)
