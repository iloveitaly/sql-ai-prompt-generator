from pathlib import Path
import click
from . import sqlite
from . import postgres
from . import mysql


@click.command()
@click.argument(
    "database_url",
)
@click.argument("table_names", required=False, nargs=-1)
@click.option(
    "--all",
    is_flag=True,
    default=False,
    help="Generate a prompt for all tables in the database.",
)
@click.option(
    "--no-data",
    is_flag=True,
    default=False,
    help="Exclude sample data from the generated prompt.",
)
def main(database_url, table_names: tuple[str], all: bool, no_data: bool):
    """
    Generate a prompt for a table in a database for use in chatgpt or other LLMs to help write SQL.

    - DATABASE_URL Could be a file path or a database url reference. Supports sqlite, postgres, and mysql.

    - TABLE_NAME Name of the table to generate a prompt for. If not provided, will generate a prompt for all tables in the database.
    """
    # Convert the no_data flag to include_data parameter (inverse logic)
    include_data = not no_data

    if "postgresql" in database_url:
        postgres.describe_database_and_table(database_url, table_names, all, include_data)
    elif "mysql" in database_url:
        mysql.describe_database_and_table(database_url, table_names, all, include_data)
    elif ("sqlite" in database_url) or Path(database_url).exists():
        sqlite.describe_database_and_table(database_url, table_names, all, include_data)
    else:
        print("Unknown database type. If you are referencing a SQLite database, make sure you've specified a valid file path")
        exit(1)
