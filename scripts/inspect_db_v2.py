
import psycopg2
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "immatriculation",
    "user": "immat_user",
    "password": "immat_dev_password",
}

def get_table_schema(cur, schema, table_name):
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table_name}'
        ORDER BY ordinal_position;
    """)
    columns = cur.fetchall()
    
    cur.execute(f"SELECT COUNT(*) FROM {schema}.{table_name}")
    count = cur.fetchone()[0]
    
    return {"columns": columns, "count": count}

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        tables = [
            ('public', 'houses_immat'), 
            ('public', 'cmr_admin3'), 
            ('immatriculation', 'admin_regions'), 
            ('immatriculation', 'admin_departments'), 
            ('immatriculation', 'mercuriale_prix'), 
            ('immatriculation', 'airbnb_listings')
        ]
        
        results = {}
        for schema, name in tables:
            try:
                results[f"{schema}.{name}"] = get_table_schema(cur, schema, name)
            except Exception as e:
                results[f"{schema}.{name}"] = f"Error: {e}"
        
        print(json.dumps(results, indent=2))
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
