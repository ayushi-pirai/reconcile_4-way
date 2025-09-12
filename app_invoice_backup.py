import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import csv
import base64
import json
import hashlib
from fpdf import FPDF
import tempfile
import os
# Try to enable OCR dependencies
try:
    import pytesseract
    from pdf2image import convert_from_path
    # Allow overriding tesseract binary path via env var
    if os.getenv('TESSERACT_CMD'):
        pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_CMD')
    OCR_AVAILABLE = True
except Exception as _ocr_e:
    OCR_AVAILABLE = False
    OCR_IMPORT_ERROR = str(_ocr_e)

# Optional Gemini for summaries
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
    if os.getenv('GEMINI_API_KEY'):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    else:
        GEMINI_AVAILABLE = False
except Exception as _gem_e:
    GEMINI_AVAILABLE = False
    GEMINI_IMPORT_ERROR = str(_gem_e)

import re
import glob

# Set page configuration
st.set_page_config(
    page_title="Bank Statement & Invoice Reconciliation",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("🏦 Bank Statement & Invoice Reconciliation")
st.markdown("""
This tool helps you reconcile your ledger entries with bank statements and validate invoices against ledger entries.
Upload your ledger data, bank statements, and invoices to identify matches, discrepancies, and unmatched transactions.
""")

# Sidebar for navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Upload Data", "Bank Reconciliation", "Invoice Validation", "Entry Explorer", "Analysis & Reports"])

# Sample data generation function
def generate_sample_data():
    # Generate sample ledger data
    ledger_data = {
        'Date': [datetime(2023, 10, i).strftime('%Y-%m-%d') for i in range(1, 16)],
        'Description': [
            'Office Supplies - Office Depot', 'Client Payment - ABC Corp', 'Utility Bill - Electric Company', 
            'Software Subscription - Adobe Inc', 'Client Payment - XYZ Ltd', 'Rent Payment - Property Management Co',
            'Equipment Purchase - Tech Store', 'Consulting Fee - John Smith', 'Marketing Services - Marketing Solutions Inc',
            'Travel Expenses - Airline Company', 'Client Refund - ABC Corp', 'Insurance Payment - Insurance Co', 
            'Website Hosting - Web Services Inc', 'Professional Development - Training Co', 'Miscellaneous Expenses - Various'
        ],
        'Reference': ['INV-100{}'.format(i) for i in range(1, 16)],
        'Vendor': [
            'Office Depot', 'ABC Corp', 'Electric Company', 'Adobe Inc', 'XYZ Ltd', 
            'Property Management Co', 'Tech Store', 'John Smith', 'Marketing Solutions Inc',
            'Airline Company', 'ABC Corp', 'Insurance Co', 'Web Services Inc', 'Training Co', 'Various'
        ],
        'Debit': [0] * 15,
        'Credit': [
            250.00, 5000.00, 350.50, 199.99, 7500.00, 2000.00, 1200.00, 
            1500.00, 850.25, 450.75, 200.00, 350.00, 99.99, 300.00, 150.50
        ],
        'Account': ['Cash at Bank'] * 15
    }
    
    # Generate sample bank statement data
    bank_data = {
        'Date': [datetime(2023, 10, i).strftime('%Y-%m-%d') for i in [1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 13, 14, 15]],
        'Description': [
            'OFFICE DEPOT', 'ABC CORP', 'ELECTRIC COMPANY', 
            'ADOBE INC', 'XYZ LTD', 'PROPERTY MGMT CO', 'TECH STORE',
            'JOHN SMITH', 'MARKETING SOLUTIONS INC', 'AIRLINE CO', 
            'ABC CORP REFUND', 'INSURANCE CO', 'WEB SERVICES INC'
        ],
        'Reference': ['CHK{}'.format(1000 + i) for i in range(1, 14)],
        'Withdrawal': [
            250.00, 0, 350.50, 199.99, 0, 2000.00, 1200.00, 
            0, 850.25, 450.75, 0, 350.00, 99.99
        ],
        'Deposit': [
            0, 5000.00, 0, 0, 7500.00, 0, 0, 
            1500.00, 0, 0, 200.00, 0, 0
        ],
        'Balance': [5000.00, 10000.00, 9649.50, 9449.51, 16949.51, 14949.51, 13749.51, 
                   15249.51, 14399.26, 13948.51, 14148.51, 13798.51, 13698.52]
    }
    
    # Generate sample invoice data
    invoice_data = {
        'Invoice_ID': ['INV-100{}'.format(i) for i in range(1, 16)],
        'Date': [datetime(2023, 10, i).strftime('%Y-%m-%d') for i in range(1, 16)],
        'Vendor': [
            'Office Depot', 'ABC Corp', 'Electric Company', 'Adobe Inc', 'XYZ Ltd', 
            'Property Management Co', 'Tech Store', 'John Smith', 'Marketing Solutions Inc',
            'Airline Company', 'ABC Corp', 'Insurance Co', 'Web Services Inc', 'Training Co', 'Various Suppliers'
        ],
        'Amount': [
            250.00, 5000.00, 350.50, 199.99, 7500.00, 2000.00, 1200.00, 
            1500.00, 850.25, 450.75, 200.00, 350.00, 99.99, 300.00, 150.50
        ],
        'Description': [
            'Office Supplies', 'Product Payment', 'Monthly Electricity Bill', 
            'Software Subscription', 'Service Payment', 'Office Rent', 
            'Computer Equipment', 'Consulting Services', 'Marketing Campaign',
            'Business Travel', 'Customer Refund', 'Insurance Premium', 
            'Web Hosting Services', 'Training Course', 'Miscellaneous Expenses'
        ],
        'Status': ['Paid'] * 15
    }
    
    ledger_df = pd.DataFrame(ledger_data)
    bank_df = pd.DataFrame(bank_data)
    invoice_df = pd.DataFrame(invoice_data)
    
    return ledger_df, bank_df, invoice_df

# Matching algorithm for bank transactions
def match_bank_transactions(ledger_df, bank_df):
    # Initialize result columns
    ledger_df['Bank_Status'] = 'Not Matched'
    ledger_df['Matched_Bank_Index'] = -1
    ledger_df['Bank_Discrepancy_Type'] = ''
    ledger_df['Bank_Discrepancy_Amount'] = 0.0
    ledger_df['AI_Flag'] = ''
    
    bank_df['Status'] = 'Not Matched'
    bank_df['Matched_Ledger_Index'] = -1
    
    # Create copies for matching
    ledger_copy = ledger_df.copy()
    bank_copy = bank_df.copy()
    
    # First pass: Exact amount and date matching
    for l_idx, ledger_row in ledger_copy.iterrows():
        ledger_amount = ledger_row['Credit'] if ledger_row['Credit'] > 0 else ledger_row['Debit']
        ledger_date = datetime.strptime(ledger_row['Date'], '%Y-%m-%d')
        
        for b_idx, bank_row in bank_copy.iterrows():
            bank_amount = bank_row['Deposit'] if bank_row['Deposit'] > 0 else bank_row['Withdrawal']
            bank_date = datetime.strptime(bank_row['Date'], '%Y-%m-%d')
            
            # Check for exact match
            if abs(ledger_amount - bank_amount) < 0.01 and abs((ledger_date - bank_date).days) <= 2:
                ledger_df.at[l_idx, 'Bank_Status'] = 'Matched'
                ledger_df.at[l_idx, 'Matched_Bank_Index'] = b_idx
                bank_df.at[b_idx, 'Status'] = 'Matched'
                bank_df.at[b_idx, 'Matched_Ledger_Index'] = l_idx
                bank_copy.drop(b_idx, inplace=True)
                break
    
    # Second pass: Amount matching with date tolerance
    for l_idx, ledger_row in ledger_copy[ledger_df['Bank_Status'] == 'Not Matched'].iterrows():
        ledger_amount = ledger_row['Credit'] if ledger_row['Credit'] > 0 else ledger_row['Debit']
        ledger_date = datetime.strptime(ledger_row['Date'], '%Y-%m-%d')
        
        for b_idx, bank_row in bank_copy[bank_df['Status'] == 'Not Matched'].iterrows():
            bank_amount = bank_row['Deposit'] if bank_row['Deposit'] > 0 else bank_row['Withdrawal']
            bank_date = datetime.strptime(bank_row['Date'], '%Y-%m-%d')
            
            # Check for amount match with date discrepancy
            if abs(ledger_amount - bank_amount) < 0.01 and abs((ledger_date - bank_date).days) <= 7:
                ledger_df.at[l_idx, 'Bank_Status'] = 'Discrepancy Detected'
                ledger_df.at[l_idx, 'Matched_Bank_Index'] = b_idx
                ledger_df.at[l_idx, 'Bank_Discrepancy_Type'] = 'Date Variance'
                ledger_df.at[l_idx, 'Bank_Discrepancy_Amount'] = abs((ledger_date - bank_date).days)
                bank_df.at[b_idx, 'Status'] = 'Discrepancy Detected'
                bank_df.at[b_idx, 'Matched_Ledger_Index'] = l_idx
                bank_copy.drop(b_idx, inplace=True)
                break
            # Check for date match with amount discrepancy
            elif abs((ledger_date - bank_date).days) <= 2 and abs(ledger_amount - bank_amount) >= 0.01:
                ledger_df.at[l_idx, 'Bank_Status'] = 'Discrepancy Detected'
                ledger_df.at[l_idx, 'Matched_Bank_Index'] = b_idx
                ledger_df.at[l_idx, 'Bank_Discrepancy_Type'] = 'Amount Variance'
                ledger_df.at[l_idx, 'Bank_Discrepancy_Amount'] = abs(ledger_amount - bank_amount)
                bank_df.at[b_idx, 'Status'] = 'Discrepancy Detected'
                bank_df.at[b_idx, 'Matched_Ledger_Index'] = l_idx
                bank_copy.drop(b_idx, inplace=True)
                break
    
    # AI Flagging (simplified)
    for l_idx, ledger_row in ledger_df.iterrows():
        flags = []
        ledger_amount = ledger_row['Credit'] if ledger_row['Credit'] > 0 else ledger_row['Debit']
        
        # Check for potential duplicates
        similar_entries = ledger_df[
            (ledger_df['Description'] == ledger_row['Description']) & 
            (abs(ledger_df['Credit'] - ledger_row['Credit']) < 0.01) &
            (ledger_df.index != l_idx)
        ]
        if len(similar_entries) > 0:
            flags.append('Possible Duplicate')
        
        # Check for round numbers (potential errors)
        if ledger_amount % 100 == 0:
            flags.append('Round Amount - Verify')
            
        # Check for large transactions
        if ledger_amount > 5000:
            flags.append('Large Transaction')
        
        if flags:
            ledger_df.at[l_idx, 'AI_Flag'] = ', '.join(flags)
    
    return ledger_df, bank_df

# Matching algorithm for invoice validation
def match_invoice_validation(ledger_df, invoice_df):
    # Initialize result columns
    ledger_df['Invoice_Status'] = 'Pending Match'
    ledger_df['Matched_Invoice_ID'] = ''
    ledger_df['Invoice_Discrepancy_Type'] = ''
    ledger_df['Invoice_Discrepancy_Amount'] = 0.0
    ledger_df['Invoice_Notes'] = ''
    
    invoice_df['Ledger_Status'] = 'Pending Match'
    invoice_df['Matched_Ledger_Index'] = -1
    
    # Create copies for matching
    ledger_copy = ledger_df.copy()
    invoice_copy = invoice_df.copy()
    
    # First pass: Exact amount and vendor matching
    for l_idx, ledger_row in ledger_copy.iterrows():
        ledger_amount = ledger_row['Credit'] if ledger_row['Credit'] > 0 else ledger_row['Debit']
        ledger_vendor = str(ledger_row.get('Vendor') or ((ledger_row.get('Description') or '').split(' - ')[-1] if isinstance(ledger_row.get('Description'), str) else '')).strip()
        ledger_date = datetime.strptime(ledger_row['Date'], '%Y-%m-%d')
        
        for i_idx, invoice_row in invoice_copy.iterrows():
            invoice_amount = invoice_row['Amount']
            invoice_vendor = invoice_row['Vendor']
            invoice_date = datetime.strptime(invoice_row['Date'], '%Y-%m-%d')
            
            # Check for exact match
            if (abs(ledger_amount - invoice_amount) < 0.01 and 
                ledger_vendor.lower() == str(invoice_vendor).lower() and
                abs((ledger_date - invoice_date).days) <= 2):
                
                ledger_df.at[l_idx, 'Invoice_Status'] = 'Matched'
                ledger_df.at[l_idx, 'Matched_Invoice_ID'] = invoice_row['Invoice_ID']
                invoice_df.at[i_idx, 'Ledger_Status'] = 'Matched'
                invoice_df.at[i_idx, 'Matched_Ledger_Index'] = l_idx
                invoice_copy.drop(i_idx, inplace=True)
                break
    
    # Second pass: Fuzzy matching with tolerances
    for l_idx, ledger_row in ledger_copy[ledger_df['Invoice_Status'] == 'Pending Match'].iterrows():
        ledger_amount = ledger_row['Credit'] if ledger_row['Credit'] > 0 else ledger_row['Debit']
        ledger_vendor = str(ledger_row.get('Vendor') or ((ledger_row.get('Description') or '').split(' - ')[-1] if isinstance(ledger_row.get('Description'), str) else '')).strip()
        ledger_date = datetime.strptime(ledger_row['Date'], '%Y-%m-%d')
        
        for i_idx, invoice_row in invoice_copy[invoice_df['Ledger_Status'] == 'Pending Match'].iterrows():
            invoice_amount = invoice_row['Amount']
            invoice_vendor = invoice_row['Vendor']
            invoice_date = datetime.strptime(invoice_row['Date'], '%Y-%m-%d')
            
            # Check for amount match with vendor match but date discrepancy
            if (abs(ledger_amount - invoice_amount) < 0.01 and 
                ledger_vendor.lower() == str(invoice_vendor).lower() and
                abs((ledger_date - invoice_date).days) <= 7):
                
                ledger_df.at[l_idx, 'Invoice_Status'] = 'Discrepancy Detected'
                ledger_df.at[l_idx, 'Matched_Invoice_ID'] = invoice_row['Invoice_ID']
                ledger_df.at[l_idx, 'Invoice_Discrepancy_Type'] = 'Date Variance'
                ledger_df.at[l_idx, 'Invoice_Discrepancy_Amount'] = abs((ledger_date - invoice_date).days)
                invoice_df.at[i_idx, 'Ledger_Status'] = 'Discrepancy Detected'
                invoice_df.at[i_idx, 'Matched_Ledger_Index'] = l_idx
                invoice_copy.drop(i_idx, inplace=True)
                break
            
            # Check for vendor match with amount discrepancy
            elif (ledger_vendor.lower() == str(invoice_vendor).lower() and
                  abs((ledger_date - invoice_date).days) <= 2 and
                  abs(ledger_amount - invoice_amount) >= 0.01):
                
                ledger_df.at[l_idx, 'Invoice_Status'] = 'Discrepancy Detected'
                ledger_df.at[l_idx, 'Matched_Invoice_ID'] = invoice_row['Invoice_ID']
                ledger_df.at[l_idx, 'Invoice_Discrepancy_Type'] = 'Amount Variance'
                ledger_df.at[l_idx, 'Invoice_Discrepancy_Amount'] = abs(ledger_amount - invoice_amount)
                invoice_df.at[i_idx, 'Ledger_Status'] = 'Discrepancy Detected'
                invoice_df.at[i_idx, 'Matched_Ledger_Index'] = l_idx
                invoice_copy.drop(i_idx, inplace=True)
                break
            
            # Check for fuzzy vendor match with amount and date match
            elif (abs(ledger_amount - invoice_amount) < 0.01 and
                  abs((ledger_date - invoice_date).days) <= 2 and
                  (ledger_vendor.lower() in str(invoice_vendor).lower() or str(invoice_vendor).lower() in ledger_vendor.lower())):
                
                ledger_df.at[l_idx, 'Invoice_Status'] = 'Matched'
                ledger_df.at[l_idx, 'Matched_Invoice_ID'] = invoice_row['Invoice_ID']
                ledger_df.at[l_idx, 'Invoice_Notes'] = 'Fuzzy vendor name match'
                invoice_df.at[i_idx, 'Ledger_Status'] = 'Matched'
                invoice_df.at[i_idx, 'Matched_Ledger_Index'] = l_idx
                invoice_df.at[i_idx, 'Notes'] = 'Fuzzy vendor name match'
                invoice_copy.drop(i_idx, inplace=True)
                break
    
    return ledger_df, invoice_df

# Function to create download links
def get_table_download_link(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download {filename}</a>'
    return href

# Function to create a sample PDF invoice
def create_sample_invoice(invoice_id, vendor, amount, date, description):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Invoice header
    pdf.cell(200, 10, txt=f"INVOICE {invoice_id}", ln=1, align='C')
    pdf.ln(10)
    
    # Vendor information
    pdf.cell(200, 10, txt=f"From: {vendor}", ln=1, align='L')
    pdf.ln(5)
    
    # Invoice details
    pdf.cell(200, 10, txt=f"Date: {date}", ln=1, align='L')
    pdf.cell(200, 10, txt=f"Description: {description}", ln=1, align='L')
    pdf.cell(200, 10, txt=f"Amount: ${amount:.2f}", ln=1, align='L')
    pdf.ln(10)
    
    # Payment terms
    pdf.cell(200, 10, txt="Payment Terms: Net 30", ln=1, align='L')
    
    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, f"{invoice_id}.pdf")
    pdf.output(file_path)
    
    return file_path

# Generate sample invoices
def generate_sample_invoices(invoice_df):
    invoice_files = {}
    for _, row in invoice_df.iterrows():
        file_path = create_sample_invoice(
            row['Invoice_ID'], 
            row['Vendor'], 
            row['Amount'], 
            row['Date'], 
            row['Description']
        )
        invoice_files[row['Invoice_ID']] = file_path
    return invoice_files

# OCR helpers to extract invoice data from PDFs
def ocr_text_from_pdf(file_path, dpi=300):
    if not OCR_AVAILABLE:
        raise RuntimeError(f"OCR dependencies missing: {OCR_IMPORT_ERROR}")
    images = convert_from_path(file_path, dpi=dpi)
    text_pages = []
    for img in images:
        text_pages.append(pytesseract.image_to_string(img))
    return "\n".join(text_pages)

# PDF Preview helpers (Chrome-compatible)
def display_pdf_preview(file_path):
    # Try image preview of first page; fallback to HTML embed
    try:
        # Only attempt image preview if pdf2image is available
        if OCR_AVAILABLE:
            imgs = convert_from_path(file_path, dpi=150, first_page=1, last_page=1)
            if imgs:
                st.image(imgs[0], caption=os.path.basename(file_path), use_column_width=True)
                with open(file_path, 'rb') as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="Download Invoice PDF",
                    data=pdf_bytes,
                    file_name=os.path.basename(file_path),
                    mime="application/pdf"
                )
                return
    except Exception:
        pass
    # Fallback: embed PDF in an iframe
    try:
        with open(file_path, 'rb') as f:
            b64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Unable to preview PDF: {e}")

