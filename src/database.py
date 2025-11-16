import sqlite3
from pathlib import Path
from typing import Optional
import pandas as pd


class FinanceDB:
    """Manages SQLite database for financial transactions."""
    
    def __init__(self, db_path: str = "data/finance.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.init_database()
    
    def init_database(self):
        """Initialize database and create tables if they don't exist."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL UNIQUE,
                account_type TEXT NOT NULL,
                institution TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                transaction_date DATE NOT NULL,
                post_date DATE,
                description TEXT NOT NULL,
                original_category TEXT,
                custom_category TEXT,
                transaction_type TEXT,
                amount REAL NOT NULL,
                memo TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts (account_id),
                UNIQUE(account_id, transaction_date, description, amount)
            )
        """)
        
        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE,
                category_type TEXT NOT NULL,
                parent_category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Category rules table (for auto-categorization)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                category_name TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_name) REFERENCES categories (category_name)
            )
        """)
        
        self.conn.commit()
        print(f"✅ Database initialized: {self.db_path}")
    
    def add_account(self, account_name: str, account_type: str, institution: str) -> int:
        """Add a new account. Returns account_id."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO accounts (account_name, account_type, institution)
                VALUES (?, ?, ?)
            """, (account_name, account_type, institution))
            self.conn.commit()
            print(f"✅ Added account: {account_name}")
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Account already exists, get its ID
            cursor.execute("""
                SELECT account_id FROM accounts WHERE account_name = ?
            """, (account_name,))
            account_id = cursor.fetchone()[0]
            print(f"ℹ️  Account already exists: {account_name} (ID: {account_id})")
            return account_id
    
    def get_account_id(self, account_name: str) -> Optional[int]:
        """Get account ID by name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT account_id FROM accounts WHERE account_name = ?", (account_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def insert_transactions(self, transactions_df: pd.DataFrame, account_id: int) -> int:
        """
        Insert transactions from DataFrame.
        Returns number of new transactions inserted.
        """
        inserted = 0
        skipped = 0
        
        cursor = self.conn.cursor()
        
        for _, row in transactions_df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO transactions (
                        account_id, transaction_date, post_date, description,
                        original_category, transaction_type, amount, memo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id,
                    row['transaction_date'],
                    row.get('post_date'),
                    row['description'],
                    row.get('original_category'),
                    row.get('transaction_type'),
                    row['amount'],
                    row.get('memo')
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                # Duplicate transaction
                skipped += 1
                continue
        
        self.conn.commit()
        print(f"✅ Inserted {inserted} new transactions")
        if skipped > 0:
            print(f"⏭️  Skipped {skipped} duplicate transactions")
        
        return inserted
    
    def get_transactions(self, account_id: Optional[int] = None, limit: int = 100) -> pd.DataFrame:
        """Get transactions as DataFrame."""
        query = """
            SELECT 
                t.*,
                a.account_name,
                a.institution
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
        """
        
        if account_id:
            query += f" WHERE t.account_id = {account_id}"
        
        query += f" ORDER BY t.transaction_date DESC LIMIT {limit}"
        
        return pd.read_sql_query(query, self.conn)
    
    
    def get_summary(self, account_id: Optional[int] = None) -> dict:
        """Get summary statistics, account-type aware."""
        cursor = self.conn.cursor()
        
        # Get all accounts or specific account
        if account_id:
            cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
            accounts = [cursor.fetchone()]
        else:
            cursor.execute("SELECT * FROM accounts")
            accounts = cursor.fetchall()
        
        summary = {
            'total_transactions': 0,
            'total_accounts': len(accounts),
            'by_account': []
        }
        
        for account in accounts:
            acc_id, acc_name, acc_type, institution, _ = account
            
            # Get transaction stats for this account
            cursor.execute("""
                SELECT 
                    COUNT(*) as count,
                    SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as negative_sum,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as positive_sum,
                    SUM(amount) as net
                FROM transactions 
                WHERE account_id = ?
            """, (acc_id,))
            
            result = cursor.fetchone()
            count, negative_sum, positive_sum, net = result
            
            negative_sum = abs(negative_sum) if negative_sum else 0
            positive_sum = positive_sum if positive_sum else 0
            net = net if net else 0
            
            # Interpret based on account type
            if 'credit' in acc_type.lower():
                account_summary = {
                    'account_id': acc_id,
                    'account_name': acc_name,
                    'account_type': acc_type,
                    'institution': institution,
                    'transaction_count': count,
                    'total_charges': negative_sum,
                    'total_payments': positive_sum,
                    'net_change': net,
                    'display_type': 'credit_card'
                }
            else:
                # Regular bank account
                account_summary = {
                    'account_id': acc_id,
                    'account_name': acc_name,
                    'account_type': acc_type,
                    'institution': institution,
                    'transaction_count': count,
                    'total_expenses': negative_sum,
                    'total_income': positive_sum,
                    'net_change': net,
                    'display_type': 'bank_account'
                }
            
            summary['by_account'].append(account_summary)
            summary['total_transactions'] += count
        
        return summary
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed")


# Test the database
if __name__ == "__main__":
    print("Testing FinanceDB...\n")
    
    db = FinanceDB()
    
    # Add a test account
    account_id = db.add_account(
        account_name="Chase Freedom",
        account_type="Credit Card",
        institution="Chase"
    )
    
    # Get summary
    summary = db.get_summary()
    print(f"\n📊 Database Summary:")
    print(f"   Total Accounts: {summary['total_accounts']}")
    print(f"   Total Transactions: {summary['total_transactions']}")
    
    for acc in summary['by_account']:
        print(f"\n   📱 {acc['account_name']} ({acc['account_type']}):")
        if acc['display_type'] == 'credit_card':
            print(f"      Charges: ${acc['total_charges']:,.2f}")
            print(f"      Payments: ${acc['total_payments']:,.2f}")
            print(f"      Net Change: ${acc['net_change']:,.2f}")
        else:
            print(f"      Income: ${acc['total_income']:,.2f}")
            print(f"      Expenses: ${acc['total_expenses']:,.2f}")
            print(f"      Net: ${acc['net_change']:,.2f}")
    
    db.close()