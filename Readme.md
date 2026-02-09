# trq-sql-tools

Herramientas para generar código SQL de PostgreSQL de forma interactiva.

## Requisitos

- **Python 3** instalado. Antes de correr los scripts, validá tu instalación con:
  ```bash
  python --version
  ```
  Si no funciona, probá con `py --version` (en Windows a veces Python se instala como `py`).

## Importante

El archivo `.sql` generado se crea en el **directorio actual** desde donde se ejecuta el script (es decir, donde estés parado en la terminal).

## Uso

### `inmutable_column.py`

Genera un archivo SQL que hace **inmutable** una columna, usando un trigger que bloquea updates. Opcionalmente, también puede **crear la columna** si no existe.

```bash
python inmutable_column.py [tabla.columna] [flags]
```

**Genera:** `no_modify_{schema}_{columna}_on_{tabla}.sql`

### Argumentos

| Argumento | Descripción |
|-----------|-------------|
| `tabla.columna` | Nombre de la columna (también acepta `columna` sola o `schema.tabla.columna`). Si no se pasa, se pregunta por input |

### Flags

| Flag | Descripción |
|------|-------------|
| `--service` | Agrega excepción para que el `service_role` pueda modificar la columna |
| `--create-column [tipo]` | Crea la columna si no existe (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`). Si no se pasa tipo, se pregunta interactivamente (default: `text`) |
| `--default [valor]` | Valor por defecto de la columna (solo con `--create-column`) |
| `--not-null` | La columna no permite `NULL` (solo con `--create-column`) |

### Ejemplos

```bash
# solo trigger de inmutabilidad (interactivo)
python inmutable_column.py

# con notación de puntos
python inmutable_column.py tabla.columna

# con service role exception
python inmutable_column.py tabla.columna --service

# crear columna (pregunta tipo/default/null interactivamente)
python inmutable_column.py tabla.columna --create-column

# crear columna con todo por CLI
python inmutable_column.py tabla.columna --create-column text --default hola --not-null

# crear uuid con gen_random_uuid()
python inmutable_column.py tabla.id --create-column uuid --default new --not-null --service
```

### Atajos para default value

| Tipo | Input | SQL generado |
|------|-------|-------------|
| `uuid` | `new` | `default gen_random_uuid()` |
| `timestamp`, `date`, etc. | `now` | `default now()` |

### Quoting automático del default

- **Numéricos y boolean**: sin comillas (`default 42`)
- **Texto, date, etc.**: con comillas (`default 'valor'`)
- **json, jsonb, uuid**: con comillas y cast (`default '{"a":1}'::jsonb`)
- Si el usuario ya incluyó comillas simples, se respetan tal cual

### El SQL generado incluye

- `BEGIN;` / `COMMIT;` para envolver todo en una transacción
- `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (solo con `--create-column`)
- Función PL/pgSQL que bloquea updates en la columna (usa `IS DISTINCT FROM` para no frenar noop updates)
- `DROP TRIGGER IF EXISTS` para poder re-ejecutar sin errores
- `CREATE TRIGGER` que ejecuta la función antes de cada update

---

## Notación con puntos

Al ingresar el nombre de la columna se puede usar:

- `columna` → pregunta tabla y schema por separado
- `tabla.columna` → asume schema `public`
- `schema.tabla.columna` → usa los tres valores directamente

## Idioma

Para cambiar el idioma, modificar `MSG = english` por `MSG = spanish` en `localization.py`.
