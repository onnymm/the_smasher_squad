import pandas as pd
import os
import json
import importlib
from typing import Literal
from sqlalchemy import (
    create_engine,
    insert,
    select,
    update,
    delete,
    or_,
    and_,
    asc,
    desc,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase
)
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.orm.attributes import InstrumentedAttribute
from ._types import (
    CriteriaStructure,
    _TripletStructure,
    _LogicOperator,
    _CommonType,
    _OutputFormat,
    _ConnectionParams
)
from sqlalchemy.sql.selectable import Select

# Tipos de dato
_DatabaseConnection = Literal["real", "test"]

class DMLManager():
    """
    # Manejador de transacciones con una base de datos
    Este módulo realiza las transacciones de `CREATE`, `SELECT`, `UPDATE` y
    `DELETE` así como algunos otros métodos comunes útiles para la gestión del CRUD
    en una aplicación.

    ### Uso
    Primeramente se deben inicializar los modelos de tabla adecuados y los siguientes campos
    comunes en la clase `_Base`:
    >>> from sqlalchemy.orm import DeclarativeBase, ...
    >>> 
    >>> class _Base(DeclarativeBase):
    >>>     id: Mapped[int] = mapped_column(Integer, primary_key= True)
    >>>     create_date: Mapped[DateTime] = mapped_column(DateTime, default= datetime.now)
    >>>     write_date: Mapped[DateTime] = mapped_column(DateTime, default= datetime.now, onupdate=datetime.now)
    >>> 
    >>> class Users(_Base):
    >>>     __tablename__ = "users"
    >>>     user: Mapped[str] = mapped_column(String(24), nullable= False, unique= True)
    >>>     name: Mapped[str] = mapped_column(String(60), nullable= False)

    Después se crea un archivo `.json` de configuración en la carpeta raíz del proyecto con el siguiente formato:
    ```
    {
        "connections": {
            "real": {
                "host": ...,
                "port": ...,
                "name": ...,
                "user": ...,
                "password": ...,
                "path": "app.database.models...",
                "tables": [
                    {
                        "table_name": users,
                        "table_instance": Users
                    },
                    ...
                ]
            },
            "test": {...}
        }
    }
    ```

    Finalmente se inicializa la instancia, proporcionando el nombre del archivo de configuración (Sin nombre
    de extensión) y el tipo de base de datos con el que se usará. El valor por defecto es `"real"`:
    >>> db = DMLManager("db_config", "real")

    ----
    ## Creación de registros
    `DMLManager.create()`

    Este método realiza la creación de uno o muchos registros a partir del
    nombre de la tabla proporcionado y un diccionario (un único registro) o
    una lista de diccionarios (muchos registros).

    Uso:
    >>> # Para un solo registro
    >>> record = {
    >>>     'user': 'onnymm',
    >>>     'name': 'Onnymm Azzur',
    >>> }
    >>> 
    >>> db.create('users', record)
    >>> #    id    user          name         create_date          write_date
    >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
    >>> 
    >>> # Para muchos registros
    >>> records = [
    >>>     {
    >>>         'user': 'onnymm',
    >>>         'name': 'Onnymm Azzur',
    >>>     },
    >>>     {
    >>>         'user': 'lumii',
    >>>         'name': 'Lumii Mynx',
    >>>     },
    >>> ]
    >>> 
    >>> db.create('users', records)
    >>> #    id    user          name         create_date          write_date
    >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
    >>> # 1   3   lumii    Lumii Mynx 2024-11-04 11:16:59 2024-11-04 11:16:59

    ----
    ## Búsqueda de registros
    `DMLManager.search()`

    Este método retorna todos los registros de una tabla o los registros que cumplan
    con la condición de búsqueda provista, además de segmentar desde un índice
    inicial de desfase y/o un límite de cantidad de registros retornada.

    Uso:
    >>> # Ejemplo 1
    >>> db.search('users')
    >>> # [1, 2, 3, 4, 5]
    >>> 
    >>> # Ejemplo 2
    >>> db.search('commisions', [('user_id', '=', 213)])
    >>> # [7, 9, 12, 13, 17, 21, ...]

    ### Los parámetros de entrada son:
    - `table_name`: Nombre de la tabla de donde se tomarán los registros.
    - `search_criteria`: Criterio de búsqueda para retornar únicamente los resultados que
    cumplan con las condiciones provistas (Consultar estructura más abajo).
    - `offset`: Desfase de inicio de primer registro a mostrar.
    - `limit`: Límite de registros retornados por la base de datos.

    ----
    ## Búsqueda y lectura de registros
    `DMLManager.search_read()`
    Este método retorna un DataFrame con el contenido de los registros de una
    tabla de la base de datos, en el orden en el que se especificaron los campos
    o todos los campos en caso de no haber sido especificados.

    ### Los parámetros de entrada son:
    - `table_name`: Nombre de la tabla de donde se tomarán los registros.
    - `search_criteria`: Criterio de búsqueda para retornar únicamente los resultados que
    cumplan con las condiciones provistas (Consultar estructura más abajo).
    - `fields`: Campos a mostrar. En caso de no ser especificado, se toman todos los
    campos de la tabla de la base de datos.
    - `offset`: Desfase de inicio de primer registro a mostrar.
    - `limit`: Límite de registros retornados por la base de datos.

    Uso:
    >>> # Ejemplo 1
    >>> db.search_read('users')
    >>> #    id    user          name         create_date          write_date
    >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
    >>> # 1   3   lumii    Lumii Mynx 2024-11-04 11:16:59 2024-11-04 11:16:59
    >>> 
    >>> # Ejemplo 2
    >>> db.search_read('users', [('user', '=', 'onnymm')])
    >>> #    id    user          name         create_date          write_date
    >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
    >>> 
    >>> # Ejemplo 3
    >>> db.search_read('users', [], ['user', 'create_date'])
    >>> #    id         name         create_date
    >>> # 0   2 Onnymm Azzur 2024-11-04 11:16:59
    >>> # 1   3   Lumii Mynx 2024-11-04 11:16:59

    ----
    ## Búsqueda y conteo de resultados
    `DMLManager.search_count()`

    Este método retorna el conteo de de todos los registros de una tabla o los
    registros que cumplan con la condición de búsqueda provista, ideal para funcionalidades
    de paginación que muestran un total de registros.

    Uso:
    >>> # Ejemplo 1
    >>> db.search_count('users')
    >>> # 5
    >>> 
    >>> # Ejemplo 2
    >>> db.search_count('commisions', [('user_id', '=', 213)])
    >>> # 126

    ### Los parámetros de entrada son:
    - `table_name`: Nombre de la tabla de donde se tomarán los registros.
    - `search_criteria`: Criterio de búsqueda para retornar únicamente los resultados que
    cumplan con las condiciones provistas (Consultar estructura más abajo).

    ----
    ## Actualización de registros
    `DMLManager.update()`

    Este método realiza la actualización de uno o más registros a partir de su respectiva
    ID provista, actualizando uno o más campos con el valor provisto. Este método solo
    sobreescribe un mismo valor por cada campo a todos los registros provistos.

    ### Los parámetros de entrada son:
    - `table_name`: Nombre de la tabla en donde se harán los cambios
    - `record_ids`: ID o lista de IDs a actualizar
    - `data`: Diccionario de valores a modificar masivamente

    Uso:
    >>> db.search_read('users', fields= ['user', 'name'])
    >>> #    id     user                  name
    >>> # 0   3   onnymm          Onnymm Azzur
    >>> # 1   4    lumii            Lumii Mynx
    >>> # 2   5  user001  Persona Sin Nombre 1
    >>> # 3   6  user002  Persona Sin Nombre 2
    >>> # 4   7  user003  Persona Sin Nombre 3
    >>> 
    >>> # Modificación
    >>> db.update("users", [3, 4, 5, 6, 7], {'name': 'Cambiado'})
    >>> #    id     user      name
    >>> # 0   3   onnymm  Cambiado
    >>> # 1   4    lumii  Cambiado
    >>> # 2   5  user001  Cambiado
    >>> # 3   6  user002  Cambiado
    >>> # 4   7  user003  Cambiado

    ----
    ## Eliminación de registros
    `DMLManager.delete()`

    Este método realiza la eliminación de uno o más registros de la base datos a partir de
    su respectiva ID provista.

    Uso:
    >>> #    id     user                  name
    >>> # 0   3   onnymm          Onnymm Azzur
    >>> # 1   4    lumii            Lumii Mynx
    >>> # 2   5  user001  Persona Sin Nombre 1
    >>> # 3   6  user002  Persona Sin Nombre 2
    >>> # 4   7  user003  Persona Sin Nombre 3
    >>> 
    >>> # Eliminación
    >>> db.delete("users", 3)
    >>> #    id     user                  name
    >>> # 1   4    lumii            Lumii Mynx
    >>> # 2   5  user001  Persona Sin Nombre 1
    >>> # 3   6  user002  Persona Sin Nombre 2
    >>> # 4   7  user003  Persona Sin Nombre 3

    ----
    ### Estructura de criterio de búsqueda
    La estructura del criterio de búsqueda consiste en una lista de tuplas de 3 valores, mejor
    conocidas como tripletas. Cada una de estas tripletas consiste en 3 diferentes parámetros:
    1. Nombre del campo de la tabla
    2. Operador de comparación
    3. Valor de comparación

    Algunos ejemplos de tripletas son:
    >>> ('id', '=', 5)
    >>> # ID es igual a 5
    >>> ('amount', '>', 500)
    >>> # "amount" es mayor a 500
    >>> ('name', 'ilike', 'as')
    >>> # "name" contiene "as"

    Los operadores de comparación disponibles son:
    - `'='`: Igual a
    - `'!='`: Diferente de
    - `'>'`: Mayor a
    - `'>='`: Mayor o igual a
    - `'<`': Menor que
    - `'<='`: Menor o igual que
    - `'><'`: Entre
    - `'in'`: Está en
    - `'not in'`: No está en
    - `'ilike'`: Contiene
    - `'not ilike'`: No contiene

    Estas tuplas deben contenerse en una lista. En caso de haber más de una condición, se deben
    Unir por operadores lógicos `'AND'` u `'OR'`. Siendo el operador lógico el que toma la
    primera posición:
    >>> ['&', ('amount', '>', 500), ('name', 'ilike', 'as')]
    >>> # "amount" es mayor a 500 y "name" contiene "as"
    >>> ['|', ('id', '=', 5), ('state', '=', 'posted')]
    >>> # "id" es igual a 5 o "state" es igual a "posted"

    Los operadores lógicos disponibles son:
    - `'&'`: AND
    - `'|'`: OR

    ----
    ### Criterios de búsqueda muy específicos
    También es posible formular criterios de búsqueda más avanzados como el que se muestra a
    continuación:
    >>> search_criteria = [
    >>>     '&',
    >>>         '|',
    >>>             ('partner_id', '=', 14418),
    >>>             ('partner_id', '=', 14417),
    >>>         ('salesperson_id', '=', 213)
    >>> ]
    >>> # "partner_id" es igual a 14418 o "partner_id" es igual a 14417 y a su vez "salesperson_id" es igual a 213.
    
    Si el criterio es demasiado largo, también se puede declarar por fuera. También se puede importar
    el tipo de dato `CriteriaStructure` para facilitar la creación apoyandose con el la herramienta de
    autocompletado del editor de código:
    >>> from app.core._types import CriteriaStructure
    >>> search_criteria: CriteriaStructure = ...
    """

    # Campos no manipulables
    _unmutable_fields = {
        'id',
        'create_date',
        'write_date',
    }

    # Mapas de funciones:
    _sorting_direction = {
        True: asc,
        False: desc,
    }

    def __init__(
        self,
        config_file_name: str,
        database_connection: _DatabaseConnection = "real",
        _dir_sublevels: int = 3
    ):

        # Creación del diccionario de tablas y el engine de SQLAlchemy
        ( self._tables, self._engine ) = self._get_config(
            config_file_name,
            _dir_sublevels,
            database_connection
        )

    def create(
        self,
        table_name: str,
        data: list[dict] | dict
    ) -> bool:
        """
        ## Creación de registros
        Este método realiza la creación de uno o muchos registros a partir del
        nombre de la tabla proporcionado y un diccionario (un único registro) o
        una lista de diccionarios (muchos registros).

        Uso:
        >>> # Para un solo registro
        >>> record = {
        >>>     'user': 'onnymm',
        >>>     'name': 'Onnymm Azzur',
        >>> }
        >>> 
        >>> db.create('users', record)
        >>> #    id    user          name         create_date          write_date
        >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> 
        >>> # Para muchos registros
        >>> records = [
        >>>     {
        >>>         'user': 'onnymm',
        >>>         'name': 'Onnymm Azzur',
        >>>     },
        >>>     {
        >>>         'user': 'lumii',
        >>>         'name': 'Lumii Mynx',
        >>>     },
        >>> ]
        >>> 
        >>> db.create('users', records)
        >>> #    id    user          name         create_date          write_date
        >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> # 1   3   lumii    Lumii Mynx 2024-11-04 11:16:59 2024-11-04 11:16:59

        ----
        ### Nota
        Los campos como `id`, `create_date` y `write_date` son descartados, pues
        éstos son manejados por la base de datos y no son manipulables.
        """

        # Obtención de la instancia de la tabla
        table_instance = self._get_table_instance(table_name)

        # Conversión de datos entrantes si es necesaria
        if isinstance(data, dict):
            data = [data,]

        # Filtro de datos
        filtered_data = []

        for record in data:
            record = self._discard_unmutable_fields(record)
            filtered_data.append(record)

        stmt = (
            insert(table_instance)
            .values(filtered_data)
        )

        # Conexión con la base de datos
        with self._engine.connect() as conn:
            # Ejecución en la base de datos
            conn.execute(stmt)
            # Commit de los cambios
            conn.commit()

        return True

    def search(
        self,
        table_name: str,
        search_criteria: CriteriaStructure = [],
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[int]:
        """
        ## Búsqueda de registros
        Este método retorna todos los registros de una tabla o los registros que cumplan
        con la condición de búsqueda provista, además de segmentar desde un índice
        inicial de desfase y/o un límite de cantidad de registros retornada.

        Uso:
        >>> # Ejemplo 1
        >>> db.search('users')
        >>> # [1, 2, 3, 4, 5]
        >>> 
        >>> # Ejemplo 2
        >>> db.search('commisions', [('user_id', '=', 213)])
        >>> # [7, 9, 12, 13, 17, 21, ...]

        ### Los parámetros de entrada son:
        - `table_name`: Nombre de la tabla de donde se tomarán los registros.
        - `search_criteria`: Criterio de búsqueda para retornar únicamente los resultados que
        cumplan con las condiciones provistas (Consultar estructura más abajo).
        - `offset`: Desfase de inicio de primer registro a mostrar.
        - `limit`: Límite de registros retornados por la base de datos.

        ----
        ### Estructura de criterio de búsqueda
        La estructura del criterio de búsqueda consiste en una lista de tuplas de 3 valores, mejor
        conocidas como tripletas. Cada una de estas tripletas consiste en 3 diferentes parámetros:
        1. Nombre del campo de la tabla
        2. Operador de comparación
        3. Valor de comparación

        Algunos ejemplos de tripletas son:
        >>> ('id', '=', 5)
        >>> # ID es igual a 5
        >>> ('amount', '>', 500)
        >>> # "amount" es mayor a 500
        >>> ('name', 'ilike', 'as')
        >>> # "name" contiene "as"

        Los operadores de comparación disponibles son:
        - `'='`: Igual a
        - `'!='`: Diferente de
        - `'>'`: Mayor a
        - `'>='`: Mayor o igual a
        - `'<`': Menor que
        - `'<='`: Menor o igual que
        - `'><'`: Entre
        - `'in'`: Está en
        - `'not in'`: No está en
        - `'ilike'`: Contiene
        - `'not ilike'`: No contiene

        Estas tuplas deben contenerse en una lista. En caso de haber más de una condición, se deben
        Unir por operadores lógicos `'AND'` u `'OR'`. Siendo el operador lógico el que toma la
        primera posición:
        >>> ['&', ('amount', '>', 500), ('name', 'ilike', 'as')]
        >>> # "amount" es mayor a 500 y "name" contiene "as"
        >>> ['|', ('id', '=', 5), ('state', '=', 'posted')]
        >>> # "id" es igual a 5 o "state" es igual a "posted"

        Los operadores lógicos disponibles son:
        - `'&'`: AND
        - `'|'`: OR

        ----
        ### Criterios de búsqueda muy específicos
        También es posible formular criterios de búsqueda más avanzados como el que se muestra a
        continuación:
        >>> search_criteria = [
        >>>     '&',
        >>>         '|',
        >>>             ('partner_id', '=', 14418),
        >>>             ('partner_id', '=', 14417),
        >>>         ('salesperson_id', '=', 213)
        >>> ]
        >>> # "partner_id" es igual a 14418 o "partner_id" es igual a 14417 y a su vez "salesperson_id" es igual a 213.
        
        Si el criterio es demasiado largo, también se puede declarar por fuera. También se puede importar
        el tipo de dato `CriteriaStructure` para facilitar la creación apoyandose con el la herramienta de
        autocompletado del editor de código:
        >>> from app.core._types import CriteriaStructure
        >>> search_criteria: CriteriaStructure = ...

        ----
        ### Desfase de registros para paginación
        Este parámetro sirve para retornar los registros a partir del índice indicado por éste. Suponiendo que
        una búsqueda normal arrojaría los siguientes resultados:
        >>> db.search('users')
        >>> # [3, 4, 5, 6, 7]

        Se puede especificar que el retorno de los registros considerará solo a partir desde cierto registro, como
        por ejemplo lo siguiente:
        >>> db.search('users', offset= 2)
        >>> # [4, 5, 6, 7]

        ----
        ### Límite de registros retornados para paginación
        También es posible establecer una cantidad máxima de registros desde la base de datos. Suponiendo que una
        búsqueda normal arrojaría los siguientes registros:
        >>> db.search('users')
        >>> # [3, 4, 5, 6, 7]

        Se puede especificar que solo se requiere obtener una cantidad máxima de registros a partir de un
        número provisto:
        >>> db.search('users', limit= 3)
        >>> # [3, 4, 5]
        """

        # Obtención de la instancia de la tabla
        table_instance = self._get_table_instance(table_name)

        # Creación del query base
        stmt = select(table_instance.id)

        # Si hay criterios de búsqueda se genera el 'where'
        if len(search_criteria) > 0:

            # Creación del query where
            where_query = self._where._build_where(table_instance, search_criteria)

            # Conversión del query SQL
            stmt = stmt.where(where_query)

        # Ordenamiento de los datos
        stmt = stmt.order_by(asc(table_instance.id))

        # Segmentación de inicio y fin en caso de haberlos
        if offset != None:
            stmt = stmt.offset(offset)
        if limit != None:
            stmt = stmt.limit(limit)

        # Conexión con la base de datos
        with self._engine.connect() as conn:
            # Obtención de los datos desde PostgreSQL
            response = conn.execute(stmt)

        # Inicialización del DataFrame de retorno
        data = pd.DataFrame(response.fetchall())

        # Se extraen las IDs en caso de existir o una lista vacía
        try:
            return data['id'].to_list()
        except KeyError:
            return []

    def read(
        self,
        table_name: str,
        ids: list[int],
        fields: list[str] = [],
        sortby: str | list[str] = None,
        ascending: bool | list[bool] = True,
        output_format: _OutputFormat = "DataFrame",
    ) -> pd.DataFrame | dict[str, _CommonType]:
        """
        ## Lectura de registros
        Este método retorna un DataFrame con el contenido de los registros de
        una tabla de la base de datos a partir de una lista de IDs, en el orden
        en el que se especificaron los campos o todos los campos en caso de no
        haber sido especificados.

        ### Los parámetros de entrada son:
        - `table_name`: Nombre de la tabla de donde se tomarán los registros.
        - `search_criteria`: Criterio de búsqueda para retornar únicamente los
        resultados que cumplan con las condiciones provistas (Consultar
        estructura más abajo).
        - `fields`: Campos a mostrar. En caso de no ser especificado, se toman todos los
        campos de la tabla de la base de datos.
        - `offset`: Desfase de inicio de primer registro a mostrar.
        - `limit`: Límite de registros retornados por la base de datos.

        Uso:
        >>> # Ejemplo 1
        >>> db.search_read('users', [2])
        >>> #    id    user          name         create_date          write_date
        >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> 
        >>> db.search_read('users', [2, 3])
        >>> #    id    user          name         create_date          write_date
        >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> # 1   3   lumii    Lumii Mynx 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> 
        >>> # Ejemplo 3
        >>> db.search_read('users', [2, 3], ['user', 'create_date'])
        >>> #    id         name         create_date
        >>> # 0   2 Onnymm Azzur 2024-11-04 11:16:59
        >>> # 1   3   Lumii Mynx 2024-11-04 11:16:59
        """

        # Obtención de la instancia de la tabla
        table_instance = self._get_table_instance(table_name)

        # Obtención de los campos de la tabla
        table_fields = self._get_table_fields(table_instance, fields)

        # Creación del query base
        stmt = select(*table_fields)

        # Creación del query where
        where_query = self._where._build_where(table_instance, [('id', 'in', ids)])

        # Conversión del query SQL
        stmt = stmt.where(where_query)

        # Creación de parámetros de ordenamiento
        stmt = self._build_sort(
            stmt,
            table_instance,
            sortby,
            ascending
        )

        # Conexión con la base de datos
        with self._engine.connect() as conn:
            # Obtención de los datos desde PostgreSQL
            response = conn.execute(stmt)

        # Inicialización del DataFrame de retorno
        data = pd.DataFrame(response.fetchall())

        if output_format == "dict":
            return self._convert_to_dicts(data)

        return data

    def search_read(
        self,
        table_name: str,
        search_criteria: CriteriaStructure = [],
        fields: list[str] = [],
        offset: int | None = None,
        limit: int | None = None,
        sortby: str | list[str] = None,
        ascending: bool | list[bool] = True,
        output_format: _OutputFormat = "DataFrame"
    ) -> pd.DataFrame | dict[str, _CommonType]:
        """
        ## Búsqueda y lectura de registros
        Este método retorna un DataFrame con el contenido de los registros de una
        tabla de la base de datos, en el orden en el que se especificaron los campos
        o todos los campos en caso de no haber sido especificados.

        ### Los parámetros de entrada son:
        - `table_name`: Nombre de la tabla de donde se tomarán los registros.
        - `search_criteria`: Criterio de búsqueda para retornar únicamente los resultados que
        cumplan con las condiciones provistas (Consultar estructura más abajo).
        - `fields`: Campos a mostrar. En caso de no ser especificado, se toman todos los
        campos de la tabla de la base de datos.
        - `offset`: Desfase de inicio de primer registro a mostrar.
        - `limit`: Límite de registros retornados por la base de datos.

        Uso:
        >>> # Ejemplo 1
        >>> db.search_read('users')
        >>> #    id    user          name         create_date          write_date
        >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> # 1   3   lumii    Lumii Mynx 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> 
        >>> # Ejemplo 2
        >>> db.search_read('users', [('user', '=', 'onnymm')])
        >>> #    id    user          name         create_date          write_date
        >>> # 0   2  onnymm  Onnymm Azzur 2024-11-04 11:16:59 2024-11-04 11:16:59
        >>> 
        >>> # Ejemplo 3
        >>> db.search_read('users', [], ['user', 'create_date'])
        >>> #    id         name         create_date
        >>> # 0   2 Onnymm Azzur 2024-11-04 11:16:59
        >>> # 1   3   Lumii Mynx 2024-11-04 11:16:59

        ----
        ### Estructura de criterio de búsqueda
        La estructura del criterio de búsqueda consiste en una lista de tuplas de 3 valores, mejor
        conocidas como tripletas. Cada una de estas tripletas consiste en 3 diferentes parámetros:
        1. Nombre del campo de la tabla
        2. Operador de comparación
        3. Valor de comparación

        Algunos ejemplos de tripletas son:
        >>> ('id', '=', 5)
        >>> # ID es igual a 5
        >>> ('amount', '>', 500)
        >>> # "amount" es mayor a 500
        >>> ('name', 'ilike', 'as')
        >>> # "name" contiene "as"

        Los operadores de comparación disponibles son:
        - `'='`: Igual a
        - `'!='`: Diferente de
        - `'>'`: Mayor a
        - `'>='`: Mayor o igual a
        - `'<`': Menor que
        - `'<='`: Menor o igual que
        - `'><'`: Entre
        - `'in'`: Está en
        - `'not in'`: No está en
        - `'ilike'`: Contiene
        - `'not ilike'`: No contiene

        Estas tuplas deben contenerse en una lista. En caso de haber más de una condición, se deben
        Unir por operadores lógicos `'AND'` u `'OR'`. Siendo el operador lógico el que toma la
        primera posición:
        >>> ['&', ('amount', '>', 500), ('name', 'ilike', 'as')]
        >>> # "amount" es mayor a 500 y "name" contiene "as"
        >>> ['|', ('id', '=', 5), ('state', '=', 'posted')]
        >>> # "id" es igual a 5 o "state" es igual a "posted"

        Los operadores lógicos disponibles son:
        - `'&'`: AND
        - `'|'`: OR

        ----
        ### Criterios de búsqueda muy específicos
        También es posible formular criterios de búsqueda más avanzados como el que se muestra a
        continuación:
        >>> search_criteria = [
        >>>     '&',
        >>>         '|',
        >>>             ('partner_id', '=', 14418),
        >>>             ('partner_id', '=', 14417),
        >>>         ('salesperson_id', '=', 213)
        >>> ]
        >>> # "partner_id" es igual a 14418 o "partner_id" es igual a 14417 y a su vez "salesperson_id" es igual a 213.
        
        Si el criterio es demasiado largo, también se puede declarar por fuera. También se puede importar
        el tipo de dato `CriteriaStructure` para facilitar la creación apoyandose con el la herramienta de
        autocompletado del editor de código:
        >>> from app.core._types import CriteriaStructure
        >>> search_criteria: CriteriaStructure = ...

        ----
        ### Desfase de registros para paginación
        Este parámetro sirve para retornar los registros a partir del índice indicado por éste. Suponiendo que
        una búsqueda normal arrojaría los siguientes resultados:
        >>> db.search_read('users')
        >>> #    id     user                  name
        >>> # 0   3   onnymm          Onnymm Azzur
        >>> # 1   4    lumii            Lumii Mynx
        >>> # 2   5  user001  Persona Sin Nombre 1
        >>> # 3   6  user002  Persona Sin Nombre 2
        >>> # 4   7  user003  Persona Sin Nombre 3

        Se puede especificar que el retorno de los registros considerará solo a partir desde cierto registro, como
        por ejemplo lo siguiente:
        >>> db.search_read('users', offset= 2)
        >>> # 1   4    lumii            Lumii Mynx
        >>> # 2   5  user001  Persona Sin Nombre 1
        >>> # 3   6  user002  Persona Sin Nombre 2
        >>> # 4   7  user003  Persona Sin Nombre 3

        ----
        ### Límite de registros retornados para paginación
        También es posible establecer una cantidad máxima de registros desde la base de datos. Suponiendo que una
        búsqueda normal arrojaría los siguientes registros:
        >>> db.search_read('users')
        >>> #    id     user                  name
        >>> # 0   3   onnymm          Onnymm Azzur
        >>> # 1   4    lumii            Lumii Mynx
        >>> # 2   5  user001  Persona Sin Nombre 1
        >>> # 3   6  user002  Persona Sin Nombre 2
        >>> # 4   7  user003  Persona Sin Nombre 3

        Se puede especificar que solo se requiere obtener una cantidad máxima de registros a partir de un
        número provisto:
        >>> db.search_read('users', limit= 3)
        >>> #    id     user                  name
        >>> # 0   3   onnymm          Onnymm Azzur
        >>> # 1   4    lumii            Lumii Mynx
        >>> # 2   5  user001  Persona Sin Nombre 1
        """

        # Obtención de la instancia de la tabla
        table_instance = self._get_table_instance(table_name)

        # Obtención de los campos de la tabla
        table_fields = self._get_table_fields(table_instance, fields)

        # Creación del query base
        stmt = select(*table_fields)

        # Si hay criterios de búsqueda se genera el 'where'
        if len(search_criteria) > 0:

            # Creación del query where
            where_query = self._where._build_where(table_instance, search_criteria)

            # Conversión del query SQL
            stmt = stmt.where(where_query)

        # Creación de parámetros de ordenamiento
        stmt = self._build_sort(
            stmt,
            table_instance,
            sortby,
            ascending
        )

        # Segmentación de inicio y fin en caso de haberlos
        if offset != None:
            stmt = stmt.offset(offset)
        if limit != None:
            stmt = stmt.limit(limit)

        # Conexión con la base de datos
        with self._engine.connect() as conn:
            # Obtención de los datos desde PostgreSQL
            response = conn.execute(stmt)

        data = self._load_data(response.fetchall(), table_instance)

        if output_format == "dict":
            return self._convert_to_dicts(data)

        return data

    def _load_data(self, data: list[dict], table_instance: DeclarativeBase) -> pd.DataFrame:
        """
        Preparación de los datos para su uso.
        """

        # Inicialización del DataFrame
        df = pd.DataFrame(data, dtype= None)

        # Inicialización de diccionario para corrección de tipos de dato
        proper_dtypes = {}

        # Iteración por cada una de las columnas del DataFrame
        for col in df.columns:

            # Obtención del tipo de dato de la columna
            db_type = str(table_instance.__table__.columns[col].type)

            # Si el tipo de dato es entero...
            if db_type == 'INTEGER':
                proper_dtypes[col] = 'Int64'

            # Si el tipo de dato es texto...
            if 'VARCHAR' in str(table_instance.__table__.columns[col].type):
                proper_dtypes[col] = 'string'

        # Si el diccionario contiene tipos por corregir se realiza la corrección
        if len(proper_dtypes):
            df = df.astype(proper_dtypes).replace({pd.NA: None})

        # Retorno del DataFrame
        return df

    def search_count(
        self,
        table_name: str,
        search_criteria: CriteriaStructure = [],
    ) -> int:
        """
        ## Búsqueda y conteo de resultados
        Este método retorna el conteo de de todos los registros de una tabla o los
        registros que cumplan con la condición de búsqueda provista, ideal para funcionalidades
        de paginación que muestran un total de registros.

        Uso:
        >>> # Ejemplo 1
        >>> db.search_count('users')
        >>> # 5
        >>> 
        >>> # Ejemplo 2
        >>> db.search_count('commisions', [('user_id', '=', 213)])
        >>> # 126

        ### Los parámetros de entrada son:
        - `table_name`: Nombre de la tabla de donde se tomarán los registros.
        - `search_criteria`: Criterio de búsqueda para retornar únicamente los resultados que
        cumplan con las condiciones provistas (Consultar estructura más abajo).

        ----
        ### Estructura de criterio de búsqueda
        La estructura del criterio de búsqueda consiste en una lista de tuplas de 3 valores, mejor
        conocidas como tripletas. Cada una de estas tripletas consiste en 3 diferentes parámetros:
        1. Nombre del campo de la tabla
        2. Operador de comparación
        3. Valor de comparación

        Algunos ejemplos de tripletas son:
        >>> ('id', '=', 5)
        >>> # ID es igual a 5
        >>> ('amount', '>', 500)
        >>> # "amount" es mayor a 500
        >>> ('name', 'ilike', 'as')
        >>> # "name" contiene "as"

        Los operadores de comparación disponibles son:
        - `'='`: Igual a
        - `'!='`: Diferente de
        - `'>'`: Mayor a
        - `'>='`: Mayor o igual a
        - `'<`': Menor que
        - `'<='`: Menor o igual que
        - `'><'`: Entre
        - `'in'`: Está en
        - `'not in'`: No está en
        - `'ilike'`: Contiene
        - `'not ilike'`: No contiene

        Estas tuplas deben contenerse en una lista. En caso de haber más de una condición, se deben
        Unir por operadores lógicos `'AND'` u `'OR'`. Siendo el operador lógico el que toma la
        primera posición:
        >>> ['&', ('amount', '>', 500), ('name', 'ilike', 'as')]
        >>> # "amount" es mayor a 500 y "name" contiene "as"
        >>> ['|', ('id', '=', 5), ('state', '=', 'posted')]
        >>> # "id" es igual a 5 o "state" es igual a "posted"

        Los operadores lógicos disponibles son:
        - `'&'`: AND
        - `'|'`: OR

        ----
        ### Criterios de búsqueda muy específicos
        También es posible formular criterios de búsqueda más avanzados como el que se muestra a
        continuación:
        >>> search_criteria = [
        >>>     '&',
        >>>         '|',
        >>>             ('partner_id', '=', 14418),
        >>>             ('partner_id', '=', 14417),
        >>>         ('salesperson_id', '=', 213)
        >>> ]
        >>> # "partner_id" es igual a 14418 o "partner_id" es igual a 14417 y a su vez "salesperson_id" es igual a 213.
        
        Si el criterio es demasiado largo, también se puede declarar por fuera. También se puede importar
        el tipo de dato `CriteriaStructure` para facilitar la creación apoyandose con el la herramienta de
        autocompletado del editor de código:
        >>> from app.core._types import CriteriaStructure
        >>> search_criteria: CriteriaStructure = ...
        """

        # Obtención de la instancia de la tabla
        table_instance = self._get_table_instance(table_name)

        stmt = (
            select( func.count() )
            .select_from(table_instance)
        )

        # Si hay criterios de búsqueda se genera el 'where'
        if len(search_criteria) > 0:

            # Creación del query where
            where_query = self._where._build_where(table_instance, search_criteria)

            # Conversión del query SQL
            stmt = stmt.where(where_query)

        # Conexión con la base de datos
        with self._engine.connect() as conn:
            # Obtención de los datos desde PostgreSQL
            response = conn.execute(stmt)

        # Retorno del conteo de registros
        return response.scalar()

    def update(
        self,
        table_name: str,
        record_ids: int | list[int],
        data: dict[str, _CommonType],
    ) -> bool:
        """
        ## Actualización de registros
        Este método realiza la actualización de uno o más registros a partir de su respectiva
        ID provista, actualizando uno o más campos con el valor provisto. Este método solo
        sobreescribe un mismo valor por cada campo a todos los registros provistos.

        ### Los parámetros de entrada son:
        - `table_name`: Nombre de la tabla en donde se harán los cambios
        - `record_ids`: ID o lista de IDs a actualizar
        - `data`: Diccionario de valores a modificar masivamente

        Uso:
        >>> db.search_read('users', fields= ['user', 'name'])
        >>> #    id     user                  name
        >>> # 0   3   onnymm          Onnymm Azzur
        >>> # 1   4    lumii            Lumii Mynx
        >>> # 2   5  user001  Persona Sin Nombre 1
        >>> # 3   6  user002  Persona Sin Nombre 2
        >>> # 4   7  user003  Persona Sin Nombre 3
        >>> 
        >>> # Modificación
        >>> db.update("users", [3, 4, 5, 6, 7], {'name': 'Cambiado'})
        >>> #    id     user      name
        >>> # 0   3   onnymm  Cambiado
        >>> # 1   4    lumii  Cambiado
        >>> # 2   5  user001  Cambiado
        >>> # 3   6  user002  Cambiado
        >>> # 4   7  user003  Cambiado
        """

        # Obtención de la instancia de la tabla
        table_instance = self._get_table_instance(table_name)

        # Conversión de datos entrantes si es necesaria
        if isinstance(record_ids, int):
            record_ids = [record_ids,]

        stmt =  (
            update(table_instance)
            .where(table_instance.id.in_(record_ids))
            .values(data)
        )

        # Conexión con la base de datos
        with self._engine.connect() as conn:
            # Ejecución en la base de datos
            conn.execute(stmt)
            # Commit de los cambios
            conn.commit()

        return True

    def delete(self, table_name: str, record_ids: int | list[int]) -> bool:
        """
        ## Eliminación de registros
        Este método realiza la eliminación de uno o más registros de la base datos a partir de
        su respectiva ID provista.

        Uso:
        >>> #    id     user                  name
        >>> # 0   3   onnymm          Onnymm Azzur
        >>> # 1   4    lumii            Lumii Mynx
        >>> # 2   5  user001  Persona Sin Nombre 1
        >>> # 3   6  user002  Persona Sin Nombre 2
        >>> # 4   7  user003  Persona Sin Nombre 3
        >>> 
        >>> # Eliminación
        >>> db.delete("users", 3)
        >>> #    id     user                  name
        >>> # 1   4    lumii            Lumii Mynx
        >>> # 2   5  user001  Persona Sin Nombre 1
        >>> # 3   6  user002  Persona Sin Nombre 2
        >>> # 4   7  user003  Persona Sin Nombre 3
        """

        # Obtención de la instancia de la tabla
        table_instance = self._get_table_instance(table_name)

        # Conversión de datos entrantes si es necesaria
        if isinstance(record_ids, int):
            record_ids = [record_ids,]


        stmt =  (
            delete(table_instance)
            .where(table_instance.id.in_(record_ids))
        )

        # Conexión con la base de datos
        with self._engine.connect() as conn:
            # Ejecución en la base de datos
            conn.execute(stmt)
            # Commit de los cambios
            conn.commit()

        return True

    def _build_sort(
        self,
        stmt: Select,
        table_instance: DeclarativeBase,
        sortby: str | list[str],
        ascending: str | list[bool] = True,
    ) -> BinaryExpression:
        """
        ## Construcción de parámetros de ordenamiento
        Este método interno construye los parámetros de ordenamiento por una o
        más columnas de una tabla de manera ascendente o descendente.

        Uso:
        >>> # Ejemplo 1
        >>> stmt = select(...)
        >>> stmt = self._build_sort(stmt, table_instance, "col_1")
        >>> # SELECT ... ORDER BY table.col_1 ASC
        >>> 
        >>> stmt = select(...)
        >>> stmt = self._build_sort(stmt, table_instance, ["col_1", "col_2"], [True, False])
        >>> # SELECT ... ORDER BY table.col_1 ASC, table.col_2 DESC
        """

        # Ordenamiento de los datos
        if sortby is None:
            # Ordenamiento ascendente por IDs
            stmt = stmt.order_by(asc(table_instance.id))

        else:
            # Ordenamiento por una columna
            if isinstance(sortby, str):
                # Creación del query
                stmt = stmt.order_by(
                    # Obtención de función de ordenamiento
                    self._sorting_direction[ascending](
                        # Obtención del campo atributo de la tabla
                        getattr(table_instance, sortby)
                    )
                )

            # Ordenamiento por varias columnas
            elif isinstance(sortby, list):
                # Creación del query
                stmt = stmt.order_by(
                    # Destructuración en [*args] de una compreensión de lista
                    *[
                        # Obtención de función de ordenamiento
                        self._sorting_direction[ascending_i](
                            # Obtención del campo atributo de la tabla
                            getattr(table_instance, sortby_i)
                        )
                        # Destructuración de la columna y dirección de ordenamiento del zip de listas
                        for ( sortby_i, ascending_i ) in zip(
                            sortby, ascending
                        )
                    ]
                )

        # Retorno de la expresión binaria
        return stmt

    def _get_table_fields(
            self, table_instance: DeclarativeBase,
            fields: list[str] = []
    ) -> list[InstrumentedAttribute]:
        """
        ## Obtención de campos de tabla
        Este método obtiene una lista ordenada de los atributos (campos) de la instancia
        de una tabla provista, iniciando por el ID, los campos propios de la tabla y
        finalmente los campos comunes como `create_date` y `write_date`. En caso de ser
        provista una lista de campos en `str` se retorna esta misma lista de instancias
        junto con el campo de ID como primer elemento.

        Nota: El campo de ID de la tabla siempre irá incluido como primer elemento aún cuando no
        sea especificado.
        """
        
        # Inicialización de la lista con el valor de 'id' como primer elemento
        id_field = ['id']
        
        # Obtención de todos los campos 
        if len(fields) == 0:
            # Obtención de los campos propios de la tabla
            instance_fields = list( table_instance.__annotations__.keys() )
            # Obtención de los campos comunes desde la clase heredada (_Base)
            base_fields = list( table_instance.__base__.__annotations__.keys() )
            # Suma de ambas listas para mantener la prioridad a los campos de la tabla
            fields = instance_fields + base_fields

        # Remoción del campo de 'ID' en caso de ser solicitado, para evitar campos duplicados en
        #       el retorno de la información.
        try:
            fields.remove('id')
        except ValueError:
            pass

        # Suma del campo 'ID' como primer elemento de los campos a retornar
        table_fields =  id_field + fields

        # Obtención de los atributos de la tabla a partir de los nombres de los campos,
        #       y retorno en una lista para ser usados en el query correspondiente
        return [ getattr(table_instance, field) for field in table_fields ]

    def _get_table_instance(self, table_name: str) -> DeclarativeBase:
        """
        ## Obtención de la instancia de tabla
        Este método interno obtiene el nombre de la tabla nombrado desde
        la el método que llama a este método.

        Uso:
        >>> table_instance = self._get_table_instance("users")
        >>> # Uso de la instancia...
        >>> stmt = select(table_instance).where(table_instance.id == ...)
        """

        return self._tables[table_name]

    def _discard_unmutable_fields(self, incoming_data: dict) -> dict:
        """
        ## Filtro de valores no modificables
        Este método descarta todos los campos no modificables de los datos
        ingresados desde el backend intencional o accidentalmente.
        """

        # Inicialización de las llaves del registro entrante
        writable_keys = set(incoming_data.keys())
        # Se descartan las llaves en caso de existir
        writable_keys -= self._unmutable_fields

        # Retorno del registro con llaves filtradas
        return { key: incoming_data[key] for key in writable_keys }

    def _get_config(
        self,
        file_name,
        sublevels: int,
        database_connection: Literal["real", "test"] = "real",
    ):
        """
        ## Obtención del archivo de configuración
        Este método interno realiza la búsqueda del archivo de configuración
        en base al nombre que se le dio, buscando en el directorio raíz
        en donde se creó el proyecto que utiliza este módulo.

        Uso:

        Si el archivo de configuración se encuentra en la ruta:

        `C/Users/user_name/Documents/my_proyect/config.json`

        Entonces la ejecución de este método sería:
        >>> self._get_config("config", 3)

        Normalmente este módulo se encuentra 3 subniveles por debajo del
        directorio raíz, así que el parámetro `sublevels` debería recibir el
        valor `3` en casi todos los casos de uso. Para más información,
        consultar la documentación del método interno `_get_root_path` que
        obtiene el directorio raíz a partir del parámetro `sublevels`.
        """

        # Ruta del archivo de configuración
        _root_path = self._get_root_path(sublevels)

        # Nombre del archivo de configuración
        file_path = os.path.join(_root_path, f"{file_name}.json")

        # Obtención de los parámetros de configuración
        with open(file_path) as file:
            config_file = json.load(file)
        
        connection_params = config_file["connections"][database_connection]

        # Obtención de las tablas con nombres
        tables = self._get_table_instances(connection_params)
        engine = self._create_engine(connection_params)

        return ( tables, engine )

    def _get_root_path(self, sublevels: int):
        """
        ## Obtención de la ruta raíz
        Este método interno obtiene la ruta raíz del directorio del proyecto.
        Normalmente este módulo se encuentra 3 subniveles por debajo del
        directorio raíz, así que el parámetro `sublevels` debería recibir el
        valor `3` en casi todos los casos de uso.

        Uso:
        >>> # Si este módulo se se encuentra en
        >>> #   C:\\Users\\user_name\\Documents\\my_proyect\\env\\Lib\\dml_manager
        >>> self._get_root_path(3)
        >>> # C:\\Users\\user_name\\Documents\\my_proyect\\
        """

        # Ruta base
        root_path = os.path.dirname(__file__)

        # Por cada subnivel se obtiene el directorio padre
        if sublevels:
            for _ in range(sublevels):
                root_path = os.path.dirname(root_path)

        # Retorno de la ruta del archivo
        return root_path

    def _get_table_instances(
        self,
        connection_params: _ConnectionParams,
    ) -> dict[str, DeclarativeBase]:
        """
        ## Obtención de las referencias de modelos SQLAlchemy
        Este método interno genera un diccionario con nombres de tabla y su
        respectivo modelo a partir de los nombres de tabla y modelos SQLAlchemy
        provistos en el archivo `.json` de configuración. Para más información,
        consultar la documentación del módulo.
        """

        # Obtención de la ruta de origen de las instancias de la tabla
        import_path = connection_params['path']

        # Importación del módulo
        module = importlib.import_module(import_path)

        # Inicialización del mapa de tablas a retornar
        tables_map = {}

        # Creación del mapa de tablas
        for table_params in connection_params['tables']:
            tables_map[table_params['table_name']] = getattr(module, table_params['table_instance'])

        # retorno del mapa de tablas
        return tables_map

    def _create_engine(self, connection_params: _ConnectionParams):
        """
        ## Creación del motor de conexión a PostgreSQL
        Este método interno crea el motor de conexión entre una base de datos
        de PostgreSQL en base a un diccionario provisto con las llaves:
        - `'host'`: URL de la base de datos de PostgreSQL.
        - `'port'`: Puerto de comunicación.
        - `'name'`: Nombre de la base de datos.
        - `'user'`: Usuario de la base de datos.
        - `'password'`: Contraseña del usuario.
        - `'path'`: Ruta de importación en python
        - `'tables'`: Diccionario de tablas

        Para más información consultar la documentación del módulo.
        """

        # Obtención de los parámetros a utilizar
        host = connection_params['host']
        port = connection_params['port']
        name = connection_params['name']
        user = connection_params['user']
        password = connection_params['password']

        # Creación de la URL de la conexión a la base de datos
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

        # Creación del motor de conexión con la base de datos
        engine = create_engine(url)

        # Retorno del motor de conexión
        return engine

    def _convert_to_dicts(self, data: pd.DataFrame) -> list[dict[str, _CommonType]]:
        """
        ## Conversión de resultados a lista de diccionarios
        Este método interno convierte un DataFrame a lista de diccionarios. Si
        el DataFrame entrante está vacío se retorna una lista vacía.
        """

        if len(data) == 0:
            return []
        
        return (
            list(
                data
                .T
                .to_dict()
                .values()
            )
        )

    class _where():
        """
        ## Subclase interna para construcción de filtros
        Esta subclase empaqueta todos los métodos utilizados en la construcción
        de filtros de búsqueda `WHERE` para consultas SQL, principalmente para
        lectura.

        Uso:
        >>> # Ejemplo 1
        >>> search_criteria = [('invoice_line_id', '=', 5)]
        >>> cls._where.build_read_query('commisions', search_criteria)
        >>> # ... WHERE commisions.invoice_line_id = 5
        >>> 
        >>> # Ejemplo 2
        >>> search_criteria = ['|', ('state', '=', 'posted'), ('state', '=', 'sent')]
        >>> cls._where.build_read_query('commisions', search_criteria)
        >>> # ...WHERE <nombre de la tabla>.state = 'posted' AND <nombre de la tabla>.state = 'sent'

        Los operadores de comparación disponibles a ejecutar son:
        - `'='`: Igual a
        - `'!='`: Diferente de
        - `'>'`: Mayor a
        - `'>='`: Mayor o igual a
        - `'<`': Menor que
        - `'<='`: Menor o igual que
        - `'><'`: Entre
        - `'in'`: Está en
        - `'not in'`: No está en
        - `'ilike'`: Contiene
        - `'not ilike'`: No contiene

        Los operadores lógicos disponibles son:
        - `'&'`: AND
        - `'|'`: OR
        """

        # Operaciones de comparación
        _comparison_operation = {
            '=': lambda table, field, value: getattr(table, field) == value,
            '!=': lambda table, field, value: getattr(table, field) != value,
            '>': lambda table, field, value: getattr(table, field) > value,
            '>=': lambda table, field, value: getattr(table, field) >= value,
            '<': lambda table, field, value: getattr(table, field) < value,
            '<=': lambda table, field, value: getattr(table, field) <= value,
            '><': lambda table, field, value: getattr(table, field).between(value[0], value[1]),
            'in': lambda table, field, value: getattr(table, field).in_(value),
            'not in': lambda table, field, value: getattr(table, field).not_in(value),
            'ilike': lambda table, field, value: getattr(table, field).ilike(value),
            'not ilike': lambda table, field, value: getattr(table, field).notilike(value),
        }
        """
        ## Operación de comparación
        Este mapa de funciones retorna un query SQL que consiste
        en la comparación de una columna de una tabla de la base de datos
        con un valor o una colección de valores.

        ### Los parámetros de entrada son:
        - `table`: Instancia de la tabla de la cual se tomará el nombre de la columna.
        - `field`: Nombre de la columna de la tabla, a evaluar.
        - `value`: Valor o colección de valores con los cuales se va a evaluar la columna. 

        Uso:
        >>> cls._where._comparison_operation['='](commisions, invoice_line_id, 5)
        >>> # ... WHERE commisions.invoice_line_id = 5

        Los operadores de comparación disponibles a ejecutar son:
        - `'='`: Igual a
        - `'!='`: Diferente de
        - `'>'`: Mayor a
        - `'>='`: Mayor o igual a
        - `'<`': Menor que
        - `'<='`: Menor o igual que
        - `'><'`: Entre
        - `'in'`: Está en
        - `'not in'`: No está en
        - `'ilike'`: Contiene
        - `'not ilike'`: No contiene
        """

        # Operaciones lógicas
        _logic_operation = {
            '|': lambda condition_1, condition_2: or_(condition_1, condition_2),
            '&': lambda condition_1, condition_2: and_(condition_1, condition_2),
        }
        """
        ## Operación lógica
        Este mapa de funciones retorna un query SQL que consiste en la
        unión de dos queries SQL unidas por un operador `and` u `or`.

        ### Los parámetros de entrada son:
        - `condition_1`: Query SQL generada por la función `_create_individual_condition`.
        - `condition_2`: Query SQL generada por la función `_create_individual_condition`.

        Uso:
        >>> self._where._logic_operation['|'](
        >>>     _create_individual_condition(('state', '=', 'posted')),
        >>>     _create_individual_condition(('state', '=', 'sent')),
        >>> )
        >>> # ...WHERE <nombre de la tabla>.state = 'posted' AND <nombre de la tabla>.state = 'sent'

        Los operadores lógicos disponibles son:
        - `'&'`: AND
        - `'|'`: OR
        """

        @classmethod
        def _build_where(cls, table: DeclarativeBase, search_criteria: CriteriaStructure) -> BinaryExpression:
            """
            ## Creación de Query SQL de lectura
            Esta función crea un query SQL para leer los datos de la tabla provista,
            que coincidan con los criterios de búsqueda.

            ### Los parámetros de entrada son:
            `table`: Instancia de la tabla de la cual se tomará el nombre de la columna.
            `search_criteria`: Lista de tuplas y Literales `'&'`, `'|'` que contienen los
            criterios de evaluación para lectura de la tabla.

            Uso:
            >>> # Ejemplo 1
            >>> search_criteria = [('invoice_line_id', '=', 5)]
            >>> cls._where.build_read_query('commisions', search_criteria)
            >>> # ... WHERE commisions.invoice_line_id = 5
            >>> 
            >>> # Ejemplo 2
            >>> search_criteria = ['|', ('state', '=', 'posted'), ('state', '=', 'sent')]
            >>> cls._where.build_read_query('commisions', search_criteria)
            >>> # ...WHERE <nombre de la tabla>.state = 'posted' AND <nombre de la tabla>.state = 'sent'

            Los operadores de comparación disponibles a ejecutar son:
            - `'='`: Igual a
            - `'!='`: Diferente de
            - `'>'`: Mayor a
            - `'>='`: Mayor o igual a
            - `'<`': Menor que
            - `'<='`: Menor o igual que
            - `'><'`: Entre
            - `'in'`: Está en
            - `'not in'`: No está en
            - `'ilike'`: Contiene
            - `'not ilike'`: No contiene

            Los operadores lógicos disponibles son:
            - `'&'`: AND
            - `'|'`: OR
            """

            # Si el criterio de búsqueda sólo contiene una tripleta 
            if len(search_criteria) == 1:
                # Destructuración de la tripleta
                [ triplet ] = search_criteria
                # Creación de query de condición individual
                return cls._create_individual_query(table, triplet)

            # Iteración
            for i in range( len(search_criteria) ):
                # Creación de condiciones individuales para facilitar su lectura
                istriplet_1 = cls._is_triplet(search_criteria[i])
                istriplet_2 = cls._is_triplet(search_criteria[i + 1])
                istriplet_3 = cls._is_triplet(search_criteria[i + 2])

                # Si sólo el primer valor es un operador lógico y los siguientes dos  son tripletas
                if not istriplet_1 and istriplet_2 and istriplet_3:
                    # Destructuración de los valores
                    ( op, condition_1, condition_2) = search_criteria[i: i + 3]

                    # Retorno de la unión de las dos condiciones
                    return cls._merge_queries(
                        op,
                        cls._create_individual_query(table, condition_1),
                        cls._create_individual_query(table, condition_2)
                    )
                
                # Si uno de los dos siguientes valores no es tripleta se tiene que generar una
                #   condición compleja, en dos diferentes escenarios:
                else:
                    # Obtención del operador lógico
                    op = search_criteria[i]

                    # Si el primero de los dos siguientes valores es tripleta
                    if istriplet_2:
                        # Unión de condiciones
                        return cls._merge_queries(
                            op,
                            # Se convierte el primer siguiente valor en query SQL
                            cls._create_individual_query(table, search_criteria[i + 1]),
                            # Se ejecuta esta función recursivamente para la evaluación del resto
                            #   de los valores del criterio de búsqueda
                            cls.build_where(table, search_criteria[i + 2:])
                        )

                    # Si el segundo de los dos siguientes valores es tripleta
                    else:
                        # Unión de dos condiciones
                        return cls._merge_queries(
                            op,
                            # Se ejecuta esta función recursivamente para la evaluación del
                            #   criterio de búsqueda a partir del siguiente primer valor hasta
                            #   el penúltimo valor del criterio de búsqueda
                            cls._build_where(table, search_criteria[i + 1: -1]),
                            # Se convierte el último valor del criterio de búsqueda en query SQL
                            cls._create_individual_query(table, search_criteria[-1])
                        )

        @classmethod
        def _merge_queries(cls, op: _LogicOperator, condition_1: BinaryExpression, condition_2: BinaryExpression) -> BinaryExpression:
            """
            ## Unión de dos queries SQL
            Esta función retorna un query SQL que consiste en la unión de dos queries
            SQL unidas por un operador `and` u `or`.

            ### Los parámetros de entrada son:
            - `op`: Operador lógico para unir los queries (Consultar los operadores lógicos
            disponibles más abajo).
            - `condition_1`: Query SQL generada por la función `_create_individual_condition`.
            - `condition_2`: Query SQL generada por la función `_create_individual_condition`.

            Uso:
            >>> _merge_conditions(
            >>>     '|',
            >>>     _create_individual_condition(('state', '=', 'posted')),
            >>>     _create_individual_condition(('state', '=', 'sent')),
            >>> )
            >>> # ...WHERE <nombre de la tabla>.state = 'posted' AND <nombre de la tabla>.state = 'sent'

            Los operadores lógicos disponibles son:
            - `'&'`: AND
            - `'|'`: OR
            """

            # Retorno de la unión de los dos queries
            return cls._logic_operation[op](condition_1, condition_2)

        @classmethod
        def _create_individual_query(cls, table: DeclarativeBase, fragment: _TripletStructure) -> BinaryExpression:
            """
            ## Función de creación de query SQL individual
            Esta función crea un query SQL que consiste en la comparación de
            una columna de una tabla de la base de datos con un valor o una
            colección de valores.

            ### Los parámetros de entrada son:
            - `table`: Instancia de la tabla de la cual se tomará el nombre de la columna.
            - `fragment`: Tripleta en formato de tupla, que contiene los siguientes valores:
                1. Nombre de la columna de la tabla, a evaluar.
                2. Operador de comparación (Consultar los operadores de comparación disponibles
                más abajo).
                3. Valor o colección de valores con los cuales se va a evaluar la columna.

            Uso:
            >>> fragment = ('invoice_line_id', '=', 5)
            >>> cls._where._create_individual_condition(commisions, fragment)
            >>> # ... WHERE commisions.invoice_line_id = 5

            Los operadores de comparación disponibles a ejecutar son:
            - `'='`: Igual a
            - `'!='`: Diferente de
            - `'>'`: Mayor a
            - `'>='`: Mayor o igual a
            - `'<`': Menor que
            - `'<='`: Menor o igual que
            - `'><'`: Entre
            - `'in'`: Está en
            - `'not in'`: No está en
            - `'ilike'`: Contiene
            - `'not ilike'`: No contiene
            """
            # Destructuración de valores
            ( field, op, value ) = fragment

            # Retorno de la evaluación
            return cls._comparison_operation[op](table, field, value)

        @classmethod
        def _is_triplet(cls, value) -> bool:
            """
            ## Evaluación de posible tripleta de condición
            Esta función evalúa si el valor provisto es una tupla o una lista de
            3 valores que puede ser convertida a un query SQL.
            """
            return (
                    isinstance(value, tuple) or isinstance(value, list)
                and 
                    len(value) == 3
            )