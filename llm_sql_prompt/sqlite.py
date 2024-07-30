import sqlite3
import subprocess

from llm_sql_prompt.util import system_prompt


def describe_table_schema(db_filename, table_name):
    """Outputs the table schema using the sqlite3 CLI tool."""

    # TODO should use which to detect if this exists

    # Execute the sqlite3 CLI command
    result = subprocess.run(
        ["sqlite3", db_filename, f".schema {table_name}"],
        capture_output=True,
        text=True,
    )

    # Print the output
    print(result.stdout)


def list_sqllite_tables(db_filename):
    """Outputs the table schema using the sqlite3 CLI tool."""

    result = subprocess.run(
        ["sqlite3", db_filename, ".tables"],
        capture_output=True,
        text=True,
    )

    # Split the output on whitespace and join with newlines
    formatted_output = "\n".join(result.stdout.split())

    return formatted_output


def describe_database_and_table(db_filename, table_names, all_tables):
    if not table_names and not all_tables:
        print(
            f"""No table name provided. Please provide a table name from the list below:

{list_sqllite_tables(db_filename)}
            """
        )
        exit(1)

    if all_tables:
        table_names = list_sqllite_tables(db_filename).split()

    print(
        f"""
{system_prompt()}
- You are working with a SQLite 3 database
- SQLite does not support the CREATE OR REPLACE syntax
- Quote reserved words like 'to'

        """
    )

    for table_name in table_names:
        print(
            """
# Table Schema for `{table_name}`
```sql
"""
        )

        describe_table_schema(db_filename, table_name)

        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()

        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        # Sample 3 rows
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT 3")
        sample_rows = cursor.fetchall()

        print(
            f"""
    ```

## Sample rows from `{table_name}`:

```sql
    """
        )

        col_names = [col[1] for col in columns]
        for row in sample_rows:
            values = ", ".join(
                map(repr, row)
            )  # Using repr() to handle data types like strings
            print(
                f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({values});"
            )

        print("```")

        conn.close()
