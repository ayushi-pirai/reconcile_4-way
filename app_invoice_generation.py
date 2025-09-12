import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fpdf import FPDF
import base64
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
import io
import random

# Set page configuration
st.set_page_config(
    page_title="Invoice Generator for Reconciliation",
    page_icon="🧾",
    layout="wide"
)

st.title("🧾 Invoice Generator for Bank Reconciliation")
st.markdown("""
This tool generates sample invoices in PDF format that correspond to bank statement entries.
You can upload a bank statement CSV and generate invoices with different matching scenarios.
""")

# Sample bank statement data
sample_bank_data = {
    'Date': ['2023-10-01', '2023-10-02', '2023-10-03', '2023-10-04', '2023-10-05', 
             '2023-10-06', '2023-10-07', '2023-10-08', '2023-10-09', '2023-10-10'],
    'Description': ['OFFICE SUPPLIES INC', 'ABC CORP PAYMENT', 'ELECTRIC COMPANY', 
                   'SOFTWARE SUBSCRIPTION', 'XYZ LTD', 'RENT PAYMENT', 'TECH STORE',
                   'CONSULTING SERVICES', 'MARKETING SOLUTIONS', 'TRAVEL EXPENSES'],
    'Reference': ['CHK1001', 'DEP1002', 'CHK1003', 'CHK1004', 'DEP1005', 
                 'CHK1006', 'CHK1007', 'CHK1008', 'CHK1009', 'CHK1010'],
    'Withdrawal': [250.00, 0, 350.50, 199.99, 0, 2000.00, 1200.00, 1500.00, 850.25, 450.75],
    'Deposit': [0, 5000.00, 0, 0, 7500.00, 0, 0, 0, 0, 0],
    'Balance': [5000.00, 10000.00, 9649.50, 9449.51, 16949.51, 14949.51, 13749.51, 12249.51, 11399.26, 10948.51]
}

# Vendor information for invoice generation
vendors = {
    'OFFICE SUPPLIES INC': {
        'name': 'Office Supplies Inc.',
        'address': '123 Business Ave, Suite 456\nNew York, NY 10001',
        'phone': '(555) 123-4567',
        'email': 'billing@officesupplies.com',
        'website': 'www.officesupplies.com'
    },
    'ABC CORP': {
        'name': 'ABC Corporation',
        'address': '456 Corporate Blvd\nChicago, IL 60601',
        'phone': '(555) 987-6543',
        'email': 'accounts@abccorp.com',
        'website': 'www.abccorp.com'
    },
    'ELECTRIC COMPANY': {
        'name': 'Electric Company Utilities',
        'address': '789 Power Lane\nHouston, TX 77001',
        'phone': '(555) 555-1234',
        'email': 'billing@electriccompany.com',
        'website': 'www.electriccompany.com'
    },
    'SOFTWARE SUBSCRIPTION': {
        'name': 'Software Solutions Inc.',
        'address': '321 Tech Park\nSan Francisco, CA 94101',
        'phone': '(555) 456-7890',
        'email': 'invoices@softwaresolutions.com',
        'website': 'www.softwaresolutions.com'
    },
    'XYZ LTD': {
        'name': 'XYZ Limited',
        'address': '654 Enterprise St\nBoston, MA 02101',
        'phone': '(555) 234-5678',
        'email': 'finance@xyzltd.com',
        'website': 'www.xyzltd.com'
    }
}

# Function to create a PDF invoice
# Now supports multiple formats/styles

