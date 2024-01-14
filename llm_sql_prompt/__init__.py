from pkg_resources import require
import click
from . import sqlite
from . import postgres


@click.command()
@click.argument("database_url", type=click.Path(exists=True))
@click.argument("table_name", required=False)
def main(database_url, table_name):
    if "postgresql" in database_url:
        postgres.describe_database_and_table(database_url, table_name)
    elif "sqlite" in database_url:
        sqlite.describe_database_and_table(database_url, table_name)
    else:
        print("Unknown database type.")
        exit(1)
