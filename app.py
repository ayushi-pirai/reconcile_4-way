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

# Set page configuration
st.set_page_config(
    page_title="Bank Statement Reconciliation",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("🏦 Bank Statement Reconciliation")
st.markdown("""
This tool helps you reconcile your ledger entries with bank statements.
Upload your ledger data and bank statements to identify matches, discrepancies, and unmatched transactions.
""")

# Sidebar for navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Upload Data", "Reconciliation Results", "Analysis & Reports"])

# Sample data generation function
def generate_sample_data():
    # Generate sample ledger data
    ledger_data = {
        'Date': [datetime(2023, 10, i).strftime('%Y-%m-%d') for i in range(1, 16)],
        'Description': [
            'Office Supplies', 'Client Payment - ABC Corp', 'Utility Bill', 
            'Software Subscription', 'Client Payment - XYZ Ltd', 'Rent Payment',
            'Equipment Purchase', 'Consulting Fee - John Smith', 'Marketing Services',
            'Travel Expenses', 'Client Refund', 'Insurance Payment', 
            'Website Hosting', 'Professional Development', 'Miscellaneous Expenses'
        ],
        'Reference': ['INV-100{}'.format(i) for i in range(1, 16)],
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
            'OFFICE SUPPLIES INC', 'ABC CORP', 'ELECTRIC COMPANY', 
            'SOFTWARE CO', 'XYZ LTD', 'LANDLORD PROPERTY', 'TECH STORE',
            'JOHN SMITH', 'MARKETING SOLUTIONS', 'AIRLINE COMPANY', 
            'CLIENT REFUND', 'INSURANCE CO', 'WEB SERVICES INC'
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
    
    ledger_df = pd.DataFrame(ledger_data)
    bank_df = pd.DataFrame(bank_data)
    
    return ledger_df, bank_df

# Matching algorithm
def match_transactions(ledger_df, bank_df):
    # Initialize result columns
    ledger_df['Status'] = 'Not Matched'
    ledger_df['Matched_Bank_Index'] = -1
    ledger_df['Discrepancy_Type'] = ''
    ledger_df['Discrepancy_Amount'] = 0.0
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
                ledger_df.at[l_idx, 'Status'] = 'Matched'
                ledger_df.at[l_idx, 'Matched_Bank_Index'] = b_idx
                bank_df.at[b_idx, 'Status'] = 'Matched'
                bank_df.at[b_idx, 'Matched_Ledger_Index'] = l_idx
                bank_copy.drop(b_idx, inplace=True)
                break
    
    # Second pass: Amount matching with date tolerance
    for l_idx, ledger_row in ledger_copy[ledger_df['Status'] == 'Not Matched'].iterrows():
        ledger_amount = ledger_row['Credit'] if ledger_row['Credit'] > 0 else ledger_row['Debit']
        ledger_date = datetime.strptime(ledger_row['Date'], '%Y-%m-%d')
        
        for b_idx, bank_row in bank_copy[bank_df['Status'] == 'Not Matched'].iterrows():
            bank_amount = bank_row['Deposit'] if bank_row['Deposit'] > 0 else bank_row['Withdrawal']
            bank_date = datetime.strptime(bank_row['Date'], '%Y-%m-%d')
            
            # Check for amount match with date discrepancy
            if abs(ledger_amount - bank_amount) < 0.01 and abs((ledger_date - bank_date).days) <= 7:
                ledger_df.at[l_idx, 'Status'] = 'Discrepancy Detected'
                ledger_df.at[l_idx, 'Matched_Bank_Index'] = b_idx
                ledger_df.at[l_idx, 'Discrepancy_Type'] = 'Date Variance'
                ledger_df.at[l_idx, 'Discrepancy_Amount'] = abs((ledger_date - bank_date).days)
                bank_df.at[b_idx, 'Status'] = 'Discrepancy Detected'
                bank_df.at[b_idx, 'Matched_Ledger_Index'] = l_idx
                bank_copy.drop(b_idx, inplace=True)
                break
            # Check for date match with amount discrepancy
            elif abs((ledger_date - bank_date).days) <= 2 and abs(ledger_amount - bank_amount) >= 0.01:
                ledger_df.at[l_idx, 'Status'] = 'Discrepancy Detected'
                ledger_df.at[l_idx, 'Matched_Bank_Index'] = b_idx
                ledger_df.at[l_idx, 'Discrepancy_Type'] = 'Amount Variance'
                ledger_df.at[l_idx, 'Discrepancy_Amount'] = abs(ledger_amount - bank_amount)
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

# File upload and processing
def process_uploaded_files(uploaded_ledger, uploaded_bank):
    if uploaded_ledger is not None and uploaded_bank is not None:
        try:
            # Read files based on extension
            if uploaded_ledger.name.endswith('.csv'):
                ledger_df = pd.read_csv(uploaded_ledger)
            else:
                ledger_df = pd.read_excel(uploaded_ledger)
                
            if uploaded_bank.name.endswith('.csv'):
                bank_df = pd.read_csv(uploaded_bank)
            else:
                bank_df = pd.read_excel(uploaded_bank)
                
            return ledger_df, bank_df
        except Exception as e:
            st.error(f"Error processing files: {str(e)}")
            return None, None
    return None, None

# Visualization functions
def create_summary_visualization(ledger_df, bank_df):
    col1, col2, col3 = st.columns(3)
    
    matched_count = len(ledger_df[ledger_df['Status'] == 'Matched'])
    discrepancy_count = len(ledger_df[ledger_df['Status'] == 'Discrepancy Detected'])
    unmatched_count = len(ledger_df[ledger_df['Status'] == 'Not Matched'])
    total_count = len(ledger_df)
    
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
        title='Transaction Reconciliation Status',
        color=['Matched', 'Discrepancies', 'Unmatched'],
        color_discrete_map={'Matched':'green', 'Discrepancies':'orange', 'Unmatched':'red'}
    )
    st.plotly_chart(fig, use_container_width=True)

# Main app logic
if page == "Upload Data":
    st.header("Upload Data")
    
    # Option to use sample data or upload files
    use_sample_data = st.checkbox("Use sample data for demonstration", value=True)
    
    if use_sample_data:
        ledger_df, bank_df = generate_sample_data()
        st.success("Sample data loaded successfully!")
        
        # Display sample data
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Sample Ledger Data")
            st.dataframe(ledger_df)
        with col2:
            st.subheader("Sample Bank Statement Data")
            st.dataframe(bank_df)
            
        # Save to session state
        st.session_state.ledger_df = ledger_df
        st.session_state.bank_df = bank_df
        
    else:
        st.subheader("Upload your files")
        uploaded_ledger = st.file_uploader("Upload Ledger File (CSV or Excel)", type=['csv', 'xlsx'])
        uploaded_bank = st.file_uploader("Upload Bank Statement (CSV or Excel)", type=['csv', 'xlsx'])
        
        if uploaded_ledger and uploaded_bank:
            ledger_df, bank_df = process_uploaded_files(uploaded_ledger, uploaded_bank)
            if ledger_df is not None and bank_df is not None:
                st.session_state.ledger_df = ledger_df
                st.session_state.bank_df = bank_df
                st.success("Files uploaded successfully!")
                
                # Display uploaded data
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Uploaded Ledger Data")
                    st.dataframe(ledger_df.head())
                with col2:
                    st.subheader("Uploaded Bank Statement Data")
                    st.dataframe(bank_df.head())
    
    # Process button
    if st.button("Process Reconciliation") and 'ledger_df' in st.session_state and 'bank_df' in st.session_state:
        with st.spinner("Processing transactions..."):
            ledger_result, bank_result = match_transactions(
                st.session_state.ledger_df, 
                st.session_state.bank_df
            )
            st.session_state.ledger_result = ledger_result
            st.session_state.bank_result = bank_result
            st.session_state.processed = True
            st.success("Reconciliation completed!")
            st.rerun()

elif page == "Reconciliation Results":
    st.header("Reconciliation Results")
    
    if 'processed' not in st.session_state:
        st.warning("Please process data first on the Upload Data page.")
    else:
        ledger_result = st.session_state.ledger_result
        bank_result = st.session_state.bank_result
        
        # Summary visualization
        create_summary_visualization(ledger_result, bank_result)
        
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
            discrepancies = ledger_result[ledger_result['Status'] == 'Discrepancy Detected']
            st.subheader("Transactions with Discrepancies")
            if len(discrepancies) > 0:
                st.dataframe(discrepancies)
                
                # Allow adding comments
                for idx, row in discrepancies.iterrows():
                    with st.expander(f"Discrepancy: {row['Description']} - {row['Reference']}"):
                        comment = st.text_input(
                            "Add comment or action:",
                            key=f"comment_{idx}",
                            value=""
                        )
                        if st.button("Save Comment", key=f"save_{idx}"):
                            st.success(f"Comment saved for {row['Reference']}")
            else:
                st.success("No discrepancies found!")
        
        with tab3:
            unmatched = ledger_result[ledger_result['Status'] == 'Not Matched']
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
                                key=f"match_{idx}"
                            )
                            if selected_match and st.button("Confirm Match", key=f"confirm_{idx}"):
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
                            key=f"action_{idx}"
                        )
                        if st.button("Save Action", key=f"save_action_{idx}"):
                            st.success(f"Action saved for {row['Reference']}")
            else:
                st.success("No AI flags generated!")

