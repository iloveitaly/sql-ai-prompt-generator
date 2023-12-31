import sqlite3
import click
import subprocess

from util import system_prompt


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


@click.command()
@click.argument("db_filename", type=click.Path(exists=True))
@click.argument("table_name")
def describe_and_sample(db_filename, table_name):
    print(
        f"""
{system_prompt()}
- You are working with a SQLite3 database

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
        print(f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({values});")

    print("```")

    conn.close()


if __name__ == "__main__":
    describe_and_sample()
