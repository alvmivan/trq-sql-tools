import re
from localization import MSG

#si tienen mayusculas vamos a usar las comillas
def quote_sql_identifier(name):
    if name.lower() != name:
        return '"' + name + '"'
    return name

# sanitiza un nombre para usarlo como parte de un identificador SQL (ej: nombre de función/trigger)
def sanitize_identifier(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

# Lista de los tipos válidos en Postgress
valid_postgress_types = [
    'smallint', 'integer', 'int', 'bigint', 'serial', 'bigserial',
    'real', 'double precision', 'float', 'numeric', 'decimal',
    'boolean', 'bool',
    'text', 'varchar', 'char', 'character varying', 'character',
    'uuid',
    'date', 'time', 'timestamp', 'timestamptz', 'timestamp with time zone',
    'interval',
    'json', 'jsonb',
    'bytea',
    'inet', 'cidr', 'macaddr',
    'int4range', 'int8range', 'numrange', 'tsrange', 'tstzrange', 'daterange',
    'point', 'line', 'lseg', 'box', 'path', 'polygon', 'circle',
    'xml', 'money', 'bit', 'bit varying',
    'smallserial', 'oid',
]

# tipos que no necesitan comillas en el default (numéricos y boolean)
unquoted_types = [
    'smallint', 'integer', 'int', 'bigint', 'serial', 'bigserial',
    'real', 'double precision', 'float', 'numeric', 'decimal',
    'boolean', 'bool', 'smallserial', 'money',
]

# tipos que necesitan cast explícito
cast_types = ['json', 'jsonb', 'uuid']

date_types = ['date', 'time', 'timestamp', 'timestamptz', 'timestamp with time zone']

def format_default(value, col_type):
    if not value:
        return ''
    # atajos: "new" para uuid genera gen_random_uuid(), "now" para fechas genera now()
    if value.lower() == 'new' and col_type.lower() == 'uuid':
        return ' default gen_random_uuid()'
    if value.lower() == 'now' and col_type.lower() in date_types:
        return ' default now()'
    # si el usuario ya puso comillas, respetar tal cual
    if value.startswith("'") and value.endswith("'"):
        return f' default {value}'
    if col_type.lower() in unquoted_types:
        return f' default {value}'
    if col_type.lower() in cast_types:
        return f" default '{value}'::{col_type}"
    return f" default '{value}'"

def parse_column_input(raw_column_name):
    """Parsea el input de columna y devuelve (schema_name, table_name, column_name)."""
    parts = raw_column_name.split('.')

    if len(parts) == 3:
        schema_name = sanitize_identifier(parts[0])
        table_name = sanitize_identifier(parts[1])
        column_name = sanitize_identifier(parts[2])
    elif len(parts) == 2:
        schema_name = sanitize_identifier('public')
        table_name = sanitize_identifier(parts[0])
        column_name = sanitize_identifier(parts[1])
    else:
        column_name = sanitize_identifier(raw_column_name)
        table_name = sanitize_identifier(input(MSG['input_table']))
        schema_name = sanitize_identifier(input(MSG['input_schema']) or 'public')

    return schema_name, table_name, column_name

def generate_immutable_trigger_sql(schema_name, table_name, column_name, allow_service):
    """Genera el SQL del trigger de inmutabilidad."""
    column_name_sql = quote_sql_identifier(column_name)
    table_name_sql = quote_sql_identifier(table_name)
    schema_name_sql = quote_sql_identifier(schema_name)

    # el true es para evitar excepciones si el 'request.jwt.claim.role' no existe.
    allow_service_role_code = """
    if current_setting('request.jwt.claim.role', true) = 'service_role' then
    return new;
    end if;
""" if allow_service else ''

    # chequeamos  DISTINCT FROM para no frenar los noop updates
    sql = f"""
create or replace function prevent_{schema_name}_{column_name}_update_on_{table_name}()
returns trigger
language plpgsql
as $$
begin
{allow_service_role_code}
    if new.{column_name_sql} IS DISTINCT FROM old.{column_name_sql} then  
        raise exception using
            errcode = '42501',
            message = '{column_name.replace(chr(39), chr(39)*2)} is immutable';
    end if;
    return new;
end;
$$;

drop trigger if exists trg_prevent_{schema_name}_{column_name}_update_on_{table_name} on {schema_name_sql}.{table_name_sql};

create trigger trg_prevent_{schema_name}_{column_name}_update_on_{table_name}
before update on {schema_name_sql}.{table_name_sql}
for each row
execute function prevent_{schema_name}_{column_name}_update_on_{table_name}();
"""
    return sql

def write_sql_file(schema_name, column_name, table_name, sql):
    """Escribe el archivo SQL y muestra el mensaje de éxito."""
    file_name = f'no_modify_{schema_name}_{column_name}_on_{table_name}.sql'
    with open(file_name, 'w+') as f:
        f.write('begin;\n' + sql + '\ncommit;\n')
    print(MSG['done'].format(file_name=file_name))
