from pkg_resources import require
import click
from . import sqlite
from . import postgres


@click.command()
@click.argument(
    "database_url",
)
@click.argument(
    "table_name",
    required=False,
)
def main(database_url, table_name):
    """
    Generate a prompt for a table in a database for use in chatgpt or other LLMs to help write SQL.

    - DATABASE_URL Could be a file path or a postgres url reference. Does not support postgres+ssh protocols.

    - TABLE_NAME Name of the table to generate a prompt for. If not provided, will generate a prompt for all tables in the database.
    """

    if "postgresql" in database_url:
        postgres.describe_database_and_table(database_url, table_name)
    elif "sqlite" in database_url:
        sqlite.describe_database_and_table(database_url, table_name)
    else:
        print("Unknown database type.")
        exit(1)