def create_invoice(invoice_number, vendor, client, date, due_date, items, total, 
                   notes="", terms="Net 30", status="Paid", match_status="Matched", format_style="Classic"):
    pdf = FPDF()
    pdf.add_page()

    # --- Format Style Definitions ---
    styles = {
        "Classic": {
            "header_bg": (200, 200, 200),
            "header_text": (0, 0, 0),
            "footer_bg": (240, 240, 240),
            "footer_text": (80, 80, 80),
            "font": ("Arial", "", 12),
            "logo": "logo1.jpg",
            "watermark": None,
            "layout": "stacked"
        },
        "Modern": {
            "header_bg": (0, 102, 204),
            "header_text": (255, 255, 255),
            "footer_bg": (0, 102, 204),
            "footer_text": (255, 255, 255),
            "font": ("Helvetica", "B", 13),
            "logo": "logo2.jpg",
            "watermark": "watermark_paid.jpg",
            "layout": "side_by_side"
        },
        "Minimal": {
            "header_bg": (255, 255, 255),
            "header_text": (0, 0, 0),
            "footer_bg": (255, 255, 255),
            "footer_text": (120, 120, 120),
            "font": ("Times", "", 12),
            "logo": None,
            "watermark": None,
            "layout": "minimal"
        },
        "Bold": {
            "header_bg": (255, 87, 34),
            "header_text": (255, 255, 255),
            "footer_bg": (255, 235, 205),
            "footer_text": (0, 0, 0),
            "font": ("Arial", "B", 14),
            "logo": "logo3.jpg",
            "watermark": "watermark_due.jpg",
            "layout": "bold"
        },
        "Elegant": {
            "header_bg": (44, 62, 80),
            "header_text": (236, 240, 241),
            "footer_bg": (44, 62, 80),
            "footer_text": (236, 240, 241),
            "font": ("Times", "I", 13),
            "logo": "logo4.jpg",
            "watermark": "watermark_logo_faint.jpg",
            "layout": "elegant"
        },
        "Tech": {
            "header_bg": (33, 150, 243),
            "header_text": (255, 255, 255),
            "footer_bg": (33, 150, 243),
            "footer_text": (255, 255, 255),
            "font": ("Courier", "B", 12),
            "logo": "logo5.jpg",
            "watermark": None,
            "layout": "tech"
        },
        "InvoicePro": {
            "header_bg": (76, 175, 80),
            "header_text": (255, 255, 255),
            "footer_bg": (232, 245, 233),
            "footer_text": (76, 175, 80),
            "font": ("Arial", "B", 13),
            "logo": "logo6.jpg",
            "watermark": "watermark_stamp.jpg",
            "layout": "pro"
        },
        "Corporate": {
            "header_bg": (158, 158, 158),
            "header_text": (33, 33, 33),
            "footer_bg": (224, 224, 224),
            "footer_text": (33, 33, 33),
            "font": ("Helvetica", "", 12),
            "logo": "logo7.jpg",
            "watermark": None,
            "layout": "corporate"
        },
        "Creative": {
            "header_bg": (255, 193, 7),
            "header_text": (0, 0, 0),
            "footer_bg": (255, 249, 196),
            "footer_text": (0, 0, 0),
            "font": ("Arial", "I", 12),
            "logo": "logo8.jpg",
            "watermark": "watermark_creative.jpg",
            "layout": "creative"
        },
        "BlueStripe": {
            "header_bg": (33, 150, 243),
            "header_text": (255, 255, 255),
            "footer_bg": (33, 150, 243),
            "footer_text": (255, 255, 255),
            "font": ("Arial", "B", 12),
            "logo": "logo9.jpg",
            "watermark": "watermark_stripe.jpg",
            "layout": "stripe"
        }
    }
    style = styles.get(format_style, styles["Classic"])

    # --- Header ---
    pdf.set_fill_color(*style["header_bg"])
    pdf.set_text_color(*style["header_text"])
    pdf.set_font(*style["font"])
    pdf.cell(0, 15, f"INVOICE", 0, 1, 'C', True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # --- Watermark (if any) ---
    if style["watermark"]:
        # Place a watermark image at the center (user to provide JPG)
        try:
            pdf.image(f"images/{style['watermark']}", x=40, y=80, w=120, h=60)
        except:
            pass  # If image not found, skip

    # --- Logo (if enabled) ---
    if style["logo"]:
        # Place logo in different positions depending on layout
        try:
            if style["layout"] in ["stacked", "minimal"]:
                pdf.image(f"images/{style['logo']}", x=10, y=10, w=30)
            elif style["layout"] == "side_by_side":
                pdf.image(f"images/{style['logo']}", x=170, y=10, w=30)
            elif style["layout"] == "bold":
                pdf.image(f"images/{style['logo']}", x=85, y=10, w=40)
            elif style["layout"] == "elegant":
                pdf.image(f"images/{style['logo']}", x=10, y=20, w=25)
            elif style["layout"] == "tech":
                pdf.image(f"images/{style['logo']}", x=10, y=10, w=25)
            elif style["layout"] == "pro":
                pdf.image(f"images/{style['logo']}", x=170, y=10, w=30)
            elif style["layout"] == "corporate":
                pdf.image(f"images/{style['logo']}", x=170, y=10, w=30)
            elif style["layout"] == "creative":
                pdf.image(f"images/{style['logo']}", x=100, y=10, w=40)
            elif style["layout"] == "stripe":
                pdf.image(f"images/{style['logo']}", x=10, y=10, w=30)
        except:
            pass  # If image not found, skip

    # --- Layouts ---
    if style["layout"] == "stacked":
        # Vendor and client stacked
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "From:", 0, 1)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 6, f"{vendor['name']}\n{vendor['address']}\nPhone: {vendor['phone']}\nEmail: {vendor['email']}")
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "To:", 0, 1)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 6, f"{client['name']}\n{client['address']}\nPhone: {client['phone']}\nEmail: {client['email']}")
        pdf.ln(4)
    elif style["layout"] == "side_by_side":
        # Vendor left, client right, modern table
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(90, 8, "From:", 0, 0)
        pdf.cell(0, 8, "To:", 0, 1)
        pdf.set_font("Helvetica", '', 11)
        y = pdf.get_y()
        x = pdf.get_x()
        pdf.multi_cell(90, 6, f"{vendor['name']}\n{vendor['address']}\nPhone: {vendor['phone']}\nEmail: {vendor['email']}", 0, 'L')
        pdf.set_xy(x+90, y)
        pdf.multi_cell(0, 6, f"{client['name']}\n{client['address']}\nPhone: {client['phone']}\nEmail: {client['email']}", 0, 'L')
        pdf.ln(4)
    elif style["layout"] == "minimal":
        # Minimal: no logo, no header color, info in a table
        pdf.set_font("Times", '', 11)
        pdf.cell(40, 8, "From:", 0, 0)
        pdf.cell(0, 8, vendor['name'], 0, 1)
        pdf.cell(40, 8, "Address:", 0, 0)
        pdf.cell(0, 8, vendor['address'].split('\n')[0], 0, 1)
        pdf.cell(40, 8, "To:", 0, 0)
        pdf.cell(0, 8, client['name'], 0, 1)
        pdf.cell(40, 8, "Client Addr:", 0, 0)
        pdf.cell(0, 8, client['address'].split(',')[0], 0, 1)
        pdf.ln(2)
    elif style["layout"] == "bold":
        # Bold: Large colored header, logo center, all info centered, thick table borders
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(0, 10, "BILL TO:", 0, 1, 'C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 8, client['name'], 0, 1, 'C')
        pdf.cell(0, 8, client['address'], 0, 1, 'C')
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(0, 10, "FROM:", 0, 1, 'C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 8, vendor['name'], 0, 1, 'C')
        pdf.cell(0, 8, vendor['address'], 0, 1, 'C')
        pdf.ln(2)
    elif style["layout"] == "elegant":
        # Elegant: Italic font, lines between sections, watermark
        pdf.set_font("Times", 'I', 12)
        pdf.cell(0, 8, "From:", 0, 1)
        pdf.cell(0, 8, vendor['name'], 0, 1)
        pdf.cell(0, 8, vendor['address'], 0, 1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.cell(0, 8, "To:", 0, 1)
        pdf.cell(0, 8, client['name'], 0, 1)
        pdf.cell(0, 8, client['address'], 0, 1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)
    elif style["layout"] == "tech":
        # Tech: Monospace font, info in bordered boxes, QR code placeholder
        pdf.set_font("Courier", 'B', 12)
        pdf.cell(0, 8, "From:", 1, 1)
        pdf.set_font("Courier", '', 11)
        pdf.cell(0, 8, vendor['name'], 1, 1)
        pdf.cell(0, 8, vendor['address'], 1, 1)
        pdf.cell(0, 8, "To:", 1, 1)
        pdf.cell(0, 8, client['name'], 1, 1)
        pdf.cell(0, 8, client['address'], 1, 1)
        pdf.ln(2)
        # pdf.image('images/qr_placeholder.png', x=170, y=pdf.get_y(), w=25)  # Add a QR code PNG if desired
    elif style["layout"] == "pro":
        # InvoicePro: Green header, vendor/client in two columns, bold table, signature line
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(90, 8, "From:", 0, 0)
        pdf.cell(0, 8, "To:", 0, 1)
        pdf.set_font("Arial", '', 11)
        y = pdf.get_y()
        x = pdf.get_x()
        pdf.multi_cell(90, 6, f"{vendor['name']}\n{vendor['address']}", 0, 'L')
        pdf.set_xy(x+90, y)
        pdf.multi_cell(0, 6, f"{client['name']}\n{client['address']}", 0, 'L')
        pdf.ln(2)
        pdf.cell(0, 8, "Authorized by: ________________________", 0, 1, 'R')
    elif style["layout"] == "corporate":
        # Corporate: Gray header, logo right, info left, table with grid
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 8, "From:", 0, 1)
        pdf.set_font("Helvetica", '', 11)
        pdf.cell(0, 8, vendor['name'], 0, 1)
        pdf.cell(0, 8, vendor['address'], 0, 1)
        pdf.cell(0, 8, "To:", 0, 1)
        pdf.cell(0, 8, client['name'], 0, 1)
        pdf.cell(0, 8, client['address'], 0, 1)
        pdf.ln(2)
    elif style["layout"] == "creative":
        # Creative: Yellow header, playful font, info in colored boxes, watermark
        pdf.set_fill_color(255, 249, 196)
        pdf.set_font("Arial", 'I', 12)
        pdf.cell(0, 8, "From:", 1, 1, 'L', True)
        pdf.cell(0, 8, vendor['name'], 1, 1, 'L', True)
        pdf.cell(0, 8, vendor['address'], 1, 1, 'L', True)
        pdf.cell(0, 8, "To:", 1, 1, 'L', True)
        pdf.cell(0, 8, client['name'], 1, 1, 'L', True)
        pdf.cell(0, 8, client['address'], 1, 1, 'L', True)
        pdf.ln(2)
    elif style["layout"] == "stripe":
        # BlueStripe: Blue header/footer, info in horizontal stripes
        pdf.set_fill_color(33, 150, 243)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "From:", 0, 1, 'L', True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 8, vendor['name'], 0, 1, 'L', True)
        pdf.cell(0, 8, vendor['address'], 0, 1, 'L', True)
        pdf.cell(0, 8, "To:", 0, 1, 'L', True)
        pdf.cell(0, 8, client['name'], 0, 1, 'L', True)
        pdf.cell(0, 8, client['address'], 0, 1, 'L', True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
    else:
        # Default to stacked
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "From:", 0, 1)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 6, f"{vendor['name']}\n{vendor['address']}\nPhone: {vendor['phone']}\nEmail: {vendor['email']}")
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, "To:", 0, 1)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 6, f"{client['name']}\n{client['address']}\nPhone: {client['phone']}\nEmail: {client['email']}")
        pdf.ln(4)

    # --- Invoice Info Table ---
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Invoice #: {invoice_number}    Date: {date}    Due: {due_date}    Status: {status}    Reconciliation: {match_status}", 0, 1)
    pdf.ln(2)

    # --- Items Table ---
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(80, 8, "Description", 1, 0, 'C')
    pdf.cell(25, 8, "Qty", 1, 0, 'C')
    pdf.cell(30, 8, "Unit Price", 1, 0, 'C')
    pdf.cell(30, 8, "Amount", 1, 1, 'C')
    pdf.set_font("Arial", '', 11)
    for item in items:
        pdf.cell(80, 8, item['description'], 1)
        pdf.cell(25, 8, str(item['quantity']), 1, 0, 'C')
        pdf.cell(30, 8, f"${item['unit_price']:.2f}", 1, 0, 'R')
        pdf.cell(30, 8, f"${item['amount']:.2f}", 1, 1, 'R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(135, 8, "Total", 1, 0, 'R')
    pdf.cell(30, 8, f"${total:.2f}", 1, 1, 'R')
    pdf.ln(2)

    # --- Notes/Terms ---
    if notes:
        pdf.set_font("Arial", 'I', 10)
        pdf.multi_cell(0, 6, f"Notes: {notes}")
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, f"Terms: {terms}")

    # --- Footer ---
    pdf.set_y(-25)
    pdf.set_fill_color(*style["footer_bg"])
    pdf.set_text_color(*style["footer_text"])
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 10, f"Generated by Invoice Generator - {format_style}", 0, 0, 'C', True)
    pdf.set_text_color(0, 0, 0)

    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, f"{invoice_number}.pdf")
    pdf.output(file_path)
    return file_path

