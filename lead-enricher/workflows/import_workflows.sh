#!/bin/bash
# Assuming you have the n8n CLI available, or run this via Docker on your VPS:
# Example: docker exec -it n8n-container bash
# Inside the container (or wherever n8n CLI is installed):

n8n import:workflow --input=01_import_batch.json
n8n import:workflow --input=02_resolve_company.json
n8n import:workflow --input=03_enrich_company.json
n8n import:workflow --input=04_discover_news.json
n8n import:workflow --input=05_extract_sites.json
n8n import:workflow --input=06_find_contacts.json
n8n import:workflow --input=07_qa_verify.json
n8n import:workflow --input=08_export_results.json

echo "All workflows imported successfully!"
