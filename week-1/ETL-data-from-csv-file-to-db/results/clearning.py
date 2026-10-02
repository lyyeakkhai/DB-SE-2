#!/usr/bin/env python3
"""
ETL Process: Clean CSV Data and Load into PostgreSQL Database
Source Notebook: week-1/ETL-data-from-csv-file-to-db/notebooks/student_practice-etl_data_from_csv_into_db.ipynb
Target Script: week-1/ETL-data-from-csv-file-to-db/results/clearning.py
"""

import os
import warnings
import numpy as np
import pandas as pd
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

# Ignore warning
warnings.filterwarnings('ignore')

# ----------------------------------------------------------------------
# File paths
# ----------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # week-1/ETL-data-from-csv-file-to-db
DATASET_PATH = os.path.join(BASE_DIR, 'dataset', 'sales_transaction_dataset.csv')
RESULTS_DIR = SCRIPT_DIR
CLEANED_CSV_PATH = os.path.join(RESULTS_DIR, 'sales_transaction_dataset_cleaned.csv')
CLEANED_XLSX_PATH = os.path.join(RESULTS_DIR, 'sales_transaction_dataset_cleaned.xlsx')

if not os.path.exists(DATASET_PATH):
    DATASET_PATH = '../dataset/sales_transaction_dataset.csv'

# ======================================================================
# III. Read Dataset
# ======================================================================
print(f"Reading dataset from: {DATASET_PATH}")
df = pd.read_csv(DATASET_PATH)

# ======================================================================
# IV. Exploratory Data Analysis (EDA)
# ======================================================================
# Show top 5 records
print("\n--- Top 5 records ---")
print(df.head())

# Show bottom 5 records
print("\n--- Bottom 5 records ---")
print(df.tail())

# Show random 5 sample
print("\n--- Random 5 samples ---")
print(df.sample(5))

# Check number of row and column
print("\n--- Shape (rows, columns) ---")
print(df.shape)

# Check column names
print("\n--- Column names ---")
print(df.columns)

# Check data type of each column
print("\n--- Data types ---")
print(df.dtypes)

# Check null value in all records
print("\n--- Null value count ---")
print(df.isnull().sum())

# Check info of all records
print("\n--- DataFrame Info ---")
df.info()

# ======================================================================
# V. Data Cleaning
# ======================================================================

# --- A). Clean TransactionNo column ---
# Find records with null value in "TransactionNo"
print("\n--- Records with null TransactionNo ---")
print(df[df['TransactionNo'].isnull()])

# Drop all records in "TransactionNo" that have null value
df = df.dropna(subset=['TransactionNo'], inplace=False)

# Find records with null value after removed null
print("\n--- Null TransactionNo after drop ---")
print(df[df['TransactionNo'].isnull()])

# --- B). Clean CustomerNo column ---
# Find records with null value in "CustomerNo"
print("\n--- Records with null CustomerNo (top 5) ---")
print(df[df['CustomerNo'].isnull()].head())

# Drop all the records with "CustomerNo" have null value
df = df.dropna(subset=['CustomerNo'], inplace=False)

# Convert "CustomerNo" from float to int
df['CustomerNo'] = df['CustomerNo'].astype(int)

# Convert "CustomerNo" from integer to string
df['CustomerNo'] = df['CustomerNo'].astype(str)

# Find records with null value after removed null
print("\n--- Null CustomerNo after drop (top 5) ---")
print(df[df['CustomerNo'].isnull()].head())

# Check null value after removed
print("\n--- Null values count after CustomerNo cleaned ---")
print(df.isnull().sum())

# --- C). Clean Date column ---
# Find unique type of Date
# df['Date'].unique()

# Convert "Date" using the first format - m.d.y
date_format_1 = pd.to_datetime(df['Date'], format='%m.%d.%y', errors='coerce')

# Convert "Date" using the second format - m/d/Y
date_format_2 = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')

# Combine both results
stardardized_date = date_format_1.fillna(date_format_2)

# Create new column to replace existing "Date"
df['stardardized_date'] = stardardized_date

print("\n--- Head after standardized Date added ---")
print(df.head())

# --- D). Clean Quantity column ---
# Convert datatype from integer to string
df['Quantity'] = df['Quantity'].astype(str)

# Find records of "Quantity" that contain (-)
print("\n--- Records with negative Quantity (-) ---")
print(df[df['Quantity'].str.contains('-', case=False)].head())

# Remove (-) from number in "Quantity"
df['Quantity'] = df['Quantity'].str.replace('-', '', regex=False)

# Find records of "Quantity" that contain (-) after removed
print("\n--- Records with negative Quantity after cleaning ---")
print(df[df['Quantity'].str.contains('-', case=False)].head())

# Convert "Quantity" from string to float
df['Quantity'] = df['Quantity'].astype(float)

