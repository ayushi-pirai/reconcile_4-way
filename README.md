## DWTC_simple – Bank Statement & Invoice Reconciliation

A Streamlit app for reconciling a general ledger with bank statements and validating invoices. Includes an OCR tester to quickly verify invoice parsing from PDFs.

### Files
- `app_invoice.py`: Main Streamlit application for end-to-end reconciliation and analysis.
- `ocr_invoice_tester.py`: Standalone OCR tester to upload invoice PDFs, preview them, and inspect extracted fields and raw OCR text.
- `reconciliation_42_200/` (optional, local example): Folder where you can place your own CSVs and invoice PDFs for the “Load from local directory” feature.
  - Expected CSV patterns (first match wins):
    - `*general_ledger*_recon.csv` or `*general_ledger*.csv`
    - `*bank_statement*_recon.csv` or `*bank_statement*.csv`
  - All `*.pdf` files inside are treated as invoices.

### What the main app does (`app_invoice.py`)
- Upload or load from directory:
  - General ledger (CSV/Excel)
  - Bank statements (CSV/Excel)
  - Invoices via PDFs (OCR) or CSV/Excel
- Reconcile ledger vs bank (amount/date tolerances) and ledger vs invoices
- Visualize summaries and export results
- Entry Explorer to view a specific ledger entry with linked bank/invoice details and preview the invoice
- OCR debug view to see extracted invoice fields and raw OCR text

### What the OCR tester does (`ocr_invoice_tester.py`)
- Upload one or more invoice PDFs
- Runs OCR and shows:
  - Parsed fields: `Invoice_ID`, `Vendor`, `Date`, `Amount`, `Currency`, `Description`
  - Raw OCR text
  - PDF preview (image of first page when possible; otherwise embedded PDF)
- Use this to quickly iterate on OCR parsing quality independently of the main app

## Setup

### 1) System dependencies (macOS)
```bash
brew install tesseract poppler
```

### 2) Python dependencies
```bash
python3 -m pip install --upgrade pip
python3 -m pip install streamlit pandas numpy matplotlib plotly pillow fpdf pytesseract pdf2image
```

### 3) Optional: Gemini summaries (Entry Explorer)
```bash
python3 -m pip install google-generativeai
export GEMINI_API_KEY=YOUR_API_KEY
# Optional: pick a model (default: gemini-1.5-flash)
export GEMINI_MODEL=gemini-1.5-flash
```

### 4) Point pytesseract to the Tesseract binary if needed
- Apple Silicon:
```bash
export TESSERACT_CMD=/opt/homebrew/bin/tesseract
```
- Intel:
```bash
export TESSERACT_CMD=/usr/local/bin/tesseract
```

## How to run

### Main app
```bash
streamlit run /Users/pi-in-166/Desktop/DWTC_simple/app_invoice.py
```

- Pages:
  - Upload Data: upload files or use “Load from local directory (OCR PDFs)” to point to a folder (defaults to `reconciliation_42_200`). When PDFs are present, invoice data is built via OCR. Shows an OCR debug section with the extracted table and raw OCR text.
  - Bank Reconciliation: metrics/charts + drilldowns.
  - Invoice Validation: metrics/charts + drilldowns and manual matching examples.
  - Entry Explorer: pick a ledger entry; see linked bank/invoice details, a summary (Gemini if configured), and invoice preview.
  - Analysis & Reports: timeline, amount distribution, top descriptions, and a downloadable report.

### OCR tester
```bash
streamlit run /Users/pi-in-166/Desktop/DWTC_simple/ocr_invoice_tester.py
```
- Upload any invoice PDF(s) to view parsed fields, raw text, and preview.

## Data expectations
- Ledger CSV minimal columns: `Date`, `Description`, `Reference`, `Debit`, `Credit`
- Bank CSV minimal columns: `Date`, `Description`, `Reference`, `Withdrawal`, `Deposit`
- Invoices via OCR: extracted fields include `Invoice_ID`, `Vendor`, `Date` (DD/MM/YYYY preferred), `Amount` (USD-only), `Description`, `Status`, and `Currency` (basic detection). Non-USD invoices are flagged and excluded from matching.

## Troubleshooting
- OCR not available / No module named 'pytesseract':
  - Install system deps: `brew install tesseract poppler`
  - Install Python deps: `pip install pytesseract pdf2image`
  - Set `TESSERACT_CMD` as above and restart Streamlit from the same shell
- Bad filename/preview errors:
  - Try the fallback embedded PDF (shown automatically) or re-upload.
- Missing columns (e.g., 'Vendor'):
  - App no longer groups on vendor; descriptions are used instead. If any place relies on vendor, it is derived from description for display only.
- OCR quality inconsistent across PDFs:
  - Try higher DPI (300–400) in the tester. See README “Strategies” below for production-grade approaches.

## Strategies for robust invoice parsing
- Hybrid pipeline: text-first (pdfplumber/pypdf), OCR fallback
- Adaptive multi-DPI OCR with early stopping; cache best DPI per template/vendor
- Layout-aware, anchor-proximity parsing using token positions (pdfplumber words or `pytesseract.image_to_data`)
- ROI (region) re-OCR around anchors at higher DPI for failing fields
- Image preprocessing (grayscale, adaptive threshold, denoise, deskew) + tuned Tesseract `psm`/`oem`
- Table extraction for totals (camelot/tabula) on last page
- Optional cloud parsers (Google Document AI, AWS Textract, Azure Form Recognizer)
- Human-in-the-loop for low-confidence cases

## Notes
- Tested on macOS; commands use absolute paths as examples.
- The “Load from local directory” option is a convenience to auto-load CSVs and OCR all PDFs in a folder. 