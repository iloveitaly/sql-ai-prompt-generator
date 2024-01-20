# ChatGPT Prompt for SQL Writing

Generate a prompt for writing SQL queries with LLMs like ChatGPT. Drop your database URL and table name into the script and it will generate a prompt for you to copy and paste into your favorite LLM.

## What this does

- Snapshot of Table Structure: Understand the columns, types, and organization of your table at a glance.
- Sample Rows: Includes INSERT statements to describe the data in your table.

## Usage

```shell
Usage: llm-sql-prompt [OPTIONS] DATABASE_URL [TABLE_NAME]

Options:
  --help  Show this message and exit.
```

Generate a prompt from a postgres database:

```shell
llm-sql-prompt postgresql://postgres:postgres@localhost:5555/database_name table_name | pbcopy
llm-sql-prompt $DATABASE_URL
```

## TODO

Super basic script, needs a lot of work

- [x] pg support
- [x] one entrypoint
- [ ] multiple tables
- [ ] prompt tweaking
- [ ] understand prompt size limits and sample records until one fits