import click
from . import sqlite
from . import postgres


@click.command()
@click.argument(
    "database_url",
)
@click.argument("table_names", required=False, nargs=-1)
def main(database_url, table_names: tuple[str]):
    """
    Generate a prompt for a table in a database for use in chatgpt or other LLMs to help write SQL.

    - DATABASE_URL Could be a file path or a postgres url reference. Does not support postgres+ssh protocols.

    - TABLE_NAME Name of the table to generate a prompt for. If not provided, will generate a prompt for all tables in the database.
    """

    if "postgresql" in database_url:
        postgres.describe_database_and_table(database_url, table_names)
    elif "sqlite" in database_url:
        sqlite.describe_database_and_table(database_url, table_names)
    else:
        print("Unknown database type.")
        exit(1)
