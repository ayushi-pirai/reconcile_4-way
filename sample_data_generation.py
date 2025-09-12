import pandas as pd
from datetime import datetime, timedelta
import random

# Generate more comprehensive sample data
def generate_comprehensive_sample_data():
    # Generate sample ledger data with more variety
    ledger_data = {
        'Date': [],
        'Description': [],
        'Reference': [],
        'Debit': [],
        'Credit': [],
        'Account': []
    }
    
    # Generate sample bank statement data
    bank_data = {
        'Date': [],
        'Description': [],
        'Reference': [],
        'Withdrawal': [],
        'Deposit': [],
        'Balance': []
    }
    
    # Start with a balance
    current_balance = 15000.00
    
    # Dates for October 2023
    dates = [datetime(2023, 10, i) for i in range(1, 31)]
    
    # Common transaction descriptions
    descriptions = {
        'Office Supplies': ['OFFICE SUPPLIES INC', 'OFFICE DEPOT', 'STAPLES'],
        'Client Payment': ['ABC CORP', 'XYZ LTD', 'ACME INC', 'GLOBEX CORP'],
        'Utility Bill': ['ELECTRIC COMPANY', 'WATER AUTHORITY', 'GAS COMPANY'],
        'Software': ['SOFTWARE CO', 'ADOBE INC', 'MICROSOFT CORP'],
        'Rent': ['LANDLORD PROPERTY', 'REALTY MANAGEMENT', 'PROPERTY CO'],
        'Equipment': ['TECH STORE', 'COMPUTER WORLD', 'OFFICE EQUIP'],
        'Consulting': ['JOHN SMITH', 'JANE DOE', 'CONSULTING FIRM'],
        'Marketing': ['MARKETING SOLUTIONS', 'AD AGENCY', 'DIGITAL MARKETING'],
        'Travel': ['AIRLINE COMPANY', 'HOTEL CHAIN', 'RENTAL CAR CO'],
        'Refund': ['CLIENT REFUND', 'CUSTOMER REFUND'],
        'Insurance': ['INSURANCE CO', 'HEALTH INSURANCE', 'PROPERTY INS'],
        'Hosting': ['WEB SERVICES INC', 'CLOUD HOSTING', 'SERVER CO'],
        'Development': ['SOFTWARE DEV', 'WEB DEVELOPMENT', 'APP DEVELOPMENT'],
        'Training': ['PROFESSIONAL DEVELOPMENT', 'TRAINING COURSE', 'SEMINAR'],
        'Miscellaneous': ['MISC EXPENSE', 'SUNDRY ITEMS', 'GENERAL EXPENSE']
    }
    
    # Generate ledger transactions
    ledger_entries = 40
    for i in range(ledger_entries):
        date = random.choice(dates)
        desc_category = random.choice(list(descriptions.keys()))
        description = f"{desc_category} - {random.choice(descriptions[desc_category])}" if random.random() > 0.3 else desc_category
        
        # Create some variations in references
        if random.random() > 0.7:
            reference = f"INV-{1000 + i}"
        else:
            reference = f"PMT-{2000 + i}"
            
        # Determine if debit or credit
        is_credit = random.random() > 0.3  # More credits than debits for cash account
        
        amount = round(random.uniform(50, 5000), 2)
        
        ledger_data['Date'].append(date.strftime('%Y-%m-%d'))
        ledger_data['Description'].append(description)
        ledger_data['Reference'].append(reference)
        
        if is_credit:
            ledger_data['Debit'].append(0)
            ledger_data['Credit'].append(amount)
        else:
            ledger_data['Debit'].append(amount)
            ledger_data['Credit'].append(0)
            
        ledger_data['Account'].append('Cash at Bank')
    
    # Generate bank transactions with matches, discrepancies, and unmatched entries
    bank_entries = 45  # More bank entries to create some unmatched
    used_ledger_indices = set()
    
    for i in range(bank_entries):
        # Decide if this should match a ledger entry or not
        should_match = random.random() > 0.2  # 80% should match
        
        if should_match and len(used_ledger_indices) < ledger_entries:
            # Find a ledger entry that hasn't been used yet
            ledger_idx = random.choice([i for i in range(ledger_entries) if i not in used_ledger_indices])
            used_ledger_indices.add(ledger_idx)
            
            ledger_entry = {
                'Date': ledger_data['Date'][ledger_idx],
                'Description': ledger_data['Description'][ledger_idx],
                'Reference': ledger_data['Reference'][ledger_idx],
                'Amount': ledger_data['Credit'][ledger_idx] if ledger_data['Credit'][ledger_idx] > 0 else ledger_data['Debit'][ledger_idx]
            }
            
            # Decide what kind of match this will be
            match_type = random.choice(['exact', 'date_discrepancy', 'amount_discrepancy', 'fuzzy'])
            
            if match_type == 'exact':
                # Exact match
                bank_date = ledger_entry['Date']
                bank_desc = ledger_entry['Description'].upper()
                bank_amount = ledger_entry['Amount']
                
            elif match_type == 'date_discrepancy':
                # Date discrepancy (1-5 days difference)
                date_diff = random.randint(1, 5)
                ledger_date = datetime.strptime(ledger_entry['Date'], '%Y-%m-%d')
                if random.random() > 0.5:
                    bank_date = (ledger_date + timedelta(days=date_diff)).strftime('%Y-%m-%d')
                else:
                    bank_date = (ledger_date - timedelta(days=date_diff)).strftime('%Y-%m-%d')
                bank_desc = ledger_entry['Description'].upper()
                bank_amount = ledger_entry['Amount']
                
            elif match_type == 'amount_discrepancy':
                # Amount discrepancy (small difference)
                bank_date = ledger_entry['Date']
                bank_desc = ledger_entry['Description'].upper()
                amount_diff = round(random.uniform(0.01, 10.00), 2)
                if random.random() > 0.5:
                    bank_amount = ledger_entry['Amount'] + amount_diff
                else:
                    bank_amount = max(0.01, ledger_entry['Amount'] - amount_diff)
                    
            else:  # fuzzy match
                # Fuzzy match (similar but not identical description)
                bank_date = ledger_entry['Date']
                orig_desc = ledger_entry['Description']
                if ' - ' in orig_desc:
                    parts = orig_desc.split(' - ')
                    bank_desc = f"{parts[0].upper()} - {parts[1]}"
                else:
                    similar_descs = descriptions.get(orig_desc, [orig_desc.upper()])
                    bank_desc = random.choice(similar_descs)
                bank_amount = ledger_entry['Amount']
                
        else:
            # Create an unmatched bank transaction
            date = random.choice(dates)
            desc_category = random.choice(list(descriptions.keys()))
            bank_desc = random.choice(descriptions[desc_category])
            
            bank_date = date.strftime('%Y-%m-%d')
            bank_amount = round(random.uniform(50, 3000), 2)
            
        # Determine if withdrawal or deposit
        is_deposit = random.random() > 0.6  # More withdrawals than deposits
        
        # Update balance
        if is_deposit:
            current_balance += bank_amount
            withdrawal = 0
            deposit = bank_amount
        else:
            current_balance -= bank_amount
            withdrawal = bank_amount
            deposit = 0
            
        # Add to bank data
        bank_data['Date'].append(bank_date)
        bank_data['Description'].append(bank_desc)
        bank_data['Reference'].append(f"CHK{3000 + i}")
        bank_data['Withdrawal'].append(withdrawal)
        bank_data['Deposit'].append(deposit)
        bank_data['Balance'].append(round(current_balance, 2))
    
    ledger_df = pd.DataFrame(ledger_data)
    bank_df = pd.DataFrame(bank_data)
    
    return ledger_df, bank_df

# Generate the data
ledger_df, bank_df = generate_comprehensive_sample_data()

# Save to CSV files
ledger_df.to_csv('comprehensive_ledger.csv', index=False)
bank_df.to_csv('comprehensive_bank_statement.csv', index=False)

print("Sample data generated and saved to comprehensive_ledger.csv and comprehensive_bank_statement.csv")
print(f"Ledger entries: {len(ledger_df)}")
print(f"Bank entries: {len(bank_df)}")