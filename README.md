# ChatGPT Prompt for SQL Writing

Generate a prompt for writing SQL queries with LLMs like ChatGPT. Drop your database URL and table name into the script and it will generate a prompt for you to copy and paste into your favorite LLM.

## What this does

- Snapshot of Table Structure: Understand the columns, types, and organization of your table at a glance.
- Sample Rows: Includes INSERT statements to describe the data in your table.
- Extracts Table and Field Comments: If you have comments on your tables or columns, they will be included in the prompt.

## Usage

Install the package:

```shell
pip install llm-sql-prompt
```

Here's how to use it:

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

From a local sqlite database:

```shell
llm-sql-prompt "$HOME/Library/Application Support/BeeperTexts/index.db" --all
```

### Tunneling to a remote port

If you find yourself wanting to tunnel into a remote box and work with a production database, here's some helpful commands so you don't need to remember the weird SSH tunneling syntax:

```shell
function find_random_open_port() {
  local start_port=${1:-1024}
  local max_attempts=100
  local attempt=0
  local port=$start_port

  while (( attempt < max_attempts )); do
    if ! nc -z localhost $port 2>/dev/null; then
      echo $port
      return
    fi
    port=$((port + 1))
    attempt=$((attempt + 1))
  done

  echo "No open port found after $max_attempts attempts, starting from $start_port." > /dev/stderr
  return 1
}


function ssh-tunnel() {
  if [ $# -lt 2 ]; then
    echo "Usage: ssh-tunnel remote_host remote_port [local_port]"
    echo "This function sets up SSH port forwarding."
    return 1
  fi

  local remote_host=$1
  local remote_port=$2
  local local_port=${3:-$(find-random-open-port $remote_port)}

  if [[ -z $local_port ]]; then
    echo "Failed to find an open local port."
    return 1
  fi

  echo "Forwarding local port $local_port to remote port $remote_port on $remote_host..."
  set -x
  ssh $remote_host -L ${local_port}:localhost:${remote_port}
}
```

## TODO

Super basic script, needs a lot of work

- [x] pg support
- [x] one entrypoint
- [x] use DB comments on columns + tables
- [x] multiple tables
- [ ] prompt tweaking
- [ ] understand prompt size limits and sample records until one fits