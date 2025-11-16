import pandas as pd
from pathlib import Path
from typing import Optional
from database import FinanceDB
from datetime import datetime


class ChaseImporter:
    """Imports Chase credit card CSV files."""
    
    def __init__(self, db: FinanceDB):
        self.db = db
    
    def import_csv(self, csv_path: str, account_name: str = "Chase Credit Card") -> int:
        """
        Import Chase CSV file into database.
        
        Args:
            csv_path: Path to Chase CSV file
            account_name: Name to give this account
            
        Returns:
            Number of transactions imported
        """
        print(f"\n📂 Importing: {csv_path}")
        
        # Check if file exists
        if not Path(csv_path).exists():
            print(f"❌ File not found: {csv_path}")
            return 0
        
        # Read CSV
        try:
            df = pd.read_csv(csv_path)
            print(f"✅ Read {len(df)} rows from CSV")
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return 0
        
        # Display columns to verify format
        print(f"\n📋 Columns found: {list(df.columns)}")
        print(f"\n👀 First few rows:")
        print(df.head())
        
        # Clean and standardize data
        df_clean = self._clean_chase_data(df)
        
        # Add or get account
        account_id = self.db.add_account(
            account_name=account_name,
            account_type="Credit Card",
            institution="Chase"
        )
        
        # Insert transactions
        inserted = self.db.insert_transactions(df_clean, account_id)
        
        return inserted
    
    def _clean_chase_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize Chase CSV data."""
        df_clean = df.copy()
        
        # Standardize column names (Chase format may vary slightly)
        column_mapping = {}
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'transaction' in col_lower and 'date' in col_lower:
                column_mapping[col] = 'transaction_date'
            elif 'post' in col_lower and 'date' in col_lower:
                column_mapping[col] = 'post_date'
            elif 'description' in col_lower:
                column_mapping[col] = 'description'
            elif 'category' in col_lower:
                column_mapping[col] = 'original_category'
            elif 'type' in col_lower:
                column_mapping[col] = 'transaction_type'
            elif 'amount' in col_lower:
                column_mapping[col] = 'amount'
            elif 'memo' in col_lower:
                column_mapping[col] = 'memo'
        
        df_clean.rename(columns=column_mapping, inplace=True)
        
        # Convert dates to standard format
        if 'transaction_date' in df_clean.columns:
            df_clean['transaction_date'] = pd.to_datetime(df_clean['transaction_date']).dt.strftime('%Y-%m-%d')
        
        if 'post_date' in df_clean.columns:
            df_clean['post_date'] = pd.to_datetime(df_clean['post_date']).dt.strftime('%Y-%m-%d')
        
        # Clean amount (remove commas, convert to float)
        if 'amount' in df_clean.columns:
            df_clean['amount'] = df_clean['amount'].astype(float)
        
        # Remove any completely empty rows
        df_clean = df_clean.dropna(how='all')
        
        # Fill missing memos with empty string
        if 'memo' in df_clean.columns:
            df_clean['memo'] = df_clean['memo'].fillna('')
        else:
            df_clean['memo'] = ''
        
        print(f"\n✅ Cleaned data:")
        print(f"   Columns: {list(df_clean.columns)}")
        print(f"   Rows: {len(df_clean)}")
        print(f"   Date range: {df_clean['transaction_date'].min()} to {df_clean['transaction_date'].max()}")
        
        return df_clean


class ImportManager:
    """Manages importing from multiple file types and institutions."""
    
    def __init__(self, db: FinanceDB):
        self.db = db
        self.chase_importer = ChaseImporter(db)
    
    def import_file(self, file_path: str, institution: str = "chase", account_name: Optional[str] = None):
        """
        Import a file based on institution type.
        
        Args:
            file_path: Path to the file
            institution: Institution name (chase, bofa, discover, etc.)
            account_name: Custom account name (optional)
        """
        institution = institution.lower()
        
        if institution == "chase":
            if account_name is None:
                account_name = f"Chase - {Path(file_path).stem}"
            return self.chase_importer.import_csv(file_path, account_name)
        else:
            print(f"❌ Unsupported institution: {institution}")
            print(f"   Currently supported: chase")
            return 0


# Test/Usage script
if __name__ == "__main__":
    print("="*70)
    print("MoneyMatters - Transaction Importer")
    print("="*70)
    
    # Initialize database
    db = FinanceDB()
    
    # Create importer
    importer = ImportManager(db)
    
    # Import Chase CSV
    raw_data_dir = Path("data/raw")
    
    # Find all CSV files in raw data directory
    csv_files = list(raw_data_dir.glob("*.csv"))
    
    if not csv_files:
        print("\n⚠️  No CSV files found in data/raw/")
        print("   Please add your Chase CSV file to the data/raw/ folder")
    else:
        print(f"\n📂 Found {len(csv_files)} CSV file(s):")
        for csv_file in csv_files:
            print(f"   - {csv_file.name}")
        
        print("\n" + "="*70)
        
        # Import each file
        for csv_file in csv_files:
            print(f"\nImporting: {csv_file.name}")
            
            # You can customize the account name here
            account_name = f"Chase - {csv_file.stem}"
            
            imported = importer.import_file(
                file_path=str(csv_file),
                institution="chase",
                account_name=account_name
            )
            
            print(f"\n✅ Imported {imported} transactions from {csv_file.name}")
    
    # Show summary
    print("\n" + "="*70)
    print("📊 Account Summaries:")
    print("="*70)
    
    summary = db.get_summary()
    print(f"\nTotal Accounts: {summary['total_accounts']}")
    print(f"Total Transactions: {summary['total_transactions']}")
    
    for acc in summary['by_account']:
        print(f"\n💳 {acc['account_name']} ({acc['account_type']})")
        print(f"   {acc['institution']}")
        print(f"   Transactions: {acc['transaction_count']}")
        
        if acc['display_type'] == 'credit_card':
            print(f"   Total Charges: ${acc['total_charges']:,.2f}")
            print(f"   Total Payments/Credits: ${acc['total_payments']:,.2f}")
            print(f"   Net Balance Change: ${acc['net_change']:,.2f}")
            if acc['net_change'] < 0:
                print(f"   (You charged ${abs(acc['net_change']):,.2f} more than you paid)")
        else:
            print(f"   Total Income: ${acc['total_income']:,.2f}")
            print(f"   Total Expenses: ${acc['total_expenses']:,.2f}")
            print(f"   Net: ${acc['net_change']:,.2f}")
            
    
    # Show recent transactions
    if summary['total_transactions'] > 0:
        print("\n" + "="*70)
        print("📝 Recent Transactions (last 10):")
        print("="*70)
        
        recent = db.get_transactions(limit=10)
        for _, row in recent.iterrows():
            amount_str = f"${abs(row['amount']):,.2f}"
            symbol = "💸" if row['amount'] < 0 else "💰"
            print(f"{symbol} {row['transaction_date']} | {row['description'][:40]:40} | {amount_str:>12}")
    
    db.close()