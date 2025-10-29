# finstock-ai/backend/app/setup_db.py
import sqlite3
import os

# Define the path for the database in the 'data' folder
DB_PATH = os.path.join("data", "stocks.db")
DB_DIR = os.path.dirname(DB_PATH)

# Ensure the 'data' directory exists
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

# Sample data: (Symbol, Company Name)
# We'll use symbols that yfinance recognizes
stocks_to_add = [
    ('RELIANCE.NS', 'Reliance Industries Ltd.'),
    ('TCS.NS', 'Tata Consultancy Services Ltd.'),
    ('HDFCBANK.NS', 'HDFC Bank Ltd.'),
    ('INFY.NS', 'Infosys Ltd.'),
    ('ICICIBANK.NS', 'ICICI Bank Ltd.'),
    ('HINDUNILVR.NS', 'Hindustan Unilever Ltd.'),
    ('SBIN.NS', 'State Bank of India'),
    ('BHARTIARTL.NS', 'Bharti Airtel Ltd.'),
    ('ITC.NS', 'ITC Ltd.'),
    ('LTIM.NS', 'LTIMindtree Ltd.')
]

try:
    # Connect to the SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create the 'stocks' table
    # IF NOT EXISTS prevents errors if you run this script multiple times
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT NOT NULL
    )
    ''')
    print("Table 'stocks' created (or already exists).")

    # Insert the data
    # executemany is efficient for inserting multiple rows
    # IGNORE ensures that duplicate PRIMARY KEYS (symbols) are skipped
    cursor.executemany("INSERT OR IGNORE INTO stocks (symbol, name) VALUES (?, ?)", stocks_to_add)

    # Commit the changes and close the connection
    conn.commit()
    print(f"Successfully added {len(stocks_to_add)} stocks to the database.")

except sqlite3.Error as e:
    print(f"An error occurred: {e}")

finally:
    if conn:
        conn.close()
        print("Database connection closed.")