elif page == "Analysis & Reports":
    st.header("Analysis & Reports")
    
    if 'processed' not in st.session_state:
        st.warning("Please process data first on the Upload Data page.")
    else:
        ledger_result = st.session_state.ledger_result
        
        # Time analysis
        st.subheader("Transaction Timeline")
        ledger_result['Date'] = pd.to_datetime(ledger_result['Date'])
        daily_counts = ledger_result.groupby('Date').size().reset_index(name='Count')
        
        fig = px.line(daily_counts, x='Date', y='Count', title='Transactions per Day')
        st.plotly_chart(fig, use_container_width=True)
        
        # Amount analysis
        st.subheader("Transaction Amount Distribution")
        ledger_result['Amount'] = ledger_result[['Debit', 'Credit']].max(axis=1)
        fig = px.histogram(ledger_result, x='Amount', title='Distribution of Transaction Amounts')
        st.plotly_chart(fig, use_container_width=True)
        
        # Generate report
        st.subheader("Generate Reconciliation Report")
        if st.button("Generate PDF Report"):
            st.info("This feature would generate a comprehensive PDF report in a production environment")
            
        # Export results
        st.subheader("Export Results")
        csv = ledger_result.to_csv(index=False)
        st.download_button(
            label="Download Reconciliation Results as CSV",
            data=csv,
            file_name="reconciliation_results.csv",
            mime="text/csv"
        )

# Footer
st.sidebar.markdown("---")
# st.sidebar.info(
#     "This is a demonstration of bank statement reconciliation using Streamlit. "
#     "In a production environment, this would integrate with OCR and more advanced matching algorithms."
# )