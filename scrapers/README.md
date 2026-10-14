# scrapers/

Scraper Laboratory -- canary testing for external data sources.

IMPORTANT: For laboratory testing and schema-drift detection ONLY.
Must NOT be imported by production agents.

## Usage

    python scraper.py test reddit
    python scraper.py test-all
    python scraper.py health
    python scraper.py report

## Canary Fixtures
Each platform has a fixture in scrapers/fixtures/canaries.py.
If a canary fails, the target site changed its schema.
