# Project Documentation: shikaku (シカク)

This project automates the collection and hosting of university cafeteria and kitchen car schedules.

## Data Normalization Conventions

Consistency in data normalization is critical. We use two primary normalization functions:

1.  **`squash_name(x)`**: Used for **Shop Name (ID)** and **Note**.
    - Normalizes to NFKC (half-width).
    - Converts parentheses to full-width: `(` -> `（`, `)` -> `）`.
    - Collapses consecutive whitespace into a single space and trims.
2.  **`squash_field(x)`**: Used for **Location**, **Time**, **Business Hours**, and **Note** (depending on context).
    - Normalizes to NFKC (half-width).
    - Removes ALL whitespace.
    - Converts parentheses to full-width.
    - Replaces tilde `~` with full-width `～`.

## Data Pipeline

| Script | Input | Output | Purpose |
| :--- | :--- | :--- | :--- |
| `scripts/fetch_cafeteria_pdf.py` | Web URL | `daily/YYYY_MM.pdf` | Fetches cafeteria PDFs. |
| `scripts/parse_cafeteria_pdf.py` | `daily/YYYY_MM.pdf` | `tmp/parsed_YYYY_MM.json` | Parses cafeteria PDF to normalized JSON. |
| `scripts/fetch_kitchen_cars.py` | Web URL | `tmp/kitchen_cars_raw.html` | Fetches JS-rendered HTML for kitchen cars. |
| `scripts/scrape_kitchen_cars.py` | `tmp/kitchen_cars_raw.html` | `tmp/scraped_kitchen_cars.json` | Parses HTML to normalized JSON. |
| `scripts/generator.py` | `tmp/parsed_*.json`, `tmp/scraped_kitchen_cars.json` | `public/api/...` | Integrates data and generates API endpoints. |

## Workflow Rules

- **Input paths:** Do not hardcode input paths in scripts. Use CLI arguments (e.g., `argparse`).
- **Output paths:** Scripts should default to `stdout`. Use `-o` or `--output` for file output when necessary.
- **Normalization:** Always apply `squash_name` or `squash_field` as defined above.
- **Regression:** Always run `scripts/test_cafeteria_parser.py` after modifying parsing logic.
- **State Management:** Use `daily/.metadata.json` for tracking PDF fetch status in CI environments.
