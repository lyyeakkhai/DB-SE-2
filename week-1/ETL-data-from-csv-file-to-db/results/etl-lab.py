#!/usr/bin/env python3
"""
ETL Pipeline: Clean CSV Sales Data and Load into PostgreSQL Database
"""

import os
import sys
import warnings
from urllib.parse import quote_plus
import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError

# Suppress minor library warnings
warnings.filterwarnings('ignore')

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # week-1/ETL-data-from-csv-file-to-db
DEFAULT_DATASET_PATH = os.path.join(BASE_DIR, 'dataset', 'sales_transaction_dataset.csv')
CLEANED_CSV_PATH = os.path.join(SCRIPT_DIR, 'sales_transaction_dataset_cleaned.csv')
CLEANED_XLSX_PATH = os.path.join(SCRIPT_DIR, 'sales_transaction_dataset_cleaned.xlsx')

# Database Credentials
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "username": "postgres",
    "password": "post@123!"
}


# ======================================================================
# 1. EXTRACT: Read Dataset with Exception Handling
# ======================================================================
def read_dataset(file_path: str) -> pd.DataFrame:
    """
    Read dataset from a CSV file with comprehensive exception handling.
    """
    print(f"[*] Reading dataset from: {file_path}")
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset file not found at: {file_path}")

        df = pd.read_csv(file_path)

        if df.empty:
            raise EmptyDataError(f"Dataset file is empty: {file_path}")

        print(f"[+] Dataset successfully loaded: {df.shape[0]:,} rows, {df.shape[1]} columns.")
        return df

    except FileNotFoundError as err:
        print(f"[!] File Error: {err}")
        sys.exit(1)
    except EmptyDataError as err:
        print(f"[!] Data Error: {err}")
        sys.exit(1)
    except ParserError as err:
        print(f"[!] CSV Parsing Error: File format is corrupted. {err}")
        sys.exit(1)
    except PermissionError as err:
        print(f"[!] Permission Error: Access denied for file {file_path}. {err}")
        sys.exit(1)
    except Exception as err:
        print(f"[!] Unexpected error while reading dataset: {err}")
        sys.exit(1)


