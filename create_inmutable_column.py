# esto genera un código SQL que garantiza que un (o multiples columnas) sean inmutables.
# Aclaración, fijate que la columna tenga valor por defecto o que es creada correctamente con su valor, ya que no se podrá modificar más
import re

spanish = {
    'intro': 'Necesitamos el nombre de la tabla y de la columna para escribir el código SQL',
    'input_column': 'Ingrese el nombre de la columna (tambien puede ser tabla.col o schema.tabla.col): ',
    'input_table': 'Ingrese el nombre de la tabla: ',
    'input_schema': 'Ingrese el schema (default: public): ',
    'input_allow_service': 'Quiere agregar una excepción para que un service role SI pueda escribir en esta columna? (util para desarrollo) (y/N)',
    'input_type': 'Ingrese el tipo de la columna (ej: text, int, boolean): ',
    'input_default': 'Ingrese el valor por defecto (dejar vacio si no tiene): ',
    'input_nullable': 'Permitir null? (y/N): ',
    'info_immutable': 'El Archivo SQL va a servir para que la columna {column_name} de la tabla {table_name} se vuelva inmutable',
    'done': 'Se ha escrito el archivo SQL en {file_name}',
}

english = {
    'intro': 'We need the table and column name to generate the SQL code',
    'input_column': 'Enter the column name (you can also use table.col or schema.table.col): ',
    'input_table': 'Enter the table name: ',
    'input_schema': 'Enter the schema (default: public): ',
    'input_allow_service': 'Add an exception so a service role CAN write to this column? (useful for development) (y/N)',
    'input_type': 'Enter the column type (e.g.: text, int, boolean): ',
    'input_default': 'Enter the default value (leave empty for none): ',
    'input_nullable': 'Allow null? (y/N): ',
    'info_immutable': 'The SQL file will make the column {column_name} on table {table_name} immutable',
    'done': 'SQL file written to {file_name}',
}


MSG = english

#si tienen mayusculas vamos a usar las comillas
def quote_sql_identifier(name):
    if name.lower() != name:
        return '"' + name + '"'
    return name

# sanitiza un nombre para usarlo como parte de un identificador SQL (ej: nombre de función/trigger)
def sanitize_identifier(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


print(MSG['intro'])


raw_column_name = input(MSG['input_column'])

# si el usuario puso algo como tabla.columna, ya tenemos ambos raw names, no preguntar
# por tabla (y asumir schema public) 
# y si el usuario puso sch.tabla.col entonces mismo pero sacar de acá el raw_schema_name tambien

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

column_type = input(MSG['input_type']) or 'text'
default_value = input(MSG['input_default'])
allow_null = input(MSG['input_nullable']).lower() in ['y','yes','si','ok']

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

while column_type.lower() not in valid_postgress_types:
    print(f'Tipo "{column_type}" no es un tipo válido de PostgreSQL.')
    column_type = input(MSG['input_type'])

column_name_sql = quote_sql_identifier(column_name)
table_name_sql = quote_sql_identifier(table_name)
schema_name_sql = quote_sql_identifier(schema_name)

print()

allow_service = input(MSG['input_allow_service']).lower() in ['y','yes','si','ok','allow']


print(MSG['info_immutable'].format(column_name=column_name, table_name=table_name))


# el true es para evitar excepciones si el 'request.jwt.claim.role' no existe.
allow_service_role_code = """
    if current_setting('request.jwt.claim.role', true) = 'service_role' then
    return new;
    end if;
""" if allow_service else ''



# chequeamos  DISTINCT FROM para no frenar los noop updates

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

not_null_sql = '' if allow_null else ' not null'
default_sql = format_default(default_value, column_type)

sql = f"""
alter table {schema_name_sql}.{table_name_sql}
add column if not exists {column_name_sql} {column_type}{not_null_sql}{default_sql};

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


file_name = f'no_modify_{schema_name}_{column_name}_on_{table_name}.sql'

with open(file_name, 'w+') as f:
    f.write(sql)

print(MSG['done'].format(file_name=file_name))


