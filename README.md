# DB-SE-2

Data Engineering Lab & Coursework - CADT DS G2

## Structure

- **`week-1/`**
  - **`ETL-data-from-csv-file-to-db/`**: Docker Compose setup for PostgreSQL, dataset, ETL notebook, and SQL scripts.
  - **`Tools-Installation/`**: Setup guide for Data Engineering tools.
  - `Theory - Introduction to Data Engineering.pdf`

## Quick Start (PostgreSQL Docker)

```bash
# Start PostgreSQL container
cd week-1/ETL-data-from-csv-file-to-db
docker compose up -d

# Verify connection with Python
python test_connection.py
```
