import streamlit as st
import pandas as pd
import os
import tempfile
import base64
from datetime import datetime

# OCR deps
try:
    import pytesseract
    from pdf2image import convert_from_path
    if os.getenv('TESSERACT_CMD'):
        pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD')
    OCR_AVAILABLE = True
    OCR_IMPORT_ERROR = ''
except Exception as e:
    OCR_AVAILABLE = False
    OCR_IMPORT_ERROR = str(e)

import re

st.set_page_config(page_title="Invoice OCR Tester", page_icon="🧪", layout="wide")
st.title("🧪 Invoice OCR Tester")

if not OCR_AVAILABLE:
    st.error(f"OCR not available. Install Tesseract and Poppler, and pip install pytesseract pdf2image. Details: {OCR_IMPORT_ERROR}")
    st.stop()

st.caption("Upload an invoice PDF to see extracted fields and raw OCR text.")

# Utilities

def ocr_text_from_pdf(file_path: str, dpi: int = 300) -> str:
    images = convert_from_path(file_path, dpi=dpi)
    text_pages = []
    for img in images:
        text_pages.append(pytesseract.image_to_string(img))
    return "\n".join(text_pages)


def parse_invoice_text(text: str) -> dict:
    text_norm = text.replace('\r', '\n')
    lines = [ln.strip() for ln in text_norm.split('\n') if ln.strip()]
    joined = "\n".join(lines)

    result = {}

    # Invoice ID
    m = re.search(r'Invoice\s*(?:No\.|Number|#)?\s*[:\-]?\s*([A-Za-z0-9\-]+)', joined, re.IGNORECASE)
    if m:
        result['Invoice_ID'] = m.group(1).strip()
    else:
        m2 = re.search(r'\bINV[\- _]?\d+\b', joined, re.IGNORECASE)
        if m2:
            result['Invoice_ID'] = m2.group(0).upper().replace(' ', '').replace('_', '-')

    # Vendor
    vendor_labels = ['From', 'Vendor', 'Supplier', 'Billed By', 'Bill From', 'Seller', 'Issued By']
    for label in vendor_labels:
        vm = re.search(rf'{label}\s*:\s*(.+)', joined, re.IGNORECASE)
        if vm:
            result['Vendor'] = vm.group(1).strip()
            break

    # Date (prefer DD/MM/YYYY)
    dm = re.search(r'Date\s*:\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})', joined, re.IGNORECASE)
    raw_date = dm.group(1) if dm else None
    if not raw_date:
        dm2 = re.search(r'\b([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})\b', joined)
        raw_date = dm2.group(1) if dm2 else None
    if raw_date:
        ts = pd.to_datetime(raw_date, errors='coerce', dayfirst=True)
        result['Date'] = ts.strftime('%Y-%m-%d') if pd.notnull(ts) else None

    # Currency
    currency = 'USD' if ('$' in joined) else None
    if not currency and re.search(r'\bAED\b|\bDhs\b|\bDirham\b|د\.إ', joined, re.IGNORECASE):
        currency = 'AED'
    result['Currency'] = currency or ''

    # Amount (USD only)
    amount_patterns = [
        r'(?:Total|Amount Due|Invoice Total|Total Amount|Balance Due)\s*[:]?\s*\$\s*([0-9\.,]+)',
        r'\$\s*([0-9\.,]+)\s*(?:Total|Amount Due|Invoice Total|Total Amount|Balance Due)'
    ]
    amt_val = None
    for pat in amount_patterns:
        am = re.search(pat, joined, re.IGNORECASE)
        if am:
            try:
                amt_val = float(am.group(1).replace(',', ''))
                break
            except Exception:
                pass
    if amt_val is None:
        all_amounts = [
            float(a.replace(',', ''))
            for a in re.findall(r'\$\s*([0-9\.,]+)', joined)
            if re.match(r'^\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?$|^\d+(?:\.\d{1,2})?$', a)
        ]
        if all_amounts:
            amt_val = max(all_amounts)
    if amt_val is not None:
        result['Amount'] = amt_val

    # Description
    dm = re.search(r'Description\s*:\s*(.+)', joined, re.IGNORECASE)
    if dm:
        result['Description'] = dm.group(1).strip()

    # Status placeholder
    result['Status'] = 'Paid'
    return result


def display_pdf_preview(file_path: str):
    # Try first page image; fallback to iframe
    try:
        imgs = convert_from_path(file_path, dpi=150, first_page=1, last_page=1)
        if imgs:
            st.image(imgs[0], caption=os.path.basename(file_path), use_column_width=True)
            with open(file_path, 'rb') as f:
                st.download_button("Download PDF", f.read(), file_name=os.path.basename(file_path), mime="application/pdf")
            return
    except Exception:
        pass
    try:
        with open(file_path, 'rb') as f:
            b64_pdf = base64.b64encode(f.read()).decode('utf-8')
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600"></iframe>', unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Preview failed: {e}")

# UI
uploaded = st.file_uploader("Upload invoice PDF(s)", type=['pdf'], accept_multiple_files=True)
dpi = st.slider("OCR DPI", min_value=150, max_value=400, value=300, step=50)

if uploaded:
    rows = []
    for uf in uploaded:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(uf.getbuffer())
            tmp_path = tmp.name
        with st.expander(f"{uf.name}", expanded=True):
            try:
                text = ocr_text_from_pdf(tmp_path, dpi=dpi)
                parsed = parse_invoice_text(text)
                st.markdown("**Parsed Fields**")
                st.json(parsed)
                st.markdown("**Raw OCR Text**")
                st.text_area("", text, height=250)
                st.markdown("**Preview**")
                display_pdf_preview(tmp_path)
            except Exception as e:
                st.error(f"OCR failed: {e}")
        rows.append({
            'Source': uf.name,
            'Invoice_ID': parsed.get('Invoice_ID') if 'parsed' in locals() else '',
            'Vendor': parsed.get('Vendor') if 'parsed' in locals() else '',
            'Date': parsed.get('Date') if 'parsed' in locals() else '',
            'Amount': parsed.get('Amount') if 'parsed' in locals() else '',
            'Currency': parsed.get('Currency') if 'parsed' in locals() else '',
            'Description': parsed.get('Description') if 'parsed' in locals() else ''
        })
    st.markdown("---")
    st.subheader("Summary Table")
    st.dataframe(pd.DataFrame(rows))
else:
    st.info("Upload one or more PDF invoices to begin.") 