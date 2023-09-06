import sqlite3
import sys

def describe_table(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return columns

def sample_data(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
    return cursor.fetchall()

def generate_insert_statements(table_name, columns, rows):
    inserts = []
    for row in rows:
        values = ', '.join(['?'] * len(row))
        inserts.append(f"INSERT INTO {table_name}({', '.join(columns)}) VALUES ({values}); -- {row}")
    return inserts

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: script.py <database_filename> <table_name>")
        sys.exit(1)

    db_filename = sys.argv[1]
    table_name = sys.argv[2]

    conn = sqlite3.connect(db_filename)

    columns = describe_table(conn, table_name)
    rows = sample_data(conn, table_name)

    for statement in generate_insert_statements(table_name, columns, rows):
        print(statement)

    conn.close()
