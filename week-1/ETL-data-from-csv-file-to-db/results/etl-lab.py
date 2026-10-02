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
# CONFIGURATION
# ==============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)

INPUT_CSV_PATH = os.path.join(BASE_DIR, "dataset", "sales_transaction_dataset.csv")
OUTPUT_CSV_PATH = os.path.join(CURRENT_DIR, "sales_transaction_dataset_cleaned.csv")

DB_USER = "postgres"
DB_PASS = "post@123!"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "postgres"


# ==============================================================================
# 1. EXTRACT
# ==============================================================================
def load_raw_data(file_path: str) -> pd.DataFrame:
    """
    Read the raw dataset from a CSV file.
    Catches file missing and corrupted data exceptions.
    """
    print(f"Reading dataset: {file_path}")
    try:
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df):,} rows successfully.")
        return df
    except FileNotFoundError:
        print(f"Error: Dataset not found at '{file_path}'. Please check the path.")
        raise
    except pd.errors.EmptyDataError:
        print(f"Error: The dataset file is empty.")
        raise
    except Exception as e:
        print(f"Error reading dataset: {e}")
        raise


# ==============================================================================
# 2. TRANSFORM (Individual Cleaning Functions)
# ==============================================================================
def drop_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with missing TransactionNo or CustomerNo, format CustomerNo."""
    df = df.dropna(subset=["TransactionNo", "CustomerNo"])
    df["CustomerNo"] = df["CustomerNo"].astype(int).astype(str)
    return df


def standardize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse and unify mixed date formats (%m.%d.%y and %m/%d/%Y)."""
    fmt1 = pd.to_datetime(df["Date"], format="%m.%d.%y", errors="coerce")
    fmt2 = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")
    df["Date"] = fmt1.fillna(fmt2)
    return df


def clean_quantities(df: pd.DataFrame) -> pd.DataFrame:
    """Strip minus signs from Quantity and cast to float."""
    df["Quantity"] = (
        df["Quantity"]
        .astype(str)
        .str.replace("-", "", regex=False)
        .astype(float)
    )
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows and ensure primary key columns are unique."""
    df = df.drop_duplicates()
    df = df.drop_duplicates(subset=["customerno", "productno", "date", "transactionno"])
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Orchestrate all data cleaning steps and column formatting.
    """
    print("Transforming and cleaning data...")

    df = drop_missing_values(df)
    df = standardize_dates(df)
    df = clean_quantities(df)

    # Reorder and convert column names to lowercase
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
# 3. EXPORT
# ==============================================================================
def export_cleaned_data(df: pd.DataFrame, output_path: str) -> None:
    """
    Save the cleaned DataFrame to a CSV file.
    """
    print(f"Exporting cleaned data to: {output_path}")
    try:
        df.to_csv(output_path, index=False)
        print("CSV export completed.")
    except Exception as e:
        print(f"Warning: Failed to export CSV: {e}")


# ==============================================================================
# 4. DATABASE CONNECTION
# ==============================================================================
def get_database_engine(user: str, password: str, host: str, port: int, dbname: str):
    """
    Create a SQLAlchemy engine and verify the connection.
    Handles connection errors (Docker stopped, bad port, wrong credentials).
    """
    print(f"Connecting to database: {user}@{host}:{port}/{dbname}")
    try:
        encoded_password = quote_plus(password)
        db_url = f"postgresql+psycopg2://{user}:{encoded_password}@{host}:{port}/{dbname}?sslmode=disable"
        engine = create_engine(db_url, pool_pre_ping=True)

        # Test connection
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
# 5. LOAD
# ==============================================================================
def create_table_if_not_exists(engine) -> None:
    """Create the target table in PostgreSQL if it does not already exist."""
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
    Truncate existing table and load cleaned DataFrame in batches.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM {table_name};"))
            conn.commit()
            print(f"Cleared existing data from '{table_name}'.")

        print(f"Inserting {len(df):,} rows into '{table_name}'...")
        df.to_sql(table_name, engine, if_exists="append", index=False, chunksize=10000)

        # Verify inserted count
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
    # 1. Extract
    raw_df = load_raw_data(INPUT_CSV_PATH)

    # 2. Transform
    clean_df = transform_data(raw_df)

    # 3. Export
    export_cleaned_data(clean_df, OUTPUT_CSV_PATH)

    # 4. Connect
    engine = get_database_engine(DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME)

    # 5. Load
    create_table_if_not_exists(engine)
    load_to_database(clean_df, engine)

    print("ETL pipeline finished successfully.")


if __name__ == "__main__":
    main()