# --- E). Remove Duplicate records ---
# Find rows that are identical across all columns
duplicates = df[df.duplicated(keep=False)]

# Add a flag column to mark which ones are duplicates
df['is_duplicate'] = df.duplicated(keep=False)

# Show only the duplicate rows
duplicate_rows = df[df['is_duplicate'] == True]
print("\n--- Duplicate rows count ---", len(duplicate_rows))
print(duplicate_rows.head())

# Find duplicated records by "TransactionNo" and "ProductNo"
print("\n--- Check specific duplicates (TransactionNo: 581497, ProductNo: 21481) ---")
print(df[(df['TransactionNo'] == '581497') & (df['ProductNo'] == '21481')])

# Remove all identical rows (keep only the first occurrence)
df = df.drop_duplicates()

# Check duplicate rows in the entire dataset after removed
print("\n--- Specific duplicate after removal ---")
print(df[(df['TransactionNo'] == '581497') & (df['ProductNo'] == '21481')])

# Drop temporary duplicate flag
if 'is_duplicate' in df.columns:
    df = df.drop('is_duplicate', axis=1)

# Drop "Date" column
df = df.drop('Date', axis=1)

# Rename a "Standardized_date"
df = df.rename(columns={'stardardized_date': 'Date'})

# Reorder columns using reindex
df = df.reindex(columns=['CustomerNo', 'Date', 'TransactionNo', 'ProductNo', 'ProductName', 'Quantity', 'Price', 'Country'])

# Convert all column names to lowercase
df.columns = df.columns.str.lower()

# Check datatype after converted
print("\n--- Data types after column lowercase ---")
print(df.dtypes)

# Ensure primary key uniqueness to match PostgreSQL PRIMARY KEY (customerno, productno, date, transactionno)
df = df.drop_duplicates(subset=['customerno', 'productno', 'date', 'transactionno'])

# Check records after cleaned
print("\n--- Final cleaned DataFrame (top 5) ---")
print(df.head())
print(f"Total cleaned rows: {len(df)}")

# ======================================================================
# VI. Write the Cleaned Data into file (CSV or Excel)
# ======================================================================

# Save cleaned data as a csv file
print(f"\nSaving cleaned data as CSV: {CLEANED_CSV_PATH}")
df.to_csv(CLEANED_CSV_PATH, index=False)
print("Saved CSV successfully.")

# Save cleaned data as a excel file (first 50,000 rows to ensure fast writing)
print(f"Saving sample cleaned data as Excel: {CLEANED_XLSX_PATH}")
with pd.ExcelWriter(CLEANED_XLSX_PATH) as writer:
    df.head(50000).to_excel(writer, sheet_name="sales_transaction", index=False)
print("Saved Excel successfully.")

# ======================================================================
# VII. Write the Cleaned Data into Postgres database
# ======================================================================

# Credentials
host = "localhost"
port = 5432
dbname = "postgres"
username = "postgres"
password = "post@123!"

# URL-encode password
encoded_password = quote_plus(password)

# Build connection URL
db_url = f"postgresql+psycopg2://{username}:{encoded_password}@{host}:{port}/{dbname}?sslmode=disable"

# Create engine
engine = create_engine(db_url)

# Test connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT NOW();"))
        for row in result:
            print(f"\nConnection successful, current time: {row[0]}")
except Exception as e:
    print("\nConnection failed:", e)

# 4. Create Table in PostgreSQL using raw SQL
create_table_query = """
CREATE TABLE IF NOT EXISTS tbl_sales_transaction (
    customerno INT NOT NULL,
    date DATE NOT NULL,
    transactionno VARCHAR(50) NOT NULL,
    productno VARCHAR(50) NOT NULL,
    productname VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    country VARCHAR(100) NOT NULL,
    PRIMARY KEY (customerno, productno, date, transactionno)
);
"""

# Execute the create table statement
with engine.connect() as connection:
    connection.execute(text(create_table_query))  # wrap SQL in text()
    connection.commit()  # commit the transaction
    print("Table created successfully.")

# 5. Truncate Table before Load (optional clear table)
delete_table_query = """
    DELETE FROM tbl_sales_transaction;
"""
with engine.connect() as connection:
    connection.execute(text(delete_table_query))
    connection.commit()
    print("Truncate Table successfully.")

# 6. Load Cleaned Data to Table
print("Loading cleaned data into table 'tbl_sales_transaction'...")
df.to_sql('tbl_sales_transaction', engine, if_exists='append', index=False, chunksize=10000)
print("Data loaded successfully.")

# Verify count in database
with engine.connect() as connection:
    total_count = connection.execute(text("SELECT count(*) FROM tbl_sales_transaction;")).scalar()
    print(f"\n🎉 Total rows verified in 'tbl_sales_transaction': {total_count}")
