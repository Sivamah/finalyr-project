import sqlite3

def print_schemas():
    conn = sqlite3.connect('rapidoproject.db')
    cursor = conn.cursor()
    tables = ['trips', 'assignments', 'assignment_history']
    for table in tables:
        print(f"--- {table} ---")
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        res = cursor.fetchone()
        if res:
            print(res[0])
        else:
            print(f"Table {table} not found.")

if __name__ == "__main__":
    print_schemas()
