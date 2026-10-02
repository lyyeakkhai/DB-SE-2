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

print(f"Connecting to {host}:{port}/{dbname} as {username}...")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.scalar()
        print("✅ Connection successful!")
        print(f"PostgreSQL version: {version}")
        
        now = conn.execute(text("SELECT NOW();")).scalar()
        print(f"Current database time: {now}")
except Exception as e:
    print("❌ Connection failed:", e)
    sys.exit(1)
