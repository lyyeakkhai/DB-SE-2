# DE-G2 Lab Setup

## 1. Database Credentials

| Parameter | Value |
|---|---|
| **Host** | `localhost` |
| **Port** | `5432` |
| **Database** | `postgres` |
| **Username** | `postgres` |
| **Password** | `post@123!` |

---

## 2. Docker Commands

Run these from the project root (`/Users/lyyeakkhai/workspace/CADT-DS-G2/DE-G2`):

- **Start database:**
  ```bash
  docker compose up -d
  ```

- **Check status:**
  ```bash
  docker compose ps
  ```

- **Stop database:**
  ```bash
  docker compose down
  ```

- **View database logs:**
  ```bash
  docker compose logs -f postgres
  ```

---

## 3. Python Virtual Environment

A Python virtual environment is set up in `.venv` with all lab dependencies installed (`pandas`, `numpy`, `sqlalchemy`, `psycopg2-binary`, `openpyxl`, `ipykernel`).

- **Activate the environment:**
  ```bash
  source .venv/bin/activate
  ```

- **Test connection script:**
  ```bash
  python test_connection.py
  ```

- **In VS Code / Jupyter:**
  When opening [`student_practice-etl_data_from_csv_into_db.ipynb`](file:///Users/lyyeakkhai/workspace/CADT-DS-G2/DE-G2/week-1/ETL-data-from-csv-file-to-db/notebooks/student_practice-etl_data_from_csv_into_db.ipynb), select the kernel:
  **`Python (DE-G2 Lab)`** or point to `.venv/bin/python`.

---

## 4. DBeaver Connection

1. Open **DBeaver** -> Click **New Database Connection** (plug icon with `+`).
2. Select **PostgreSQL**.
3. Fill in:
   - **Host:** `localhost`
   - **Port:** `5432`
   - **Database:** `postgres`
   - **Username:** `postgres`
   - **Password:** `post@123!`
4. Click **Test Connection** -> **Finish**.

---

## 5. VS Code "Database Client" Extension Connection

The **Database Client** extension (`cweijan.vscode-database-client2`) is installed.

### Option A: Open via Database Sidebar (Standard)
1. In the VS Code left Activity Bar, click the **Database** icon (barrel/cylinder).
2. Click **Create Connection** (or the **`+`** icon).
3. Select **PostgreSQL**.
4. Enter credentials:
   - **Host:** `localhost` (or `127.0.0.1`)
   - **Port:** `5432`
   - **Username:** `postgres`
   - **Password:** `post@123!`
   - **Database:** `postgres`
5. Click **Connect** (or Save).

### Option B: Connect directly via Docker in VS Code
1. In the VS Code left Activity Bar, click the **Service** icon (stacked layers icon from Database Client).
2. Expand **Docker**.
3. Find **`de-postgres`** (or your PostgreSQL container).
4. Right-click -> **Connect Database**.

