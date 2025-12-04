import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def init_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL not found in .env")
        print("Please add DATABASE_URL=postgresql://... to your .env file")
        return

    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        print("📖 Reading schema.sql...")
        with open("schema.sql", "r") as f:
            schema = f.read()

        print("🚀 Executing schema...")
        cur.execute(schema)
        conn.commit()
        
        cur.close()
        conn.close()
        print("✅ Database schema initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

if __name__ == "__main__":
    init_db()
