import sqlite3

DB_PATH = "../database/cities_weather.db"

def list_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:", [t[0] for t in tables])

def run_weather_query(cursor):
    cursor.execute("""
    SELECT
        weather_data.city,
        weather_data.current_temp,
        weather_data.humidity,
        weather_data.wind,
        weather_data.forecast,
        climate_data.metric,
        climate_data.value,
        climate_data.month
    FROM weather_data
    JOIN climate_data ON weather_data.city = climate_data.city
    LIMIT 20;
    """)

    col_names = [description[0] for description in cursor.description]
    print("\t".join(col_names))  

    rows = cursor.fetchall()
    for row in rows:
        print("\t".join(str(item) if item is not None else "" for item in row))

def run_query(cursor):
    print("\nEnter your SQL query (or type 'exit' to quit):")
    while True:
        query = input("SQL> ").strip()
        if query.lower() == 'exit':
            break
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                print(row)
        except Exception as e:
            print("Error:", e)

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    list_tables(cursor)
    run_weather_query(cursor)
    run_query(cursor)
    
    conn.close()

if __name__ == "__main__":
    main()