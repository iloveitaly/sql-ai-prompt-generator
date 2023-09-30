import click
import psycopg2

from util import system_prompt

def describe_table_schema(conn, table_name):
    """Outputs the table schema using SQL."""
    query = f"""
    SELECT column_name, data_type, character_maximum_length
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = '{table_name}';
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        schema = cursor.fetchall()

    for column in schema:
        col_name, data_type, max_length = column
        if max_length:
            print(f"{col_name} {data_type}({max_length})")
        else:
            print(f"{col_name} {data_type}")

@click.command()
@click.argument('db_url')
@click.argument('table_name')
def describe_and_sample(db_url, table_name):
    print(
        f"""
{system_prompt()}
- You are working with a PostgreSQL database

# Table Schema for `{table_name}`
```sql
        """
          )
    with psycopg2.connect(db_url) as conn:
        describe_table_schema(conn, table_name)

        with conn.cursor() as cursor:
            # Sample 3 rows
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT 3")
            sample_rows = cursor.fetchall()

            # Get column names
            cursor.execute(f"SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = '{table_name}';")
            col_names = [col[0] for col in cursor.fetchall()]

    print(
f"""
```

3 sample rows from the {table_name} table:

```sql
"""
          )

    for row in sample_rows:
        values = ', '.join(map(repr, row))  # Using repr() to handle data types like strings
        print(f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({values});")

    print("```")

if __name__ == '__main__':
    describe_and_sample()