PYTHON = venv/bin/python3
SCRIPTS_DIR = scripts
TMP_DIR = tmp
PUBLIC_DIR = public
DAILY_DIR = $(PUBLIC_DIR)/daily
MASTER_JSON = $(SCRIPTS_DIR)/master.json

# Output files
KITCHEN_CARS_RAW = $(TMP_DIR)/kitchen_cars_raw.html
KITCHEN_CARS_JSON = $(TMP_DIR)/scraped_kitchen_cars.json

# PDF files and their corresponding parsed JSON files
# Note: Use shell wildcard to ensure we pick up files at execution time
PDF_FILES = $(wildcard $(DAILY_DIR)/*.pdf)
PARSED_JSONS = $(patsubst $(DAILY_DIR)/%.pdf, $(TMP_DIR)/parsed_%.json, $(PDF_FILES))

.PHONY: all fetch_pdf fetch_kitchencar parse_pdf parse_kitchencar generate serve clean test help

all: generate

help:
	@echo "Usage:"
	@echo "  make fetch_pdf         Fetch latest cafeteria PDFs from university website"
	@echo "  make fetch_kitchencar  Fetch latest kitchen car HTML"
	@echo "  make parse_pdf         Parse all PDFs in $(DAILY_DIR) to JSON"
	@echo "  make parse_kitchencar  Scrape kitchen car HTML to JSON"
	@echo "  make generate          Run the full pipeline (parse and generate API)"
	@echo "  make serve             Start a local development server on port 8000"
	@echo "  make test              Run cafeteria parser tests"
	@echo "  make clean             Remove temporary files"

# 1. Fetching
fetch_pdf:
	$(PYTHON) $(SCRIPTS_DIR)/fetch_cafeteria_pdf.py

fetch_kitchencar:
	@mkdir -p $(TMP_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/fetch_kitchen_cars.py -o $(KITCHEN_CARS_RAW)

# 2. Parsing
parse_pdf: $(PARSED_JSONS)

$(TMP_DIR)/parsed_%.json: $(DAILY_DIR)/%.pdf
	@mkdir -p $(TMP_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/parse_cafeteria_pdf.py $< -o $@

parse_kitchencar: $(KITCHEN_CARS_JSON)

$(KITCHEN_CARS_JSON): $(KITCHEN_CARS_RAW)
	@mkdir -p $(TMP_DIR)
	$(PYTHON) $(SCRIPTS_DIR)/scrape_kitchen_cars.py $(KITCHEN_CARS_RAW) $(KITCHEN_CARS_JSON)

# 3. Generating
generate: parse_pdf parse_kitchencar
	$(PYTHON) $(SCRIPTS_DIR)/generator.py \
		--cafeteria-dir $(TMP_DIR) \
		--kitchen-cars $(KITCHEN_CARS_JSON) \
		--master $(MASTER_JSON) \
		-o $(PUBLIC_DIR)

serve:
	$(PYTHON) -m http.server 8000 -d $(PUBLIC_DIR)

# Utilities
clean:
	rm -rf $(TMP_DIR)

test:
	$(PYTHON) $(SCRIPTS_DIR)/test_cafeteria_parser.py
