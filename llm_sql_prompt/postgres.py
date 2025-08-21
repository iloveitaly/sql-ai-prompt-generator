import psycopg
from psycopg import sql

from llm_sql_prompt.util import system_prompt


def describe_table_schema(conn, table_name):
    """Outputs the table schema using SQL, including column comments and FK info if available."""
    query = """
    SELECT column_name, data_type, character_maximum_length
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE table_name = %s;
    """
    with conn.cursor() as cursor:
        cursor.execute(query, (table_name,))
        schema = cursor.fetchall()

    # Retrieve foreign key mapping: { column_name: (foreign_table, foreign_column) }
    foreign_keys = get_foreign_keys(conn, table_name)

    for column in schema:
        col_name, data_type, max_length = column

        if max_length:
            line = f"{col_name} {data_type}({max_length})"
        else:
            line = f"{col_name} {data_type}"
        
        # Append FK info if exists
        if col_name in foreign_keys:
            fk_table, fk_column = foreign_keys[col_name]
            line += f" REFERENCES {fk_table}({fk_column})"
        
        # Get column comment if it exists
        col_comment = get_column_comments(conn, table_name, col_name)
        if col_comment:
            line += f" -- {col_comment}"
            
        print(line)


def get_table_names(db_url) -> list[str]:
    """Get the table names from the database."""
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
            table_list = [row[0] for row in cursor.fetchall()]
    return table_list


def print_table_name_options(db_url):
    table_list = get_table_names(db_url)
    formatted_table_list = "\n- ".join(table_list)

    # Print the table names
    print(
        f"""
No table name provided. Please provide a table name from the list below, or use --all:

- {formatted_table_list}
        """
    )


def get_installed_extensions(conn):
    """Return a list of installed extensions with version and comment (if available)."""
    query = """
    SELECT e.extname, e.extversion, COALESCE(x.comment, '') AS comment
    FROM pg_extension e
    LEFT JOIN pg_available_extensions x ON e.extname = x.name
    ORDER BY e.extname;
    """
    with conn.cursor() as cursor:
        cursor.execute(query)
        return cursor.fetchall()  # list of (name, version, comment)


def describe_database_and_table(db_url: str, table_names: list[str], all_tables: bool, include_data: bool = True):
    """Main function to describe database tables, including installed extensions."""

    if not table_names and not all_tables:
        print_table_name_options(db_url)
        exit(1)

    if all_tables:
        table_names = get_table_names(db_url)

    with psycopg.connect(db_url) as conn:
        # Fetch installed extensions once per run
        extensions = get_installed_extensions(conn)
        # Fetch server version
        with conn.cursor() as cursor:
            server_version = "unknown"
            try:
                cursor.execute("SHOW server_version;")
                row = cursor.fetchone()
                if row and row[0]:
                    server_version = str(row[0])
            except Exception:
                try:
                    cursor.execute("SELECT version();")
                    row = cursor.fetchone()
                    if row and row[0]:
                        # typical format: 'PostgreSQL 16.2 (Homebrew) on ...'
                        parts = str(row[0]).split()
                        if len(parts) >= 2:
                            server_version = parts[1]
                        else:
                            server_version = str(row[0])
                except Exception:
                    pass
        if extensions:
            extensions_formatted = "\n".join(
                f"  - {name} ({version}){f': {comment}' if comment else ''}" for name, version, comment in extensions
            )
            extensions_block = f"- Installed PostgreSQL extensions in this database:\n{extensions_formatted}"
        else:
            extensions_block = "- No PostgreSQL extensions installed in this database"

        print(
            f"""
{system_prompt()}
- You are working with a PostgreSQL database (server version: {server_version})
{extensions_block}
            """
        )

        for table_name in table_names:
            table_comment = get_table_comment(conn, table_name)
            print(
                f"""
# Table Schema for `{table_name}`
{table_comment}
```sql"""
            )

            describe_table_schema(conn, table_name)
            print("```")  # Close table schema SQL block

            if include_data:
                with conn.cursor() as cursor:
                    # Retrieve sample rows (identifier safely inserted)
                    sample_query = sql.SQL("SELECT * FROM {} ORDER BY RANDOM() LIMIT 3").format(
                        sql.Identifier(table_name)
                    )
                    cursor.execute(sample_query)
                    sample_rows = cursor.fetchall()

                    cursor.execute(
                        "SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = %s;",
                        (table_name,)
                    )
                    col_names = [col[0] for col in cursor.fetchall()]

                    if sample_rows:
                        print(
                            f"""
```

3 sample rows from the `{table_name}` table:

```sql
                            """
                        )
                        for row in sample_rows:
                            values = ", ".join(map(repr, row))
                            print(
                                f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({values});"
                            )
                        print("```")

def get_table_comment(conn, table_name):
    query = """
    SELECT pd.description
    FROM pg_description pd
    JOIN pg_class pc ON pd.objoid = pc.oid
    WHERE pc.relname = %s AND pd.objsubid = 0
    """
    with conn.cursor() as cursor:
        cursor.execute(query, (table_name,))
        result = cursor.fetchone()

        if result:
            return result[0]
        
        return ""

def get_column_comments(conn, table_name, column_name: str | None = None):
    """
    When column_name is provided, returns the comment for that column.
    Otherwise, returns a dictionary mapping column names to comments.
    """
    query = """
    SELECT a.attname as column_name, pd.description
    FROM pg_description pd
    JOIN pg_class pc ON pd.objoid = pc.oid
    JOIN pg_attribute a ON pd.objsubid = a.attnum AND a.attrelid = pc.oid
    WHERE pc.relname = %s AND pd.objsubid > 0
    """
    params = [table_name]
    if column_name:
        query += " AND a.attname = %s"
        params.append(column_name)
    with conn.cursor() as cursor:
        cursor.execute(query, tuple(params))
        if column_name:
            result = cursor.fetchone()
            return result[1] if result and result[1] else ""
        else:
            return {row[0]: row[1] for row in cursor.fetchall()}

def get_foreign_keys(conn, table_name):
    """
    Returns a dictionary mapping column names to a tuple (foreign_table, foreign_column)
    for foreign key constraints of the given table.
    """
    query = """
    SELECT
      kcu.column_name,
      ccu.table_name AS foreign_table_name,
      ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = %s;
    """
    with conn.cursor() as cursor:
        cursor.execute(query, (table_name,))
        results = cursor.fetchall()
    return {row[0]: (row[1], row[2]) for row in results}