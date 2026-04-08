# Lead Enricher n8n Workflows Setup

This folder contains 8 highly modular n8n workflow files designed to connect your running `n8n` system to our internally deployed `lead-enricher-api`.

## 1. Import Steps
You can import the workflows in two ways:
**Method A (UI - Recommended):**
1. Open your n8n UI in the browser.
2. Go to the "Workflows" tab.
3. Click "Import from file..." in the top-right corner menu (the three dots) inside any empty workflow.
4. Upload each JSON file sequentially. 
5. Save each workflow.

**Method B (CLI):**
1. Copy the `.json` files to your Hetzner VPS (e.g., inside the `./local-files` volume your n8n has).
2. Attach to your n8n container or run the provided `import_workflows.sh` script using the n8n CLI.

## 2. Validation & Testing
Because the logic is pushed into the `lead-enricher-api` (HTTP Request nodes instead of complex local code nodes), these workflows are lightweight.
- Ensure the base URL resolves correctly. They default to `http://lead-enricher-api:8000/api/...`
- Open **01_import_batch**, manually inject dummy data into the HTTP Node, and click **Execute Node** to ensure the API responds.

## 3. Attach Credentials
- These files are credential-free. If your internal Core API ends up requiring an API header (e.g. `X-API-KEY`), open the HTTP Request nodes and add the header. You can use n8n's Credential Store to map a generic "Header Auth" credential to these nodes securely!

## 4. Activation
- In the top-right of your n8n UI, toggle the "Active" switch for any workflows requiring webhook listeners (like `01_import_batch` if you rely on the webhook trigger!). The `Execute Workflow` triggers do not need to be active to be called by a parent workflow.