# Function to generate sample client data
def generate_client():
    companies = ["Global Enterprises Inc.", "Tech Innovations Ltd.", "Future Solutions Corp.", 
                 "Digital Transformations LLC", "NextGen Technologies"]
    addresses = ["123 Main St, New York, NY 10001", "456 Oak Ave, San Francisco, CA 94101", 
                 "789 Pine Rd, Chicago, IL 60601", "321 Elm Blvd, Boston, MA 02101", 
                 "654 Maple Ln, Austin, TX 78701"]
    
    return {
        'name': random.choice(companies),
        'address': random.choice(addresses),
        'phone': f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
        'email': f"accounting@{random.choice(['global', 'tech', 'future', 'digital', 'nextgen'])}.com"
    }

# Function to generate invoice items
def generate_items(amount):
    items = []
    remaining = amount
    
    # Generate 1-3 items that sum to the total amount
    num_items = random.randint(1, 3)
    for i in range(num_items):
        if i == num_items - 1:
            item_amount = remaining
        else:
            item_amount = round(random.uniform(0.3, 0.7) * remaining, 2)
            remaining -= item_amount
        
        descriptions = [
            "Office supplies",
            "Software subscription",
            "Consulting services",
            "Marketing services",
            "Equipment purchase",
            "Monthly service fee",
            "Professional development",
            "Travel expenses",
            "Utility services",
            "Maintenance services"
        ]
        
        unit_price = round(item_amount / random.randint(1, 5), 2)
        quantity = round(item_amount / unit_price)
        
        items.append({
            'description': random.choice(descriptions),
            'quantity': quantity,
            'unit_price': unit_price,
            'amount': item_amount
        })
    
    return items

