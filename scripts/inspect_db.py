
import psycopg2
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}

def get_table_schema(cur, table_name):
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
    """)
    columns = cur.fetchall()
    
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    
    return {"columns": columns, "count": count}

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        tables = [
            'houses_immat', 'cmr_admin3', 'admin_regions', 'admin_departments', 
            'mercuriale_prix', 'airbnb_listings', 'tax_summary_regions', 
            'tax_summary_departments', 'tax_summary_communes'
        ]
        
        results = {}
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        available_tables = [t[0] for t in cur.fetchall()]
        
        for t in tables:
            if t in available_tables:
                results[t] = get_table_schema(cur, t)
            else:
                results[t] = "Table not found"
        
        print(json.dumps(results, indent=2))
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
