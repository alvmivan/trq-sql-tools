# esto genera un código SQL que garantiza que un (o multiples columnas) sean inmutables.
# Aclaración, fijate que la columna tenga valor por defecto o que es creada correctamente con su valor, ya que no se podrá modificar más

import re

#si tienen mayusculas vamos a usar las comillas
def quote_sql_identifier(name):
    if name.lower() != name:
        return '"' + name + '"'
    return name

# sanitiza un nombre para usarlo como parte de un identificador SQL (ej: nombre de función/trigger)
def sanitize_identifier(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


print('Necesitamos el nombre de la tabla y de la columna para escribir el código SQL')


raw_column_name = input('Ingrese el nombre de la columna: ')

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
    table_name = sanitize_identifier(input('Ingrese el nombre de la tabla: '))
    schema_name = sanitize_identifier(input('Ingrese el schema (default: public): ') or 'public')

column_name_sql = quote_sql_identifier(column_name)
table_name_sql = quote_sql_identifier(table_name)
schema_name_sql = quote_sql_identifier(schema_name)

print()

allow_service = input('Quiere agregar una excepción para que un service role SI pueda escribir en esta columna? (util para desarrollo) (y/N)').lower() in ['y','yes','si','ok','allow']


print(f'El Archivo SQL va a servir para que la columna {column_name} de la tabla {table_name} se vuelva inmutable')


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

create trigger trg_prevent_{schema_name}_{column_name}_update_on_{table_name}
before update on {schema_name_sql}.{table_name_sql}
for each row
execute function prevent_{schema_name}_{column_name}_update_on_{table_name}();
"""


file_name = f'no_modify_{schema_name}_{column_name}_on_{table_name}.sql'

with open(file_name, 'w+') as f:
    f.write(sql)

print('Se ha escrito el archivo SQL en ',file_name)


