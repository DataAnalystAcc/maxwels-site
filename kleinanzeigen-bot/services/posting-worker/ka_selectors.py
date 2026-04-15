"""Kleinanzeigen CSS selectors — centralized for easy maintenance.

These selectors must be verified against the live site during Phase 4 
implementation and updated whenever the site layout changes.
"""

# Posting form selectors (illustrative — must be validated against live site)
SELECTORS = {
    # New listing page URL
    "new_listing_url": "https://www.kleinanzeigen.de/p-anzeige-aufgeben.html",

    # Form fields
    "title_input": "#postad-title",
    "description_input": "#pstad-descrptn",
    "price_input": "#pstad-price",
    "price_type_fixed": "#priceType-FIXED",
    "price_type_vb": "#priceType-NEGOTIABLE",
    "zip_input": "#pstad-zip",

    # Image upload
    "file_input": "input[type='file'][accept*='image']",

    # Submit
    "submit_button": "#pstad-submit",

    # Confirmation detection
    "success_indicator": "[class*='success'], [class*='confirm'], .message-success",

    # Login detection
    "login_indicator": "#login-form, [class*='login-form']",
    "account_page": "https://www.kleinanzeigen.de/m-meine-anzeigen.html",
}
