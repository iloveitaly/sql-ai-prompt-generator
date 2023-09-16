# ChatGPT Prompt for SQL Writing

Generate a prompt for writing SQL queries with LLMs like ChatGPT.

## What this does

- Snapshot of Table Structure: Understand the columns, types, and organization of your table at a glance.
- Sample Rows: Includes INSERT statements to describe the data in your table.

## Usage

```
Usage: script.py [OPTIONS] DB_FILENAME TABLE_NAME

Options:
  --help  Show this message and exit.
```

Generate a prompt from a postgres database:

```shell
python ./postgres.py postgresql://postgres:postgres@localhost:5555/database_name table_name | pbcopy
```

## TODO

Super basic script, needs a lot of work

- [x] pg support
- [ ] one entrypoint
- [ ] multiple tables
- [ ] prompt tweaking