# Function to create a download button for PDF files
def create_download_button(file_path, button_text):
    with open(file_path, "rb") as pdf_file:
        PDFbyte = pdf_file.read()
    
    st.download_button(
        label=button_text,
        data=PDFbyte,
        file_name=os.path.basename(file_path),
        mime="application/octet-stream"
    )

# Function to generate a general ledger with mixed match scenarios

def generate_general_ledger(bank_df, seed=None):
    ledger_rows = []
    rng = random.Random(seed if seed is not None else 0)

    def pick_vendor_from_description(description: str):
        for key, vendor in vendors.items():
            if key in description:
                return vendor['name']
        # Fallback vendor name
        return rng.choice([
            "Office Depot", "ABC Corp", "Electric Company", "Software Solutions Inc.",
            "XYZ Ltd", "Property Management Co", "Tech Store", "Marketing Solutions Inc"
        ])

    # Create ledger entries corresponding to bank transactions
    for i, row in bank_df.iterrows():
        withdrawal = float(row.get('Withdrawal', 0) or 0)
        deposit = float(row.get('Deposit', 0) or 0)
        if withdrawal <= 0 and deposit <= 0:
            continue

        base_date = datetime.strptime(row['Date'], '%Y-%m-%d')
        amount = withdrawal if withdrawal > 0 else deposit
        is_withdrawal = withdrawal > 0

        # Decide if this ledger entry should be a perfect match or a partial (discrepancy)
        # 65% matched, 25% discrepancy, remaining 10% we'll skip here and create separate not-matched entries below
        roll = rng.random()
        if roll < 0.65:
            target_status = "Matched"
            # Within 2 days difference
            date_offset = rng.randint(-2, 2)
            ledger_amount = round(amount, 2)
        elif roll < 0.90:
            target_status = "Discrepancy Detected"
            # Either date variance up to 7 days or small amount variance
            if rng.random() < 0.5:
                date_offset = rng.choice([3, 4, 5, 6, 7]) * (-1 if rng.random() > 0.5 else 1)
                ledger_amount = round(amount, 2)
            else:
                date_offset = rng.randint(-2, 2)
                # 5–15% variance
                ledger_amount = round(amount * rng.uniform(0.85, 1.15), 2)
                if abs(ledger_amount - amount) < 0.01:
                    ledger_amount = round(ledger_amount + 0.02, 2)
        else:
            # Skip creating a counterpart ledger entry for this bank row (bank will remain unmatched on its side)
            continue

        post_date = (base_date + timedelta(days=date_offset)).strftime('%Y-%m-%d')
        vendor_name = pick_vendor_from_description(row['Description'])

        description = (
            f"{'Payment' if is_withdrawal else 'Deposit'} - {row['Description']}"
        )
        reference = f"LED-{2000 + i}"

        debit = 0.0
        credit = 0.0
        if is_withdrawal:
            credit = ledger_amount
        else:
            debit = ledger_amount

        ledger_rows.append({
            'Date': post_date,
            'Description': description,
            'Reference': reference,
            'Vendor': vendor_name,
            'Debit': round(debit, 2),
            'Credit': round(credit, 2),
            'Account': 'Cash at Bank',
            'Bank_Status': target_status
        })

    # Add extra ledger entries that have no bank counterpart (Not Matched)
    extra_not_matched = max(3, len(ledger_rows) // 5)
    date_choices = [datetime.strptime(d, '%Y-%m-%d') for d in bank_df['Date'].tolist()]
    for j in range(extra_not_matched):
        base_date = rng.choice(date_choices)
        post_date = (base_date + timedelta(days=rng.randint(-10, 10))).strftime('%Y-%m-%d')
        amount = round(rng.uniform(75, 1200), 2)
        is_withdrawal = rng.random() > 0.5

        debit = 0.0
        credit = 0.0
        if is_withdrawal:
            credit = amount
        else:
            debit = amount

        vendor_name = rng.choice([
            "Training Co", "Insurance Co", "Web Services Inc", "Travel Agency",
            "Office Depot", "Consulting Partners", "Local Printing", "Catering Co"
        ])

        ledger_rows.append({
            'Date': post_date,
            'Description': f"{'Payment' if is_withdrawal else 'Deposit'} - {vendor_name}",
            'Reference': f"LED-NM-{3000 + j}",
            'Vendor': vendor_name,
            'Debit': debit,
            'Credit': credit,
            'Account': 'Cash at Bank',
            'Bank_Status': 'Not Matched'
        })

    ledger_df = pd.DataFrame(ledger_rows)
    # Sort by date for readability
    if not ledger_df.empty:
        ledger_df['Date'] = pd.to_datetime(ledger_df['Date'])
        ledger_df = ledger_df.sort_values('Date').reset_index(drop=True)
        ledger_df['Date'] = ledger_df['Date'].dt.strftime('%Y-%m-%d')
    return ledger_df

# Function to generate a synthetic bank statement deterministically

def generate_bank_statement(num_entries: int, seed: int = 0) -> pd.DataFrame:
    rng = random.Random(seed if seed is not None else 0)

    descriptions = [
        'OFFICE SUPPLIES INC', 'ABC CORP PAYMENT', 'ELECTRIC COMPANY',
        'SOFTWARE SUBSCRIPTION', 'XYZ LTD', 'RENT PAYMENT', 'TECH STORE',
        'CONSULTING SERVICES', 'MARKETING SOLUTIONS', 'TRAVEL EXPENSES',
        'INSURANCE CO', 'WEB SERVICES INC', 'TRAINING CO', 'PROPERTY MGMT CO'
    ]

    base_date = datetime(2023, 10, 1)
    start_balance = round(rng.uniform(8000, 20000), 2)

    rows = []
    balance = start_balance
    for i in range(num_entries):
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        desc = rng.choice(descriptions)
        is_deposit = rng.random() < 0.35  # ~35% deposits
        if is_deposit:
            deposit = round(rng.uniform(200, 9000), 2)
            withdrawal = 0.0
            reference = f"DEP{1000 + i}"
            balance = round(balance + deposit, 2)
        else:
            withdrawal = round(rng.uniform(50, 4000), 2)
            deposit = 0.0
            reference = f"CHK{1000 + i}"
            balance = round(balance - withdrawal, 2)

        rows.append({
            'Date': date,
            'Description': desc,
            'Reference': reference,
            'Withdrawal': withdrawal,
            'Deposit': deposit,
            'Balance': balance
        })

    return pd.DataFrame(rows)

# Main application
def main():
    st.sidebar.header("Configuration")
    
    # Deterministic seed (used across bank generation, ledger, and invoices)
    seed_value = st.sidebar.number_input("Random seed", min_value=0, value=42, step=1)
    random.seed(seed_value)
    try:
        np.random.seed(seed_value)
    except Exception:
        pass
    
    # Option to upload bank statement or use sample data
    source_choice = st.sidebar.radio(
        "Bank statement source",
        ["Sample", "Upload CSV", "Generate"],
        index=0
    )
    
    if source_choice == "Sample":
        bank_df = pd.DataFrame(sample_bank_data)
        st.sidebar.success("Using sample bank statement data")
    elif source_choice == "Upload CSV":
        uploaded_file = st.sidebar.file_uploader("Upload Bank Statement (CSV)", type=['csv'])
        if uploaded_file is not None:
            bank_df = pd.read_csv(uploaded_file)
            st.sidebar.success("Bank statement uploaded successfully!")
        else:
            st.sidebar.warning("Please upload a CSV file or switch to Sample/Generate")
            return
    else:
        gen_count = st.sidebar.number_input("Number of bank entries", min_value=5, max_value=200, value=20, step=1)
        bank_df = generate_bank_statement(int(gen_count), seed=seed_value)
        st.sidebar.success(f"Generated {int(gen_count)} bank entries")
    
    # Generate a general ledger similar to app_invoice.py sample
    ledger_df = generate_general_ledger(bank_df, seed=seed_value)
    # Tables will be displayed at the end
    
    # Configuration for invoice generation
    # st.sidebar.subheader("Invoice Generation Settings")
    # Use seeded RNG for invoice distribution so it's deterministic per seed but different from ledger
    invoice_rng = random.Random(seed_value + 101)
    # Randomize percentages deterministically from seed
    a = invoice_rng.uniform(0.3, 1.0)
    b = invoice_rng.uniform(0.1, 0.8)
    c = invoice_rng.uniform(0.05, 0.6)
    s = a + b + c
    match_distribution = int((a / s) * 100)
    mismatch_distribution = int((b / s) * 100)
    pending_distribution = 100 - match_distribution - mismatch_distribution
    # st.sidebar.info(f"Invoice distribution (seeded): Matched {match_distribution}%, Mismatch {mismatch_distribution}%, Pending {pending_distribution}%")

    # Create client data (used for all invoices)
    client = generate_client()
 
    # Create invoices based on bank statement
    invoices = []
    format_options = [
        "Classic", "Modern", "Minimal", "Bold", "Elegant", "Tech", "InvoicePro", "Corporate", "Creative", "BlueStripe"
    ]
    for i, row in bank_df.iterrows():
        
        # Determine transaction type and amount
        if row['Withdrawal'] > 0:
            amount = row['Withdrawal']
            transaction_type = "Payment"
        else:
            amount = row['Deposit']
            transaction_type = "Deposit"
        
        # Skip deposits for invoice generation (invoices are typically for payments)
        if transaction_type == "Deposit":
            continue
        
        # Determine match status based on distribution
        rand = invoice_rng.randint(1, 100)
        if rand <= match_distribution:
            match_status = "Matched"
            # Use the exact amount and date from bank statement
            invoice_amount = amount
            invoice_date = row['Date']
        elif rand <= match_distribution + mismatch_distribution:
            match_status = "Mismatch Detected"
            # Create a discrepancy in amount or date
            if invoice_rng.random() > 0.5:
                # Amount discrepancy
                invoice_amount = amount * invoice_rng.uniform(0.8, 1.2)
                invoice_date = row['Date']
            else:
                # Date discrepancy (1-7 days difference)
                invoice_amount = amount
                date_obj = datetime.strptime(row['Date'], '%Y-%m-%d')
                days_diff = invoice_rng.randint(1, 7) * (-1 if invoice_rng.random() > 0.5 else 1)
                invoice_date = (date_obj + timedelta(days=days_diff)).strftime('%Y-%m-%d')
        else:
            match_status = "Pending Match"
            # Use the exact amount and date
            invoice_amount = amount
            invoice_date = row['Date']
        
        # Determine due date (15-45 days from invoice date)
        date_obj = datetime.strptime(invoice_date, '%Y-%m-%d')
        due_date = (date_obj + timedelta(days=invoice_rng.randint(15, 45))).strftime('%Y-%m-%d')
        
        # Get vendor information based on bank description
        vendor_key = None
        for key in vendors.keys():
            if key in row['Description']:
                vendor_key = key
                break
        
        if vendor_key is None:
            # Use a random vendor if no match found
            vendor_key = invoice_rng.choice(list(vendors.keys()))
        
        vendor = vendors[vendor_key]
        
        # Generate invoice items
        # Use seeded randomness for items by seeding global RNG temporarily
        prev_state = random.getstate()
        random.seed(seed_value * 1000003 + i)
        items = generate_items(invoice_amount)
        random.setstate(prev_state)
        
        # Create invoice
        invoice_number = f"INV-{1000 + i}"
        # Randomly select a format for each invoice
        format_style = invoice_rng.choice(format_options)
        invoice_path = create_invoice(
            invoice_number=invoice_number,
            vendor=vendor,
            client=client,
            date=invoice_date,
            due_date=due_date,
            items=items,
            total=invoice_amount,
            notes=f"Payment for {row['Description']}",
            status="Paid" if match_status != "Pending Match" else "Pending",
            match_status=match_status,
            format_style=format_style
        )
        
        invoices.append({
            'path': invoice_path,
            'number': invoice_number,
            'date': invoice_date,
            'vendor': vendor['name'],
            'amount': invoice_amount,
            'bank_amount': amount,
            'bank_date': row['Date'],
            'match_status': match_status
        })

    # Display invoice information
    invoice_data = []
    for invoice in invoices:
        invoice_data.append({
            'Invoice Number': invoice['number'],
            'Invoice Date': invoice['date'],
            'Vendor': invoice['vendor'],
            'Invoice Amount': invoice['amount'],
            'Bank Amount': invoice['bank_amount'],
            'Bank Date': invoice['bank_date'],
            'Match Status': invoice['match_status']
        })

    invoice_df = pd.DataFrame(invoice_data)
    # Tables displayed at the end

    # Show ledger vs invoice distributions side by side
    st.subheader("Distributions")
    col1, col2 = st.columns(2)
    with col1:
        ledger_counts = ledger_df['Bank_Status'].value_counts()
        fig_ledger = px.pie(values=ledger_counts.values, names=ledger_counts.index, title='Ledger Match Status')
        st.plotly_chart(fig_ledger, use_container_width=True)
    with col2:
        status_counts = invoice_df['Match Status'].value_counts()
        fig_invoice = px.pie(values=status_counts.values, names=status_counts.index, title='Invoice Match Status')
        st.plotly_chart(fig_invoice, use_container_width=True)

    # Prepare CSVs for download
    bank_recon_cols = [c for c in ['Date', 'Description', 'Reference', 'Withdrawal', 'Deposit'] if c in bank_df.columns]
    ledger_recon_cols = [c for c in ['Date', 'Description', 'Reference', 'Debit', 'Credit'] if c in ledger_df.columns]

    bank_recon_df = bank_df[bank_recon_cols].copy()
    bank_extra_df = bank_df.drop(columns=bank_recon_cols, errors='ignore')

    ledger_recon_df = ledger_df[ledger_recon_cols].copy()
    ledger_extra_df = ledger_df.drop(columns=ledger_recon_cols, errors='ignore')

    bank_recon_csv = bank_recon_df.to_csv(index=False)
    bank_extra_csv = bank_extra_df.to_csv(index=False)
    ledger_recon_csv = ledger_recon_df.to_csv(index=False)
    ledger_extra_csv = ledger_extra_df.to_csv(index=False)

    # Download all assets as ZIP (invoices + CSVs)
    st.subheader("Download All Outputs")
    if st.button("Generate ZIP (Invoices + CSVs)"):
        import zipfile
        zip_path = os.path.join(tempfile.mkdtemp(), "reconciliation_outputs.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add PDFs
            for invoice in invoices:
                zipf.write(invoice['path'], os.path.basename(invoice['path']))
            # Add CSVs
            zipf.writestr('bank_statement_recon.csv', bank_recon_csv)
            zipf.writestr('bank_statement_extra.csv', bank_extra_csv)
            zipf.writestr('general_ledger_recon.csv', ledger_recon_csv)
            zipf.writestr('general_ledger_extra.csv', ledger_extra_csv)
        with open(zip_path, "rb") as f:
            zip_data = f.read()
        st.download_button(
            label="Download ZIP",
            data=zip_data,
            file_name="reconciliation_outputs.zip",
            mime="application/zip"
        )

    # Individual CSV downloads
    st.subheader("Download CSVs")
    col_csv1, col_csv2 = st.columns(2)
    with col_csv1:
        st.download_button(
            label="Bank Statement (Reconciliation)",
            data=bank_recon_csv,
            file_name="bank_statement_recon.csv",
            mime="text/csv"
        )
        st.download_button(
            label="General Ledger (Reconciliation)",
            data=ledger_recon_csv,
            file_name="general_ledger_recon.csv",
            mime="text/csv"
        )
    with col_csv2:
        st.download_button(
            label="Bank Statement (Extra)",
            data=bank_extra_csv,
            file_name="bank_statement_extra.csv",
            mime="text/csv"
        )
        st.download_button(
            label="General Ledger (Extra)",
            data=ledger_extra_csv,
            file_name="general_ledger_extra.csv",
            mime="text/csv"
        )

    # Display tables at the end
    st.subheader("Invoice Data")
    st.dataframe(invoice_df)
    st.subheader("General Ledger Data")
    st.dataframe(ledger_df)
    st.subheader("Bank Statement Data")
    st.dataframe(bank_df)

if __name__ == "__main__":
    main()

# Required JPGs for images directory:
#   logo1.jpg, logo2.jpg, logo3.jpg, logo4.jpg, logo5.jpg, logo6.jpg, logo7.jpg, logo8.jpg, logo9.jpg
#   watermark_paid.jpg, watermark_due.jpg, watermark_logo_faint.jpg, watermark_stamp.jpg, watermark_creative.jpg, watermark_stripe.jpg
#   (Optional: qr_placeholder.jpg)