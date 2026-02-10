# esto genera un SQL que replica filas de una tabla source a una tabla target al hacer INSERT.
import sys
from localization import MSG
from shared import sanitize_identifier, quote_sql_identifier, write_sql_file

def get_flag_value(argv, flag):
    """Devuelve el valor siguiente a un flag, o None si no está."""
    if flag not in argv:
        return None
    idx = argv.index(flag)
    if idx + 1 < len(argv) and not argv[idx + 1].startswith('--'):
        return argv[idx + 1]
    return ''

def parse_table_input(raw):
    """Parsea schema.table y devuelve (schema, table) sanitizados."""
    parts = raw.split('.')
    if len(parts) == 2:
        return sanitize_identifier(parts[0]), sanitize_identifier(parts[1])
    return 'public', sanitize_identifier(parts[0])

print(MSG['repl_intro'])

argv = sys.argv[1:]

# flags con valor
source_flag = get_flag_value(argv, '--source')
target_flag = get_flag_value(argv, '--target')
cols_flag = get_flag_value(argv, '--cols')
target_cols_flag = get_flag_value(argv, '--target-cols')
source_cols_flag = get_flag_value(argv, '--source-cols')
avoid_security_definer = '--avoid-security-definer' in argv

# tablas
table_source_raw = source_flag if source_flag else input(MSG['repl_input_source'])
table_target_raw = target_flag if target_flag else input(MSG['repl_input_target'])

source_schema, source_table = parse_table_input(table_source_raw)
target_schema, target_table = parse_table_input(table_target_raw)

# columnas
if cols_flag is not None and cols_flag != '':
    columns_target_data = [sanitize_identifier(c.strip()) for c in cols_flag.split(',')]
    columns_source_data = columns_target_data
elif target_cols_flag is not None and source_cols_flag is not None:
    columns_target_data = [sanitize_identifier(c.strip()) for c in target_cols_flag.split(',')]
    columns_source_data = [sanitize_identifier(c.strip()) for c in source_cols_flag.split(',')]
else:
    # interactivo: preguntar si son iguales o distintas
    cols_input = input(MSG['repl_input_cols'])
    if cols_input:
        columns_target_data = [sanitize_identifier(c.strip()) for c in cols_input.split(',')]
        columns_source_data = columns_target_data
    else:
        columns_target_data = [sanitize_identifier(c.strip()) for c in input(MSG['repl_input_target_cols']).split(',')]
        columns_source_data = [sanitize_identifier(c.strip()) for c in input(MSG['repl_input_source_cols']).split(',')]

# validar cantidad de columnas
if len(columns_target_data) != len(columns_source_data):
    print(MSG['repl_error_cols_mismatch'].format(source=len(columns_source_data), target=len(columns_target_data)))
    sys.exit(1)

# construir SQL
source_full = f'{quote_sql_identifier(source_schema)}.{quote_sql_identifier(source_table)}'
target_full = f'{quote_sql_identifier(target_schema)}.{quote_sql_identifier(target_table)}'

unique_name = f'trq_create_new_{target_schema}_{target_table}_based_on_{source_schema}_{source_table}'
function_name = unique_name + '_function'
trigger_name = unique_name + '_trigger'

columns_target_sql = ', '.join([quote_sql_identifier(c) for c in columns_target_data])
columns_source_sql = ', '.join([f'new.{quote_sql_identifier(c)}' for c in columns_source_data])

security_definer_sql = '' if avoid_security_definer else '\nsecurity definer\nset search_path = public'

print(MSG['repl_info'].format(source=source_full, target=target_full))

sql = f"""
create or replace function {quote_sql_identifier(source_schema)}.{function_name}()
returns trigger
language plpgsql{security_definer_sql}
as $$
begin
    insert into {target_full} (
        {columns_target_sql}
    )
    values (
        {columns_source_sql}
    )
    on conflict do nothing;
    return new;
end;
$$;

drop trigger if exists {trigger_name} on {source_full};

create trigger {trigger_name}
after insert on {source_full}
for each row
execute function {quote_sql_identifier(source_schema)}.{function_name}();
"""

file_name = f'repl_{source_schema}_{source_table}_to_{target_schema}_{target_table}.sql'
write_sql_file(file_name, sql)