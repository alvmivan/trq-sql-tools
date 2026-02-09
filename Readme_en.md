# trq-sql-tools

Tools to interactively generate PostgreSQL SQL code.

## Requirements

- **Python 3** installed. Before running the scripts, verify your installation with:
  ```bash
  python --version
  ```
  If that doesn't work, try `py --version` (on Windows, Python is sometimes installed as `py`).

## Language setup

By default, the tool runs in **Spanish**. To switch to English, open `localization.py` and change:

```python
MSG = spanish
```

to:

```python
MSG = english
```

## Important

The generated `.sql` file is created in the **current directory** where you run the script from.

## Usage

### `inmutable_column.py`

Generates a SQL file that makes a column **immutable** using a trigger that blocks updates. Optionally, it can also **create the column** if it doesn't exist.

```bash
python inmutable_column.py [table.column] [flags]
```

**Generates:** `no_modify_{schema}_{column}_on_{table}.sql`

### Arguments

| Argument | Description |
|----------|-------------|
| `table.column` | Column name (also accepts just `column` or `schema.table.column`). If not provided, it will be asked via input |

### Flags

| Flag | Description |
|------|-------------|
| `--service` | Adds an exception so the `service_role` can modify the column |
| `--create-column [type]` | Creates the column if it doesn't exist (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`). If no type is provided, it will be asked interactively (default: `text`) |
| `--default [value]` | Default value for the column (only with `--create-column`) |
| `--not-null` | Column does not allow `NULL` (only with `--create-column`) |

### Examples

```bash
# immutability trigger only (interactive)
python inmutable_column.py

# with dot notation
python inmutable_column.py table.column

# with service role exception
python inmutable_column.py table.column --service

# create column (asks type/default/null interactively)
python inmutable_column.py table.column --create-column

# create column with everything via CLI
python inmutable_column.py table.column --create-column text --default hello --not-null

# create uuid with gen_random_uuid()
python inmutable_column.py table.id --create-column uuid --default new --not-null --service
```

### Default value shortcuts

| Type | Input | Generated SQL |
|------|-------|---------------|
| `uuid` | `new` | `default gen_random_uuid()` |
| `timestamp`, `date`, etc. | `now` | `default now()` |

### Automatic default quoting

- **Numeric and boolean**: no quotes (`default 42`)
- **Text, date, etc.**: quoted (`default 'value'`)
- **json, jsonb, uuid**: quoted with cast (`default '{"a":1}'::jsonb`)
- If the user already included single quotes, they are respected as-is

### Generated SQL includes

- `BEGIN;` / `COMMIT;` to wrap everything in a transaction
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (only with `--create-column`)
- PL/pgSQL function that blocks updates on the column (uses `IS DISTINCT FROM` to allow noop updates)
- `DROP TRIGGER IF EXISTS` so the file can be re-run without errors
- `CREATE TRIGGER` that executes the function before each update

---

## Dot notation

When entering the column name you can use:

- `column` → asks for table and schema separately
- `table.column` → assumes schema `public`
- `schema.table.column` → uses all three values directly
