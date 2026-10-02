from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import sys

# credentials
host = "localhost"
port = 5432
dbname = "postgres"
username = "postgres"
password = "post@123!"

# URL-encode password
encoded_password = quote_plus(password)

# build connection URL (matching the lab notebook)
db_url = f"postgresql+psycopg2://{username}:{encoded_password}@{host}:{port}/{dbname}?sslmode=disable"

print("=" * 60)
print(f"🚀 Testing connection to PostgreSQL on {host}:{port}/{dbname}...")
print("=" * 60)

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # 1. Server info
        version = conn.execute(text("SELECT version();")).scalar()
        now = conn.execute(text("SELECT NOW();")).scalar()
        print("✅ Connection successful!")
        print(f"   Database Time : {now}")
        print(f"   Engine Version: {version.split(',')[0]}")

        # 2. Check or create table
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
        conn.execute(text(create_table_query))
        conn.commit()
        print("\n✅ Table 'tbl_sales_transaction' is verified in database.")

        # 3. Read/Write test
        conn.execute(text("""
            INSERT INTO tbl_sales_transaction 
            (customerno, date, transactionno, productno, productname, quantity, price, country)
            VALUES (99999, '2026-10-02', 'TEST001', 'PROD001', 'Test Product', 1, 9.99, 'Testland')
            ON CONFLICT (customerno, productno, date, transactionno) DO NOTHING;
        """))
        conn.commit()

        # Read back test row
        row = conn.execute(text("SELECT * FROM tbl_sales_transaction WHERE transactionno = 'TEST001';")).mappings().first()
        print(f"✅ Write & Read Test PASSED: Retrieved test transaction {row['transactionno']} - {row['productname']}")

        # Clean up test row
        conn.execute(text("DELETE FROM tbl_sales_transaction WHERE transactionno = 'TEST001';"))
        conn.commit()
        print("✅ Cleanup PASSED: Test row removed cleanly.")

        # Check total rows in table
        count = conn.execute(text("SELECT count(*) FROM tbl_sales_transaction;")).scalar()
        print(f"\n📊 Current rows in 'tbl_sales_transaction': {count}")

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! Your PostgreSQL database is 100% ready for the lab.")
    print("=" * 60)

except Exception as e:
    print("\n❌ Connection/Execution failed:", e)
    sys.exit(1)