# ======================================================================
# 2. TRANSFORM: Data Cleaning and Standardization
# ======================================================================
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and transform the sales transaction dataset:
    - Handle missing values in TransactionNo and CustomerNo
    - Standardize mixed date formats
    - Clean negative quantity values
    - Remove duplicate records and ensure primary key integrity
    - Standardize column names to lowercase
    """
    print("\n[*] Starting data transformation...")
    initial_rows = len(df)

    # A. Clean TransactionNo & CustomerNo (Drop missing values)
    df = df.dropna(subset=['TransactionNo', 'CustomerNo'], inplace=False)

    # Convert CustomerNo from float -> int -> str
    df['CustomerNo'] = df['CustomerNo'].astype(int).astype(str)

    # B. Standardize Date formats (%m.%d.%y and %m/%d/%Y)
    date_format_1 = pd.to_datetime(df['Date'], format='%m.%d.%y', errors='coerce')
    date_format_2 = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
    df['Date'] = date_format_1.fillna(date_format_2)

    # C. Clean Quantity (remove '-' sign and convert to float)
    df['Quantity'] = (
        df['Quantity']
        .astype(str)
        .str.replace('-', '', regex=False)
        .astype(float)
    )

    # D. Reorder and normalize column names
    df = df.reindex(columns=[
        'CustomerNo', 'Date', 'TransactionNo', 'ProductNo',
        'ProductName', 'Quantity', 'Price', 'Country'
    ])
    df.columns = df.columns.str.lower()

    # E. Remove full duplicates
    df = df.drop_duplicates()

    # F. Ensure uniqueness on composite primary key (customerno, productno, date, transactionno)
    df = df.drop_duplicates(subset=['customerno', 'productno', 'date', 'transactionno'])

    final_rows = len(df)
    dropped_rows = initial_rows - final_rows
    print(f"[+] Transformation complete: {final_rows:,} valid records retained ({dropped_rows:,} removed).")
    return df


# ======================================================================
# 3. SAVE: Export Cleaned Files with Exception Handling
# ======================================================================
def save_cleaned_data(df: pd.DataFrame, csv_path: str, excel_path: str = None) -> None:
    """
    Save cleaned data to CSV and Excel with error handling.
    """
    try:
        print(f"\n[*] Saving cleaned data to CSV: {csv_path}")
        df.to_csv(csv_path, index=False)
        print("[+] CSV export successful.")

        if excel_path:
            print(f"[*] Saving sample cleaned data to Excel (50,000 rows): {excel_path}")
            with pd.ExcelWriter(excel_path) as writer:
                df.head(50000).to_excel(writer, sheet_name="sales_transaction", index=False)
            print("[+] Excel export successful.")

    except PermissionError as err:
        print(f"[!] Write Permission Error: Cannot write output files. {err}")
    except OSError as err:
        print(f"[!] OS/Disk Error while saving files: {err}")
    except Exception as err:
        print(f"[!] Warning: Failed to save output files: {err}")


# ======================================================================
# 4. DATABASE: Connection with Exception Handling
# ======================================================================
def get_db_connection(host: str, port: int, dbname: str, username: str, password: str):
    """
    Establish database engine and test connectivity with comprehensive exception handling.
    """
    print(f"\n[*] Connecting to PostgreSQL at {host}:{port}/{dbname} (User: {username})...")
    encoded_password = quote_plus(password)
    db_url = f"postgresql+psycopg2://{username}:{encoded_password}@{host}:{port}/{dbname}?sslmode=disable"

    try:
        engine = create_engine(db_url, pool_pre_ping=True)

        # Test active connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
            now = conn.execute(text("SELECT NOW();")).scalar()
            print("[+] Database connection successful!")
            print(f"    Server Time : {now}")
            print(f"    Version     : {result.split(',')[0]}")

        return engine

    except OperationalError as err:
        print(f"[!] Database Connection Error (OperationalError):")
        print(f"    Could not connect to {host}:{port}. Is the Docker container running?")
        print(f"    Details: {err.orig if hasattr(err, 'orig') else err}")
        sys.exit(1)

    except ProgrammingError as err:
        print(f"[!] Database Authentication / Configuration Error (ProgrammingError):")
        print(f"    Check your username, password, or database name.")
        print(f"    Details: {err.orig if hasattr(err, 'orig') else err}")
        sys.exit(1)

    except SQLAlchemyError as err:
        print(f"[!] General SQLAlchemy Error: {err}")
        sys.exit(1)

    except Exception as err:
        print(f"[!] Unexpected error during database connection: {err}")
        sys.exit(1)


# ======================================================================
# 5. LOAD: Table Creation and Data Ingestion
# ======================================================================
def create_table_if_not_exists(engine) -> None:
    """
    Create the target table in PostgreSQL if it doesn't already exist.
    """
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
    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_query))
            conn.commit()
            print("[+] Table 'tbl_sales_transaction' verified/created successfully.")
    except SQLAlchemyError as err:
        print(f"[!] Failed to create table: {err}")
        raise


def load_data_to_db(df: pd.DataFrame, engine, table_name: str = 'tbl_sales_transaction', truncate: bool = True) -> None:
    """
    Load cleaned DataFrame into PostgreSQL in chunks with exception handling.
    """
    try:
        with engine.connect() as conn:
            if truncate:
                print(f"[*] Truncating existing records in '{table_name}'...")
                conn.execute(text(f"DELETE FROM {table_name};"))
                conn.commit()
                print("[+] Table truncated.")

        print(f"[*] Ingesting {len(df):,} records into '{table_name}' (chunksize=10,000)...")
        df.to_sql(table_name, engine, if_exists='append', index=False, chunksize=10000)
        print("[+] Ingestion finished successfully.")

        # Verify row count
        with engine.connect() as conn:
            row_count = conn.execute(text(f"SELECT count(*) FROM {table_name};")).scalar()
            print(f"[🎉] Verification: {row_count:,} rows currently stored in '{table_name}'.")

    except SQLAlchemyError as err:
        print(f"[!] Database Error during data load: {err}")
        sys.exit(1)
    except Exception as err:
        print(f"[!] Unexpected error during data ingestion: {err}")
        sys.exit(1)


# ======================================================================
# MAIN PIPELINE
# ======================================================================
def main():
    print("=" * 65)
    print("🚀 ETL PIPELINE: CSV TO POSTGRESQL")
    print("=" * 65)

    # 1. Read Dataset (with try-catch)
    raw_df = read_dataset(DEFAULT_DATASET_PATH)

    # 2. Transform & Clean Data
    cleaned_df = transform_data(raw_df)

    # 3. Save Cleaned Files (with try-catch)
    save_cleaned_data(cleaned_df, CLEANED_CSV_PATH, CLEANED_XLSX_PATH)

    # 4. Connect to Database (with try-catch)
    engine = get_db_connection(**DB_CONFIG)

    # 5. Create Table & Load Data (with try-catch)
    create_table_if_not_exists(engine)
    load_data_to_db(cleaned_df, engine, table_name='tbl_sales_transaction', truncate=True)

    print("\n" + "=" * 65)
    print("✅ ETL PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == '__main__':
    main()
