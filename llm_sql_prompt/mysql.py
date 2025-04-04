from urllib.parse import urlparse

from llm_sql_prompt.util import system_prompt

# Try to import MySQL connector, but handle when it's missing
MYSQL_AVAILABLE = False
try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    # MySQL connector not installed
    pass

def check_mysql_available():
    """Check if MySQL connector is available and raise a helpful error if not."""
    if not MYSQL_AVAILABLE:
        raise ImportError(
            "MySQL connector not available. Please install the required package:\n"
            "pip install mysql-connector-python"
        )

def parse_mysql_url(db_url):
    """Parse a mysql URL into connection parameters."""
    check_mysql_available()
    parsed = urlparse(db_url)
    username = parsed.username or 'root'
    password = parsed.password or ''
    hostname = parsed.hostname or 'localhost'
    port = parsed.port or 3306
    database = parsed.path.strip('/') if parsed.path else None

    return {
        'user': username,
        'password': password,
        'host': hostname,
        'port': port,
        'database': database
    }

def connect_to_mysql(db_url):
    """Connect to MySQL database using URL."""
    check_mysql_available()
    conn_params = parse_mysql_url(db_url)
    return mysql.connector.connect(**conn_params)

def describe_table_schema(conn, table_name):
    """Outputs the table schema using SQL, including column comments and FK info if available."""
    database = conn.database

    query = f"""
    SELECT
        COLUMN_NAME,
        DATA_TYPE,
        CHARACTER_MAXIMUM_LENGTH,
        COLUMN_COMMENT
    FROM
        INFORMATION_SCHEMA.COLUMNS
    WHERE
        TABLE_SCHEMA = %s AND TABLE_NAME = %s;
    """

    with conn.cursor() as cursor:
        cursor.execute(query, (database, table_name))
        schema = cursor.fetchall()

    # Retrieve foreign key mapping
    foreign_keys = get_foreign_keys(conn, table_name)

    for column in schema:
        col_name, data_type, max_length, col_comment = column

        if max_length:
            line = f"{col_name} {data_type}({max_length})"
        else:
            line = f"{col_name} {data_type}"

        # Append FK info if exists
        if col_name in foreign_keys:
            fk_table, fk_column = foreign_keys[col_name]
            line += f" REFERENCES {fk_table}({fk_column})"

        # Add column comment if it exists
        if col_comment:
            line += f" -- {col_comment}"

        print(line)

def get_table_names(db_url) -> list[str]:
    """Get the table names from the database."""
    conn = connect_to_mysql(db_url)
    database = conn.database

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY TABLE_NAME;
            """,
            (database,)
        )
        table_list = cursor.fetchall()
        table_list = [table[0] for table in table_list]

    conn.close()
    return table_list

def print_table_name_options(db_url):
    """Print available table names when none are provided."""
    table_list = get_table_names(db_url)
    formatted_table_list = "\n- ".join(table_list)

    print(
        f"""
No table name provided. Please provide a table name from the list below, or use --all:

- {formatted_table_list}
        """
    )

def get_table_comment(conn, table_name):
    """Get table comment if available."""
    database = conn.database

    query = """
    SELECT TABLE_COMMENT
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s;
    """

    with conn.cursor() as cursor:
        cursor.execute(query, (database, table_name))
        result = cursor.fetchone()

        if result and result[0]:
            return result[0]

        return ""

def get_foreign_keys(conn, table_name):
    """
    Returns a dictionary mapping column names to a tuple (foreign_table, foreign_column)
    for foreign key constraints of the given table.
    """
    database = conn.database

    query = """
    SELECT
        COLUMN_NAME,
        REFERENCED_TABLE_NAME,
        REFERENCED_COLUMN_NAME
    FROM
        INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE
        REFERENCED_TABLE_SCHEMA = %s
        AND TABLE_NAME = %s
        AND REFERENCED_TABLE_NAME IS NOT NULL;
    """

    with conn.cursor() as cursor:
        cursor.execute(query, (database, table_name))
        results = cursor.fetchall()

    return {row[0]: (row[1], row[2]) for row in results}

def describe_database_and_table(db_url: str, table_names: list[str], all_tables: bool, include_data: bool = True):
    """Main function to describe database tables."""

    if not table_names and not all_tables:
        print_table_name_options(db_url)
        exit(1)

    print(
        f"""
{system_prompt()}
- You are working with a MySQL database
        """
    )

    if all_tables:
        table_names = get_table_names(db_url)

    conn = connect_to_mysql(db_url)
    try:
        for table_name in table_names:
            # Get table comment
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
                    # Sample 3 rows
                    cursor.execute(f"SELECT * FROM {table_name} ORDER BY RAND() LIMIT 3")
                    sample_rows = cursor.fetchall()

                    # Get column names
                    cursor.execute(
                        f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = %s AND TABLE_SCHEMA = %s;",
                        (table_name, conn.database)
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
    finally:
        conn.close()
