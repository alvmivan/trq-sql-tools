# esto genera un código SQL que garantiza que un (o multiples columnas) sean inmutables.
# opcionalmente, con --create-column, también crea la columna si no existe.
import sys
from localization import MSG
from shared import (
    parse_column_input, quote_sql_identifier, generate_immutable_trigger_sql,
    write_sql_file, format_default, valid_postgress_types,
)

def get_flag_value(argv, flag):
    """Devuelve el valor siguiente a un flag (ej: --default hola -> 'hola'), o None si no está."""
    if flag not in argv:
        return None
    idx = argv.index(flag)
    if idx + 1 < len(argv) and not argv[idx + 1].startswith('--'):
        return argv[idx + 1]
    return ''

print(MSG['intro'])

argv = sys.argv[1:]

# separar el argumento posicional (column name) de los flags
# el primer arg que no empieza con -- es el column name
positional = None
for i, a in enumerate(argv):
    if not a.startswith('--'):
        # saltar valores que son parte de un flag (ej: --default hola)
        if i > 0 and argv[i-1] in ('--default', '--create-column'):
            continue
        positional = a
        break

raw_column_name = positional if positional else input(MSG['input_column'])
schema_name, table_name, column_name = parse_column_input(raw_column_name)

allow_service = '--service' in argv
create_column = '--create-column' in argv

sql = ''

if create_column:
    create_column_value = get_flag_value(argv, '--create-column')
    default_flag = get_flag_value(argv, '--default')
    not_null = '--not-null' in argv

    # si --create-column viene solo (sin tipo), preguntar interactivamente
    if create_column_value == '':
        column_type = input(MSG['input_type']) or 'text'
        default_value = input(MSG['input_default'])
        allow_null = input(MSG['input_nullable']).lower() in ['y','yes','si','ok']
    else:
        column_type = create_column_value
        default_value = default_flag if default_flag is not None else ''
        allow_null = not not_null

    while column_type.lower() not in valid_postgress_types:
        print(f'Tipo "{column_type}" no es un tipo válido de PostgreSQL.')
        column_type = input(MSG['input_type'])

    column_name_sql = quote_sql_identifier(column_name)
    table_name_sql = quote_sql_identifier(table_name)
    schema_name_sql = quote_sql_identifier(schema_name)

    not_null_sql = '' if allow_null else ' not null'
    default_sql = format_default(default_value, column_type)

    sql += f"""
alter table {schema_name_sql}.{table_name_sql}
add column if not exists {column_name_sql} {column_type}{not_null_sql}{default_sql};
"""

print(MSG['info_immutable'].format(column_name=column_name, table_name=table_name))

sql += generate_immutable_trigger_sql(schema_name, table_name, column_name, allow_service)

write_sql_file(schema_name, column_name, table_name, sql)