# Optional Gemini summary
def generate_entry_summary(ledger_row: pd.Series, bank_row: pd.Series | None, invoice_row: pd.Series | None) -> str:
    # Compose a concise prompt
    def fmt_amount(x):
        try:
            return f"${float(x):.2f}"
        except Exception:
            return str(x)
    ledger_amt = max(ledger_row.get('Debit', 0.0), ledger_row.get('Credit', 0.0))
    bank_amt = None
    if bank_row is not None:
        bank_amt = max(bank_row.get('Deposit', 0.0), bank_row.get('Withdrawal', 0.0))
    invoice_amt = invoice_row.get('Amount') if invoice_row is not None else None
    prompt = f"""
    Provide a concise 3-5 sentence reconciliation summary for one entry.
    Ledger: Date={ledger_row.get('Date')}, Ref={ledger_row.get('Reference')}, Vendor={ledger_row.get('Vendor')}, Amount={fmt_amount(ledger_amt)}, Desc={ledger_row.get('Description')}.
    Bank: {('Date='+str(bank_row.get('Date'))+', Ref='+str(bank_row.get('Reference'))+', Amount='+fmt_amount(bank_amt)) if bank_row is not None else 'None'}.
    Invoice: {('ID='+str(invoice_row.get('Invoice_ID'))+', Vendor='+str(invoice_row.get('Vendor'))+', Date='+str(invoice_row.get('Date'))+', Amount='+fmt_amount(invoice_amt)) if invoice_row is not None else 'None'}.
    Also mention statuses: Bank_Status={ledger_row.get('Bank_Status')}, Invoice_Status={ledger_row.get('Invoice_Status')}.
    """
    if GEMINI_AVAILABLE:
        try:
            model = genai.GenerativeModel(model_name=os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'))
            resp = model.generate_content(prompt)
            if hasattr(resp, 'text') and resp.text:
                return resp.text
        except Exception:
            pass
    # Fallback heuristic summary
    parts = []
    parts.append(f"Ledger {ledger_row.get('Reference')} on {ledger_row.get('Date')} for {fmt_amount(ledger_amt)} ({ledger_row.get('Vendor')}).")
    if bank_row is not None:
        parts.append(f"Bank entry on {bank_row.get('Date')} for {fmt_amount(bank_amt)} matched.")
    else:
        parts.append("No matching bank entry.")
    if invoice_row is not None:
        parts.append(f"Invoice {invoice_row.get('Invoice_ID')} dated {invoice_row.get('Date')} for {fmt_amount(invoice_amt)}.")
    else:
        parts.append("No matching invoice.")
    parts.append(f"Statuses: Bank={ledger_row.get('Bank_Status')}, Invoice={ledger_row.get('Invoice_Status')}.")
    return " ".join(parts)


def parse_invoice_text(text):
    # Normalize text
    text_norm = text.replace('\r', '\n')
    lines = [ln.strip() for ln in text_norm.split('\n') if ln.strip()]
    joined = "\n".join(lines)

    result = {}

    # 1) Invoice ID: try explicit patterns, else INV-xxxx
    m = re.search(r'Invoice\s*(?:No\.|Number|#)?\s*[:\-]?\s*([A-Za-z0-9\-]+)', joined, re.IGNORECASE)
    if m:
        result['Invoice_ID'] = m.group(1).strip()
    else:
        m2 = re.search(r'\bINV[\- _]?\d+\b', joined, re.IGNORECASE)
        if m2:
            result['Invoice_ID'] = m2.group(0).upper().replace(' ', '').replace('_', '-')

    # 2) Vendor: look for common labels
    vendor_labels = ['From', 'Vendor', 'Supplier', 'Billed By', 'Bill From', 'Seller', 'Issued By']
    for label in vendor_labels:
        vm = re.search(rf'{label}\s*:\s*(.+)', joined, re.IGNORECASE)
        if vm:
            result['Vendor'] = vm.group(1).strip()
            break

    # 3) Date: prefer DD/MM/YYYY occurrences
    # Capture the first plausible date near any date label, else first dd/mm/yyyy occurrence
    dm = re.search(r'Date\s*:\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})', joined, re.IGNORECASE)
    if dm:
        raw_date = dm.group(1)
    else:
        dm2 = re.search(r'\b([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})\b', joined)
        raw_date = dm2.group(1) if dm2 else None
    if raw_date:
        ts = pd.to_datetime(raw_date, errors='coerce', dayfirst=True)
        result['Date'] = ts.strftime('%Y-%m-%d') if pd.notnull(ts) else None

    # 4) Amount ($ only): look for labeled totals first
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
        # Fall back: take the largest $ amount in the document
        all_amounts = [
            float(a.replace(',', ''))
            for a in re.findall(r'\$\s*([0-9\.,]+)', joined)
            if re.match(r'^\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?$|^\d+(?:\.\d{1,2})?$', a)
        ]
        if all_amounts:
            amt_val = max(all_amounts)
    if amt_val is not None:
        result['Amount'] = amt_val

    # 5) Description: try label; else empty
    dm = re.search(r'Description\s*:\s*(.+)', joined, re.IGNORECASE)
    if dm:
        result['Description'] = dm.group(1).strip()

    return result


def extract_invoice_data_from_pdf(file_path):
    text = ocr_text_from_pdf(file_path)
    parsed = parse_invoice_text(text)
    return parsed


def extract_invoice_df_from_files(invoice_files):
    records = []
    for invoice_id_key, file_path in invoice_files.items():
        try:
            parsed = extract_invoice_data_from_pdf(file_path)
        except Exception:
            parsed = {}
        record = {
            'Invoice_ID': parsed.get('Invoice_ID') or invoice_id_key,
            'Date': parsed.get('Date') or datetime.now().strftime('%Y-%m-%d'),
            'Vendor': parsed.get('Vendor') or '',
            'Amount': parsed.get('Amount') or 0.0,
            'Description': parsed.get('Description') or '',
            'Status': 'Paid'
        }
        records.append(record)
    return pd.DataFrame(records)


def ensure_ledger_vendor_column(df: pd.DataFrame) -> pd.DataFrame:
    if 'Vendor' in df.columns:
        return df
    df = df.copy()
    desc_series = df['Description'] if 'Description' in df.columns else pd.Series([''] * len(df))
    vendors = []
    for desc in desc_series:
        vendor_guess = ''
        if isinstance(desc, str) and ' - ' in desc:
            parts = [p.strip() for p in desc.split(' - ') if p.strip()]
            if parts:
                vendor_guess = parts[-1]
        vendors.append(vendor_guess)
    df['Vendor'] = vendors
    return df


def discover_data_in_directory(dir_path):
    # Find ledger and bank CSVs
    ledger_path = None
    bank_path = None
    # Prefer *_recon.csv if present
    cand_ledger = glob.glob(os.path.join(dir_path, '*general_ledger*_recon.csv')) or \
                  glob.glob(os.path.join(dir_path, '*general_ledger*.csv'))
    cand_bank = glob.glob(os.path.join(dir_path, '*bank_statement*_recon.csv')) or \
                glob.glob(os.path.join(dir_path, '*bank_statement*.csv'))
    if cand_ledger:
        ledger_path = cand_ledger[0]
    if cand_bank:
        bank_path = cand_bank[0]

    # Collect PDFs as invoices
    pdf_paths = glob.glob(os.path.join(dir_path, '*.pdf'))
    invoice_files = {os.path.splitext(os.path.basename(p))[0]: p for p in pdf_paths}

    return ledger_path, bank_path, invoice_files

# Main app logic
if page == "Upload Data":
    st.header("Upload Data")
    
    # Option to use sample data or upload files
    use_sample_data = st.checkbox("Use sample data for demonstration", value=True)
    
    if use_sample_data:
        ledger_df, bank_df, invoice_df = generate_sample_data()
        st.success("Sample data loaded successfully!")
        
        # Display sample data
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Sample Ledger Data")
            st.dataframe(ledger_df.head())
        with col2:
            st.subheader("Sample Bank Statement Data")
            st.dataframe(bank_df.head())
        with col3:
            st.subheader("Sample Invoice Data")
            st.dataframe(invoice_df.head())
            
        # Save to session state
        st.session_state.ledger_df = ledger_df
        st.session_state.bank_df = bank_df
        st.session_state.invoice_df = invoice_df
        
        # Generate sample invoices
        st.session_state.invoice_files = generate_sample_invoices(invoice_df)
        # Extract invoice data from generated PDFs via OCR and overwrite invoice_df
        if OCR_AVAILABLE:
            try:
                ocr_invoice_df = extract_invoice_df_from_files(st.session_state.invoice_files)
                st.session_state.invoice_df = ocr_invoice_df
                st.info("Invoice data populated from sample PDF files via OCR.")
            except Exception as e:
                st.warning(f"OCR failed to extract invoice data from sample PDFs: {e}")
        else:
            st.warning(f"OCR not available. Install Tesseract and Poppler to enable PDF invoice parsing. Details: {OCR_IMPORT_ERROR if 'OCR_IMPORT_ERROR' in globals() else ''}")
        
        # Download sample data
        st.markdown("### Download Sample Data")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(get_table_download_link(ledger_df, "sample_ledger.csv"), unsafe_allow_html=True)
        with col2:
            st.markdown(get_table_download_link(bank_df, "sample_bank_statement.csv"), unsafe_allow_html=True)
        with col3:
            st.markdown(get_table_download_link(st.session_state.invoice_df, "sample_invoices_from_pdf.csv"), unsafe_allow_html=True)
            
    else:
        st.subheader("Upload your files")
        uploaded_ledger = st.file_uploader("Upload Ledger File (CSV or Excel)", type=['csv', 'xlsx'])
        uploaded_bank = st.file_uploader("Upload Bank Statement (CSV or Excel)", type=['csv', 'xlsx'])
        uploaded_invoices = st.file_uploader("Upload Invoice Data (CSV or Excel)", type=['csv', 'xlsx'])
        uploaded_invoice_files = st.file_uploader("Upload Invoice PDFs", type=['pdf'], accept_multiple_files=True)
        
        if uploaded_ledger and uploaded_bank and (uploaded_invoices or uploaded_invoice_files):
            ledger_df = pd.read_csv(uploaded_ledger) if uploaded_ledger.name.endswith('.csv') else pd.read_excel(uploaded_ledger)
            bank_df = pd.read_csv(uploaded_bank) if uploaded_bank.name.endswith('.csv') else pd.read_excel(uploaded_bank)
            
            # Normalize ledger to ensure Vendor exists
            ledger_df = ensure_ledger_vendor_column(ledger_df)
            
            st.session_state.ledger_df = ledger_df
            st.session_state.bank_df = bank_df
            
            # Prefer PDFs for invoice data when provided; otherwise use uploaded CSV/Excel
            if uploaded_invoices and not uploaded_invoice_files:
                invoice_df = pd.read_csv(uploaded_invoices) if uploaded_invoices.name.endswith('.csv') else pd.read_excel(uploaded_invoices)
                st.session_state.invoice_df = invoice_df
            
            # Handle uploaded invoice PDFs (preferred)
            if uploaded_invoice_files:
                invoice_files = {}
                for uploaded_file in uploaded_invoice_files:
                    # Save to temporary location
                    temp_dir = tempfile.mkdtemp()
                    file_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    invoice_files[uploaded_file.name.replace('.pdf', '')] = file_path
                st.session_state.invoice_files = invoice_files

                if OCR_AVAILABLE:
                    try:
                        st.session_state.invoice_df = extract_invoice_df_from_files(invoice_files)
                        st.info("Invoice data extracted from uploaded PDFs via OCR.")
                    except Exception as e:
                        st.warning(f"OCR failed to extract invoice data from PDFs: {e}")
                else:
                    st.warning(f"OCR not available. Install Tesseract and Poppler to enable PDF invoice parsing. Details: {OCR_IMPORT_ERROR if 'OCR_IMPORT_ERROR' in globals() else ''}")
            
            st.success("Files uploaded successfully!")
        
        st.markdown("---")
        st.subheader("Load from local directory (OCR PDFs)")
        default_dir = "/Users/pi-in-166/Desktop/DWTC_simple/reconciliation_42_200"
        dir_path = st.text_input("Directory path", value=default_dir)
        if st.button("Load from directory"):
            if not os.path.isdir(dir_path):
                st.error("Directory does not exist.")
            else:
                ledger_path, bank_path, invoice_files = discover_data_in_directory(dir_path)
                if not ledger_path or not bank_path:
                    st.error("Could not find ledger/bank CSVs in the directory.")
                else:
                    try:
                        ledger_df = pd.read_csv(ledger_path)
                    except Exception:
                        ledger_df = pd.read_excel(ledger_path)
                    try:
                        bank_df = pd.read_csv(bank_path)
                    except Exception:
                        bank_df = pd.read_excel(bank_path)
                    # Normalize ledger to ensure Vendor exists
                    ledger_df = ensure_ledger_vendor_column(ledger_df)
                    st.session_state.ledger_df = ledger_df
                    st.session_state.bank_df = bank_df
                    st.session_state.invoice_files = invoice_files
                    if not invoice_files:
                        st.warning("No invoice PDFs found in the directory.")
                    if OCR_AVAILABLE and invoice_files:
                        try:
                            st.session_state.invoice_df = extract_invoice_df_from_files(invoice_files)
                            st.success("Loaded CSVs and extracted invoice data from PDFs via OCR.")
                        except Exception as e:
                            st.warning(f"OCR failed to extract invoice data from PDFs: {e}")
                    elif invoice_files:
                        st.warning(f"OCR not available. Install Tesseract and Poppler to enable PDF invoice parsing. Details: {OCR_IMPORT_ERROR if 'OCR_IMPORT_ERROR' in globals() else ''}")

    # Process button
    if st.button("Process Reconciliation") and 'ledger_df' in st.session_state and 'bank_df' in st.session_state and 'invoice_df' in st.session_state:
        with st.spinner("Processing transactions..."):
            # Process bank reconciliation
            ledger_result, bank_result = match_bank_transactions(
                st.session_state.ledger_df, 
                st.session_state.bank_df
            )
            st.session_state.ledger_result = ledger_result
            st.session_state.bank_result = bank_result
            
            # Process invoice validation
            ledger_invoice_result, invoice_result = match_invoice_validation(
                st.session_state.ledger_df,
                st.session_state.invoice_df
            )
            st.session_state.ledger_invoice_result = ledger_invoice_result
            st.session_state.invoice_result = invoice_result
            
            st.session_state.processed = True
            st.success("Reconciliation completed!")

elif page == "Bank Reconciliation":
    st.header("Bank Reconciliation")
    
    if 'processed' not in st.session_state:
        st.warning("Please process data first on the Upload Data page.")
    else:
        ledger_result = st.session_state.ledger_result
        bank_result = st.session_state.bank_result
        
        # Summary visualization
        st.subheader("Reconciliation Summary")
        col1, col2, col3 = st.columns(3)
        
        matched_count = len(ledger_result[ledger_result['Bank_Status'] == 'Matched'])
        discrepancy_count = len(ledger_result[ledger_result['Bank_Status'] == 'Discrepancy Detected'])
        unmatched_count = len(ledger_result[ledger_result['Bank_Status'] == 'Not Matched'])
        total_count = len(ledger_result)
        
        with col1:
            st.metric("Matched Transactions", f"{matched_count}/{total_count}", 
                     f"{matched_count/total_count*100:.1f}%")
        with col2:
            st.metric("Discrepancies", f"{discrepancy_count}/{total_count}", 
                     f"{discrepancy_count/total_count*100:.1f}%", delta_color="inverse")
        with col3:
            st.metric("Unmatched Transactions", f"{unmatched_count}/{total_count}", 
                     f"{unmatched_count/total_count*100:.1f}%", delta_color="off")
        
        # Create pie chart
        fig = px.pie(
            values=[matched_count, discrepancy_count, unmatched_count],
            names=['Matched', 'Discrepancies', 'Unmatched'],
            title='Bank Transaction Reconciliation Status',
            color=['Matched', 'Discrepancies', 'Unmatched'],
            color_discrete_map={'Matched':'green', 'Discrepancies':'orange', 'Unmatched':'red'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "All Transactions", 
            "Discrepancies", 
            "Unmatched Transactions", 
            "AI Flags"
        ])
        
        with tab1:
            st.subheader("All Ledger Transactions")
            st.dataframe(ledger_result)
            
            st.subheader("All Bank Transactions")
            st.dataframe(bank_result)
        
        with tab2:
            discrepancies = ledger_result[ledger_result['Bank_Status'] == 'Discrepancy Detected']
            st.subheader("Transactions with Discrepancies")
            if len(discrepancies) > 0:
                st.dataframe(discrepancies)
                
                # Allow adding comments
                for idx, row in discrepancies.iterrows():
                    with st.expander(f"Discrepancy: {row['Description']} - {row['Reference']}"):
                        st.write(f"**Discrepancy Type:** {row['Bank_Discrepancy_Type']}")
                        st.write(f"**Discrepancy Amount:** ${row['Bank_Discrepancy_Amount']:.2f}")
                        
                        comment = st.text_input(
                            "Add comment or action:",
                            key=f"bank_comment_{idx}",
                            value=""
                        )
                        if st.button("Save Comment", key=f"bank_save_{idx}"):
                            st.success(f"Comment saved for {row['Reference']}")
            else:
                st.success("No discrepancies found!")
        
        with tab3:
            unmatched = ledger_result[ledger_result['Bank_Status'] == 'Not Matched']
            st.subheader("Unmatched Ledger Transactions")
            if len(unmatched) > 0:
                st.dataframe(unmatched)
                
                # Option to manually match
                st.subheader("Manual Matching")
                for idx, row in unmatched.iterrows():
                    with st.expander(f"Unmatched: {row['Description']} - {row['Reference']}"):
                        potential_matches = bank_result[bank_result['Status'] == 'Not Matched']
                        if len(potential_matches) > 0:
                            match_options = [f"{m['Date']} - {m['Description']} - {max(m['Deposit'], m['Withdrawal'])}" 
                                           for _, m in potential_matches.iterrows()]
                            selected_match = st.selectbox(
                                "Select potential bank transaction match:",
                                options=[""] + match_options,
                                key=f"bank_match_{idx}"
                            )
                            if selected_match and st.button("Confirm Match", key=f"bank_confirm_{idx}"):
                                st.success(f"Manually matched {row['Reference']}")
                        else:
                            st.info("No potential matches found in bank statements")
            else:
                st.success("All transactions matched!")
        
        with tab4:
            flagged = ledger_result[ledger_result['AI_Flag'] != '']
            st.subheader("AI Flagged Transactions")
            if len(flagged) > 0:
                st.dataframe(flagged)
                
                for idx, row in flagged.iterrows():
                    with st.expander(f"Flag: {row['AI_Flag']} - {row['Description']}"):
                        st.write(f"**Transaction Details:**")
                        st.write(f"Date: {row['Date']}")
                        st.write(f"Amount: {max(row['Debit'], row['Credit'])}")
                        st.write(f"Reference: {row['Reference']}")
                        
                        action = st.selectbox(
                            "Select action:",
                            ["No action needed", "Mark for review", "Request correction"],
                            key=f"bank_action_{idx}"
                        )
                        if st.button("Save Action", key=f"bank_save_action_{idx}"):
                            st.success(f"Action saved for {row['Reference']}")
            else:
                st.success("No AI flags generated!")

elif page == "Invoice Validation":
    st.header("Invoice Validation")
    
    if 'processed' not in st.session_state:
        st.warning("Please process data first on the Upload Data page.")
    else:
        ledger_result = st.session_state.ledger_invoice_result
        invoice_result = st.session_state.invoice_result
        
        # Summary visualization
        st.subheader("Invoice Validation Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        matched_count = len(ledger_result[ledger_result['Invoice_Status'] == 'Matched'])
        discrepancy_count = len(ledger_result[ledger_result['Invoice_Status'] == 'Discrepancy Detected'])
        pending_count = len(ledger_result[ledger_result['Invoice_Status'] == 'Pending Match'])
        total_count = len(ledger_result)
        
        with col1:
            st.metric("Matched Invoices", f"{matched_count}/{total_count}", 
                     f"{matched_count/total_count*100:.1f}%")
        with col2:
            st.metric("Discrepancies", f"{discrepancy_count}/{total_count}", 
                     f"{discrepancy_count/total_count*100:.1f}%", delta_color="inverse")
        with col3:
            st.metric("Pending Match", f"{pending_count}/{total_count}", 
                     f"{pending_count/total_count*100:.1f}%", delta_color="off")
        with col4:
            unmatched_invoices = len(invoice_result[invoice_result['Ledger_Status'] == 'Pending Match'])
            st.metric("Unmatched Invoices", f"{unmatched_invoices}/{len(invoice_result)}", 
                     f"{unmatched_invoices/len(invoice_result)*100:.1f}%", delta_color="off")
        
        # Create pie chart
        fig = px.pie(
            values=[matched_count, discrepancy_count, pending_count],
            names=['Matched', 'Discrepancies', 'Pending'],
            title='Invoice Validation Status',
            color=['Matched', 'Discrepancies', 'Pending'],
            color_discrete_map={'Matched':'green', 'Discrepancies':'orange', 'Pending':'gray'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "All Invoices", 
            "Discrepancies", 
            "Pending Match", 
            "Unmatched Invoices"
        ])
        
        with tab1:
            st.subheader("All Ledger Transactions with Invoice Status")
            st.dataframe(ledger_result)
            
            st.subheader("All Invoices")
            st.dataframe(invoice_result)
        
        with tab2:
            discrepancies = ledger_result[ledger_result['Invoice_Status'] == 'Discrepancy Detected']
            st.subheader("Invoices with Discrepancies")
            if len(discrepancies) > 0:
                st.dataframe(discrepancies)
                
                # Allow adding comments and viewing invoices
                for idx, row in discrepancies.iterrows():
                    with st.expander(f"Discrepancy: {row['Description']} - {row['Reference']}"):
                        st.write(f"**Discrepancy Type:** {row['Invoice_Discrepancy_Type']}")
                        st.write(f"**Discrepancy Amount:** ${row['Invoice_Discrepancy_Amount']:.2f}")
                        
                        # Show invoice if available
                        if 'invoice_files' in st.session_state and row['Matched_Invoice_ID'] in st.session_state.invoice_files:
                            with open(st.session_state.invoice_files[row['Matched_Invoice_ID']], "rb") as pdf_file:
                                PDFbyte = pdf_file.read()
                            st.download_button(
                                label="Download Invoice PDF",
                                data=PDFbyte,
                                file_name=f"{row['Matched_Invoice_ID']}.pdf",
                                mime="application/octet-stream",
                                key=f"dl_{idx}"
                            )
                        
                        comment = st.text_area(
                            "Add notes or comments:",
                            key=f"invoice_comment_{idx}",
                            value=row.get('Invoice_Notes', '')
                        )
                        if st.button("Save Notes", key=f"invoice_save_{idx}"):
                            st.session_state.ledger_invoice_result.at[idx, 'Invoice_Notes'] = comment
                            st.success(f"Notes saved for {row['Reference']}")
            else:
                st.success("No discrepancies found!")
        
        with tab3:
            pending = ledger_result[ledger_result['Invoice_Status'] == 'Pending Match']
            st.subheader("Pending Invoice Matches")
            if len(pending) > 0:
                st.dataframe(pending)
                
                # Manual matching interface
                st.subheader("Manual Invoice Matching")
                for idx, row in pending.iterrows():
                    with st.expander(f"Pending: {row['Description']} - {row['Reference']}"):
                        # Find potential invoice matches
                        potential_matches = invoice_result[invoice_result['Ledger_Status'] == 'Pending Match']
                        if len(potential_matches) > 0:
                            match_options = [f"{m['Invoice_ID']} - {m['Vendor']} - ${m['Amount']:.2f} - {m['Date']}" 
                                           for _, m in potential_matches.iterrows()]
                            selected_match = st.selectbox(
                                "Select potential invoice match:",
                                options=[""] + match_options,
                                key=f"invoice_match_{idx}"
                            )
                            if selected_match and st.button("Confirm Match", key=f"invoice_confirm_{idx}"):
                                # Extract invoice ID from selection
                                invoice_id = selected_match.split(' - ')[0]
                                st.session_state.ledger_invoice_result.at[idx, 'Invoice_Status'] = 'Matched'
                                st.session_state.ledger_invoice_result.at[idx, 'Matched_Invoice_ID'] = invoice_id
                                st.success(f"Manually matched {row['Reference']} with invoice {invoice_id}")
                        else:
                            st.info("No potential invoice matches found")
            else:
                st.success("No pending matches!")
        
        with tab4:
            unmatched_invoices = invoice_result[invoice_result['Ledger_Status'] == 'Pending Match']
            st.subheader("Unmatched Invoices")
            if len(unmatched_invoices) > 0:
                st.dataframe(unmatched_invoices)
                
                # Option to manually match invoices to ledger entries
                st.subheader("Manual Invoice to Ledger Matching")
                for idx, row in unmatched_invoices.iterrows():
                    with st.expander(f"Unmatched Invoice: {row['Invoice_ID']} - {row['Vendor']}"):
                        # Show invoice if available
                        if 'invoice_files' in st.session_state and row['Invoice_ID'] in st.session_state.invoice_files:
                            with open(st.session_state.invoice_files[row['Invoice_ID']], "rb") as pdf_file:
                                PDFbyte = pdf_file.read()
                            st.download_button(
                                label="Download Invoice PDF",
                                data=PDFbyte,
                                file_name=f"{row['Invoice_ID']}.pdf",
                                mime="application/octet-stream",
                                key=f"dl_inv_{idx}"
                            )
                        
                        # Find potential ledger matches
                        potential_matches = ledger_result[ledger_result['Invoice_Status'] == 'Pending Match']
                        if len(potential_matches) > 0:
                            match_options = [f"{m['Reference']} - {m['Vendor']} - ${max(m['Debit'], m['Credit']):.2f} - {m['Date']}" 
                                           for _, m in potential_matches.iterrows()]
                            selected_match = st.selectbox(
                                "Select potential ledger entry match:",
                                options=[""] + match_options,
                                key=f"ledger_match_{idx}"
                            )
                            if selected_match and st.button("Confirm Match", key=f"ledger_confirm_{idx}"):
                                # Extract reference from selection
                                ref = selected_match.split(' - ')[0]
                                st.success(f"Manually matched invoice {row['Invoice_ID']} with ledger entry {ref}")
                        else:
                            st.info("No potential ledger matches found")
            else:
                st.success("All invoices matched!")

elif page == "Entry Explorer":
    st.header("Entry Explorer")
    
    if 'processed' not in st.session_state:
        st.warning("Please process data first on the Upload Data page.")
    else:
        ledger_result = st.session_state.ledger_result.copy()
        bank_result = st.session_state.bank_result.copy()
        ledger_invoice_result = st.session_state.get('ledger_invoice_result', None)
        invoice_result = st.session_state.get('invoice_result', None)
        invoice_files = st.session_state.get('invoice_files', {})
        
        # Ensure helpful derived columns
        if 'Amount' not in ledger_result.columns:
            ledger_result['Amount'] = ledger_result[['Debit', 'Credit']].max(axis=1)
        ledger_result = ensure_ledger_vendor_column(ledger_result)
        
        # Selection of ledger entry
        options = []
        for idx, row in ledger_result.iterrows():
            label = f"{idx} | {row.get('Date')} | {row.get('Reference')} | {row.get('Vendor')} | ${max(row.get('Debit',0), row.get('Credit',0)):.2f}"
            options.append((idx, label))
        
        selected = st.selectbox(
            "Select a ledger entry",
            options=options,
            format_func=lambda x: x[1] if isinstance(x, tuple) else str(x)
        )
        
        if selected:
            sel_idx = selected[0]
            ledger_row = ledger_result.loc[sel_idx]
            
            # Find matched bank row if available
            bank_row = None
            if 'Matched_Bank_Index' in ledger_result.columns:
                bidx = int(ledger_row.get('Matched_Bank_Index', -1)) if pd.notnull(ledger_row.get('Matched_Bank_Index', -1)) else -1
                if bidx in bank_result.index:
                    bank_row = bank_result.loc[bidx]
            
            # Find matched invoice row and file if available
            invoice_row = None
            invoice_id = None
            if ledger_invoice_result is not None and 'Matched_Invoice_ID' in ledger_invoice_result.columns and sel_idx in ledger_invoice_result.index:
                invoice_id = ledger_invoice_result.loc[sel_idx].get('Matched_Invoice_ID')
                if invoice_result is not None and invoice_id:
                    cand = invoice_result[invoice_result['Invoice_ID'] == invoice_id]
                    if len(cand) > 0:
                        invoice_row = cand.iloc[0]
            elif invoice_result is not None and 'Matched_Ledger_Index' in invoice_result.columns:
                cand = invoice_result[invoice_result['Matched_Ledger_Index'] == sel_idx]
                if len(cand) > 0:
                    invoice_row = cand.iloc[0]
                    invoice_id = invoice_row.get('Invoice_ID')
            
            # Summary
            st.subheader("Summary")
            summary_text = generate_entry_summary(ledger_row, bank_row, invoice_row)
            st.write(summary_text)
            
            # Details columns
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Ledger Entry**")
                st.json({k: (v.item() if hasattr(v, 'item') else v) for k, v in ledger_row.to_dict().items()})
            with c2:
                st.markdown("**Bank Entry**")
                if bank_row is not None:
                    st.json({k: (v.item() if hasattr(v, 'item') else v) for k, v in bank_row.to_dict().items()})
                else:
                    st.info("No linked bank entry.")
            with c3:
                st.markdown("**Invoice**")
                if invoice_row is not None:
                    st.json({k: (v.item() if hasattr(v, 'item') else v) for k, v in invoice_row.to_dict().items()})
                else:
                    st.info("No linked invoice.")
            
            # Invoice preview
            if invoice_id and invoice_id in invoice_files:
                st.subheader("Invoice Preview")
                display_pdf_preview(invoice_files[invoice_id])
            elif invoice_row is not None:
                # Try to guess by ID even if not in mapping
                guessed_id = invoice_row.get('Invoice_ID')
                if guessed_id in invoice_files:
                    st.subheader("Invoice Preview")
                    display_pdf_preview(invoice_files[guessed_id])
                else:
                    st.info("Invoice file not available for preview.")
            else:
                st.info("No invoice to preview.")

elif page == "Analysis & Reports":
    st.header("Analysis & Reports")
    
    if 'processed' not in st.session_state:
        st.warning("Please process data first on the Upload Data page.")
    else:
        ledger_result = st.session_state.ledger_result
        invoice_result = st.session_state.invoice_result
        
        # Time analysis
        st.subheader("Transaction Timeline")
        ledger_result['Date'] = pd.to_datetime(ledger_result['Date'])
        daily_counts = ledger_result.groupby('Date').size().reset_index(name='Count')
        
        fig = px.line(daily_counts, x='Date', y='Count', title='Transactions per Day')
        st.plotly_chart(fig, use_container_width=True)
        
        # Amount analysis
        st.subheader("Transaction Amount Distribution")
        if 'Amount' not in ledger_result.columns:
            ledger_result['Amount'] = ledger_result[['Debit', 'Credit']].max(axis=1)
        fig = px.histogram(ledger_result, x='Amount', title='Distribution of Transaction Amounts')
        st.plotly_chart(fig, use_container_width=True)
        
        # Vendor analysis
        st.subheader("Vendor Analysis")
        ledger_result = ensure_ledger_vendor_column(ledger_result)
        vendor_totals = ledger_result.groupby('Vendor')['Amount'].sum().reset_index()
        vendor_totals = vendor_totals.sort_values('Amount', ascending=False)
        fig = px.bar(vendor_totals.head(10), x='Vendor', y='Amount', title='Top 10 Vendors by Amount')
        st.plotly_chart(fig, use_container_width=True)
        
        # Reconciliation status by vendor
        st.subheader("Reconciliation Status by Vendor")
        vendor_status = ledger_result.groupby(['Vendor', 'Bank_Status']).size().reset_index(name='Count')
        fig = px.sunburst(vendor_status, path=['Vendor', 'Bank_Status'], values='Count',
                         title='Bank Reconciliation Status by Vendor')
        st.plotly_chart(fig, use_container_width=True)
        
        # Invoice validation status
        st.subheader("Invoice Validation Status")
        if 'ledger_invoice_result' in st.session_state:
            invoice_status = st.session_state.ledger_invoice_result.groupby('Invoice_Status').size().reset_index(name='Count')
            fig = px.pie(invoice_status, values='Count', names='Invoice_Status', 
                        title='Invoice Validation Status Distribution')
            st.plotly_chart(fig, use_container_width=True)
        
        # Generate report
        st.subheader("Generate Reconciliation Report")
        report_type = st.selectbox("Select Report Type", 
                                  ["Summary Report", "Detailed Reconciliation", "Discrepancy Analysis"])
        
        if st.button("Generate Report"):
            with st.spinner("Generating report..."):
                # Compute summary metrics locally to avoid undefined variables
                matched_count = len(ledger_result[ledger_result['Bank_Status'] == 'Matched'])
                discrepancy_count = len(ledger_result[ledger_result['Bank_Status'] == 'Discrepancy Detected'])
                unmatched_count = len(ledger_result[ledger_result['Bank_Status'] == 'Not Matched'])

                matched_count_inv = len(invoice_result[invoice_result['Ledger_Status'] == 'Matched'])
                discrepancy_count_inv = len(invoice_result[invoice_result['Ledger_Status'] == 'Discrepancy Detected'])
                pending_count = len(invoice_result[invoice_result['Ledger_Status'] == 'Pending Match'])
                
                # Create a simple text report
                report_content = f"""
                RECONCILIATION REPORT
                Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                ===================================================
                
                Bank Reconciliation Summary:
                - Total Transactions: {len(ledger_result)}
                - Matched: {matched_count} ({(matched_count/len(ledger_result))*100:.1f}%)
                - Discrepancies: {discrepancy_count} ({(discrepancy_count/len(ledger_result))*100:.1f}%)
                - Unmatched: {unmatched_count} ({(unmatched_count/len(ledger_result))*100:.1f}%)
                
                Invoice Validation Summary:
                - Total Invoices: {len(invoice_result)}
                - Matched: {matched_count_inv} ({(matched_count_inv/len(invoice_result))*100:.1f}%)
                - Discrepancies: {discrepancy_count_inv} ({(discrepancy_count_inv/len(invoice_result))*100:.1f}%)
                - Pending: {pending_count} ({(pending_count/len(invoice_result))*100:.1f}%)
                
                Top Vendors by Amount:
                """
                
                for _, row in vendor_totals.head(5).iterrows():
                    report_content += f"- {row['Vendor']}: ${row['Amount']:.2f}\n"
                
                st.text_area("Report Content", report_content, height=300)
                
                # Download report
                st.download_button(
                    label="Download Report as Text",
                    data=report_content,
                    file_name="reconciliation_report.txt",
                    mime="text/plain"
                )
        
        # Export results
        st.subheader("Export Results")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ledger_csv = ledger_result.to_csv(index=False)
            st.download_button(
                label="Download Ledger Results",
                data=ledger_csv,
                file_name="ledger_reconciliation_results.csv",
                mime="text/csv"
            )
        
        with col2:
            bank_csv = st.session_state.bank_result.to_csv(index=False)
            st.download_button(
                label="Download Bank Results",
                data=bank_csv,
                file_name="bank_reconciliation_results.csv",
                mime="text/csv"
            )
        
        with col3:
            if 'ledger_invoice_result' in st.session_state:
                invoice_csv = st.session_state.ledger_invoice_result.to_csv(index=False)
                st.download_button(
                    label="Download Invoice Results",
                    data=invoice_csv,
                    file_name="invoice_validation_results.csv",
                    mime="text/csv"
                )

# Footer
st.sidebar.markdown("---")

# Add some custom CSS for better styling
st.markdown("""
<style>
    .stButton button {
        width: 100%;
    }
    .stDownloadButton button {
        width: 100%;
    }
    .css-1v0mbdj {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)                                                                   