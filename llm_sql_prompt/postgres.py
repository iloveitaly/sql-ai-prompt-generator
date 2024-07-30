import textwrap
import psycopg2

from llm_sql_prompt.util import system_prompt


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


def get_table_names(db_url) -> list[str]:
    """Get the table names from the database."""
    conn = psycopg2.connect(db_url)

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """
        )

        table_list = cursor.fetchall()
        table_list = [table[0] for table in table_list]

    return table_list


def print_table_name_options(db_url):
    table_list = get_table_names(db_url)
    formatted_table_list = "\n- ".join(table_list)

    # Print the table names
    print(
        f"""
No table name provided. Please provide a table name from the list below:

- {formatted_table_list}
        """
    )


def describe_database_and_table(db_url: str, table_names: list[str], all_tables: bool):
    if not table_names and not all_tables:
        print_table_name_options(db_url)
        exit(1)

    print(
        f"""
{system_prompt()}
- You are working with a PostgreSQL database

        """
    )

    if all_tables:
        table_names = get_table_names(db_url)

    with psycopg2.connect(db_url) as conn:
        for table_name in table_names:
            print(
                f"""
# Table Schema for `{table_name}`
```sql
"""
            )

            describe_table_schema(conn, table_name)

            with conn.cursor() as cursor:
                # Sample 3 rows
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT 3")
                sample_rows = cursor.fetchall()

                # Get column names
                cursor.execute(
                    f"SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = '{table_name}';"
                )
                col_names = [col[0] for col in cursor.fetchall()]

                print(
                    f"""
```

3 sample rows from the `{table_name}` table:

```sql
            """
                )

                for row in sample_rows:
                    values = ", ".join(
                        map(repr, row)
                    )  # Usi`n`g repr() to handle data types like strings
                    print(
                        f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({values});"
                    )

                print("```")
