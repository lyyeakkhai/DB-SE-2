#!/usr/bin/env python3
"""
ETL Pipeline: Clean Sales Transaction CSV and Load into PostgreSQL
"""

import os
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# ==============================================================================
# CONFIGURATION & PATHS
# ==============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

DATASET_PATH = os.path.join(BASE_DIR, "dataset", "sales_transaction_dataset.csv")
CLEANED_CSV_PATH = os.path.join(CURRENT_DIR, "sales_transaction_dataset_cleaned.csv")
CLEANED_XLSX_PATH = os.path.join(CURRENT_DIR, "sales_transaction_dataset_cleaned.xlsx")

# Fallback path if run from results directory
if not os.path.exists(DATASET_PATH):
    DATASET_PATH = "../dataset/sales_transaction_dataset.csv"

# Database Configuration
DB_USER = "postgres"
DB_PASS = "post@123!"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"


# ==============================================================================
# 1. EXTRACT: Read Dataset with Exception Handling
# ==============================================================================
def read_dataset(file_path: str) -> pd.DataFrame:
    """
    Load dataset from a CSV file.
    Catches FileNotFoundError and corrupted data exceptions.
    """
    print(f"Reading dataset: {file_path}")
    try:
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df):,} rows successfully.")
        return df
    except FileNotFoundError:
        print(f"Error: Dataset file not found at '{file_path}'. Please check the path.")
        raise
    except pd.errors.EmptyDataError:
        print(f"Error: Dataset file is empty.")
        raise
    except Exception as e:
        print(f"Error reading dataset: {e}")
        raise


# ==============================================================================
# 2. TRANSFORM: Cleaning Functions
# ==============================================================================
def drop_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with missing TransactionNo or CustomerNo and format CustomerNo."""
    df = df.dropna(subset=["TransactionNo", "CustomerNo"])
    df["CustomerNo"] = df["CustomerNo"].astype(int).astype(str)
    return df


def standardize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and standardize mixed date formats into uniform datetime."""
    fmt1 = pd.to_datetime(df["Date"], format="%m.%d.%y", errors="coerce")
    fmt2 = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    df["Date"] = fmt1.fillna(fmt2)
    return df


def clean_quantities(df: pd.DataFrame) -> pd.DataFrame:
    """Strip negative signs from Quantity and cast to float."""
    df["Quantity"] = (
        df["Quantity"]
        .astype(str)
        .str.replace("-", "", regex=False)
        .astype(float)
    )
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop exact duplicate rows and ensure primary key columns are unique."""
    df = df.drop_duplicates()
    df = df.drop_duplicates(subset=["customerno", "productno", "date", "transactionno"])
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Orchestrate all data cleaning and formatting steps.
    """
    print("Transforming and cleaning data...")

    df = drop_missing_values(df)
    df = standardize_dates(df)
    df = clean_quantities(df)

    # Reorder and format column names to lowercase
    columns = [
        "CustomerNo", "Date", "TransactionNo", "ProductNo",
        "ProductName", "Quantity", "Price", "Country"
    ]
    df = df[columns]
    df.columns = df.columns.str.lower()

    df = remove_duplicates(df)

    print(f"Data cleaned: {len(df):,} valid rows ready.")
    return df


# ==============================================================================
# 3. EXPORT: Save Cleaned Files
# ==============================================================================
def export_cleaned_data(df: pd.DataFrame, csv_path: str, excel_path: str = None) -> None:
    """
    Save cleaned data to CSV and optional Excel file.
    """
    try:
        print(f"Exporting cleaned data to CSV: {csv_path}")
        df.to_csv(csv_path, index=False)
        print("CSV export completed.")

        if excel_path:
            print(f"Exporting sample cleaned data to Excel (50,000 rows): {excel_path}")
            with pd.ExcelWriter(excel_path) as writer:
                df.head(50000).to_excel(writer, sheet_name="sales_transaction", index=False)
            print("Excel export completed.")

    except Exception as e:
        print(f"Warning: Failed to export files: {e}")


# ==============================================================================
# 4. DATABASE: Connection with Exception Handling
# ==============================================================================
def get_db_connection(user: str, password: str, host: str, port: int, dbname: str):
    """
    Create a SQLAlchemy engine and verify database connection.
    Catches unreachable hosts, stopped Docker containers, or invalid credentials.
    """
    print(f"Connecting to database: {user}@{host}:{port}/{dbname}")
    try:
        encoded_password = quote_plus(password)
        db_url = f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{dbname}?sslmode=disable"
        engine = create_engine(db_url, pool_pre_ping=True)

        # Test active connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))

        print("Database connection established successfully.")
        return engine

    except SQLAlchemyError as e:
        print(f"Database connection error: Could not reach {host}:{port}/{dbname}.")
        print(f"Details: {e}")
        raise
    except Exception as e:
        print(f"Unexpected connection error: {e}")
        raise


# ==============================================================================
# 5. LOAD: Table Creation and Ingestion
# ==============================================================================
def create_table_if_not_exists(engine) -> None:
    """Create target table in PostgreSQL if it does not already exist."""
    create_table_sql = """
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
            conn.execute(text(create_table_sql))
            conn.commit()
        print("Table 'tbl_sales_transaction' is ready.")
    except SQLAlchemyError as e:
        print(f"Failed to create table: {e}")
        raise


def load_to_database(df: pd.DataFrame, engine, table_name: str = "tbl_sales_transaction") -> None:
    """
    Clear existing table data and load cleaned DataFrame in batches.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {table_name};"))
            conn.commit()
            print(f"Cleared existing data from '{table_name}'.")

        print(f"Inserting {len(df):,} rows into '{table_name}'...")
        df.to_sql(table_name, engine, if_exists="append", index=False, chunksize=10000)

        # Verify final row count
        with engine.connect() as conn:
            total_rows = conn.execute(text(f"SELECT count(*) FROM {table_name};")).scalar()

        print(f"Loaded successfully: {total_rows:,} rows in '{table_name}'.")

    except SQLAlchemyError as e:
        print(f"Database error while loading data: {e}")
        raise


# ==============================================================================
# MAIN PIPELINE
# ==============================================================================
def main():
    # 1. Read dataset
    df = read_dataset(DATASET_PATH)

    # 2. Transform and clean
    cleaned_df = transform_data(df)

    # 3. Export to CSV & Excel
    export_cleaned_data(cleaned_df, CLEANED_CSV_PATH, CLEANED_XLSX_PATH)

    # 4. Connect to PostgreSQL
    engine = get_db_connection(DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME)

    # 5. Create table & load data
    create_table_if_not_exists(engine)
    load_to_database(cleaned_df, engine)

    print("ETL pipeline finished successfully.")


if __name__ == "__main__":
    main()
