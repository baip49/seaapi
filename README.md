# SEA - Sistema de Enseñanza Abierta (COBACH)

API REST desarrollada con **FastAPI** para el sistema de registro y gestión de expedientes de alumnos del Colegio de Bachilleres de Chiapas. Proporciona endpoints para la consulta, creación y actualización de información de estudiantes, así como la gestión de documentos y catálogos.

> Desarrollado por César Sánchez ([@baip49](https://github.com/baip49) en GitHub)

## 🎯 Propósito del Proyecto

La API SEA facilita el registro de alumnos mediante:

-   **Búsqueda inteligente** por CURP o matrícula en bases de datos existentes
-   **Validación automática** de documentos PDF requeridos
-   **Gestión de catálogos** de localidades, lenguas indígenas y tipos de sangre
-   **Almacenamiento seguro** de documentos con nombres únicos UUID

## 🏗️ Arquitectura y Tecnologías

### Backend

-   **FastAPI** (Python) - Framework web moderno y rápido
-   **pyodbc** - Conexión a SQL Server
-   **Pydantic** - Validación de datos y serialización
-   **python-dotenv** - Gestión de variables de entorno

### Base de Datos

-   **SQL Server** con procedimientos almacenados
-   **Esquemas**: SIA y Catalogos
-   **Tablas temporales** para manejo de documentos

### ¿Por qué FastAPI?

_"Decidí usar FastAPI ya que vi que es lo que usan para COBACH API, viendo que el diseño era similar, y en base a mis conocimientos en Python, era lo más sencillo de implementar."_

## 🚀 Instalación y Configuración

### Prerrequisitos

-   Python 3.8 o superior
-   SQL Server con ODBC Driver 17
-   Variables de entorno configuradas

### Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/usuario/sea-api.git
cd sea-api
```

2. **Instalar dependencias**

```bash
pip install fastapi uvicorn pyodbc python-dotenv
```

3. **Configurar variables de entorno**
   Crear archivo `.env`:

```env
SERVER=servidor_sql_server
DATABASE=nombre_base_datos
USER=usuario_db
PASSWORD=contraseña_db
```

4. **Ejecutar la API**

```bash
uvicorn main:api --reload --host 127.0.0.1 --port 8000
```

La API estará disponible en `http://127.0.0.1:8000`

## 📋 Endpoints Principales

### 🎓 Gestión de Alumnos

#### **GET /alumnos**

Obtiene todos los alumnos registrados.

**Respuesta:**

```json
[
    {
        "id": "uuid",
        "curp": "CURP18CARACTERES",
        "matricula": "123456789123456",
        "nombre": "Juan",
        "apellidoPaterno": "Pérez",
        "v": "..."
    }
]
```

#### **GET /alumnos/{matricula}**

Busca un alumno específico por matrícula en la nueva base de datos.

**Parámetros:**

-   `matricula` (string): Matrícula del alumno

**Implementación:** Ejecuta el procedimiento almacenado `AlumnoConMatricula`

#### **GET /alumnos/matricula/{matricula}**

Busca alumno por matrícula en el sistema SIA (base de datos legacy).

**Uso:** Para alumnos con matrícula existente que desean actualizar su información.

#### **GET /alumnos/curp/{curp}**

Busca alumno por CURP en el sistema SIA.

**Parámetros:**

-   `curp` (string): CURP de 18 caracteres

**Implementación:** Utiliza el procedimiento `AlumnoConCurpOMatricula`

#### **POST /alumnos/insertar**

Crea un nuevo registro de alumno con documentos.

**Características:**

-   **Multipart form**: Acepta datos del formulario + archivos PDF
-   **Validación UUID**: Genera nombres únicos para documentos
-   **Transacciones**: Rollback automático en caso de error
-   **Tabla temporal**: Para gestión de documentos durante la inserción

**Campos principales:**

```python
curp: str                    # CURP de 18 caracteres
nombre: str                  # Nombre del alumno
apellidoPaterno: str         # Apellido paterno
fechaNacimiento: str         # Formato YYYY-MM-DD
idRol: int                   # Tipo de estudiante (1|2|3)
documentos: List[UploadFile] # Archivos PDF requeridos
```

**Proceso de inserción:**

1. Validar archivos PDF
2. Crear tabla temporal `#TempDocumentos`
3. Generar UUIDs para nombres de archivo
4. Guardar archivos en `uploads/documentos`
5. Ejecutar procedimiento `InsertarAlumno`
6. Commit o rollback según resultado

#### **PUT /alumnos/actualizar**

Actualiza información de alumno existente.

**Diferencias con POST:**

-   Documentos opcionales (parámetro `documentos: Optional[List[UploadFile]]`)
-   Preserva documentos existentes si no se proporcionan nuevos
-   Utiliza procedimiento `ActualizarAlumno`

### 📚 Catálogos y Búsquedas

#### **GET /lenguas/{lengua}**

Búsqueda de lenguas indígenas por nombre.

**Uso:** Autocompletado en formulario cuando el alumno indica que habla lengua indígena.

**Query SQL:**

```sql
SELECT * FROM Catalogos.Lenguas WHERE Nombre LIKE %{lengua}%
```

#### **GET /lenguas/id/{id_lengua}**

Obtiene información específica de una lengua por ID.

#### **GET /localidades/{localidad}**

Búsqueda de localidades por nombre.

**Tabla:** `SIA.Catalogos.Localidades`
**Uso:** Selección de lugar de nacimiento/residencia

#### **GET /sangre**

Catálogo completo de tipos de sangre.

**Respuesta:**

```json
[
    { "id": 1, "tipo": "A+" },
    { "id": 2, "tipo": "A-" },
    { "id": 3, "tipo": "B+" }
]
```

## 🗄️ Modelos de Datos

### **DocumentoInfo** (BaseModel)

```python
class DocumentoInfo(BaseModel):
    nombre_archivo: str      # Nombre original del archivo
    ruta_archivo: str        # Ruta completa en el servidor
    tamano_archivo: int      # Tamaño en bytes
    fecha_subida: datetime   # Timestamp de carga
```

### **ActualizarAlumno** (BaseModel)

Modelo con validaciones Pydantic para actualización:

**Validaciones principales:**

```python
curp: str = Field(max_length=18, min_length=18)
sexo: str = Field(pattern="^[HM]$")
telefono: str = Field(pattern=r"^\d+$")
correo: str = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
tipoSangre: str = Field(pattern="^(A|B|AB|O)[+-]$")
```

## 🔧 Conexión a Base de Datos

### **Función `connect()`**

Establece conexión con SQL Server usando pyodbc:

```python
def connect():
    dotenv.load_dotenv()
    conexion = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('SERVER')};"
        f"DATABASE={os.getenv('DATABASE')};"
        f"UID={os.getenv('USER')};"
        f"PWD={os.getenv('PASSWORD')};"
    )
    return conexion
```

**Características:**

-   **Variables de entorno**: Configuración segura desde `.env`
-   **Connection pooling**: Una conexión global reutilizable
-   **Error handling**: Manejo de excepciones pyodbc

## 📄 Gestión de Documentos

### Estructura de Almacenamiento

```
uploads/
└── documentos/
    ├── 1d80767c-628c-4864-bf46-bb94072a1154.pdf
    ├── 34b0e912-b3e2-46fc-9680-3565c4dec5b7.pdf
    └── ...
```

### Proceso de Carga

1. **Validación**: Solo archivos PDF permitidos
2. **UUID**: Generación de nombre único con `uuid.uuid4()`
3. **Almacenamiento**: Guardado en `uploads/documentos`
4. **Base de datos**: Registro en tabla temporal para procesamiento

### Manejo de Errores

```python
try:
    # Procesamiento de archivos
    pass
except Exception as e:
    # Rollback de transacción
    conexion.rollback()
    # Limpieza de archivos subidos
    for documento_info in documentos_info:
        if os.path.exists(documento_info['ruta_archivo']):
            os.remove(documento_info['ruta_archivo'])
```

## 🛡️ Seguridad y Configuración

### CORS

Configurado para permitir conexiones desde el frontend Angular:

```python
api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",    # Angular development
        "http://127.0.0.1:4200",
        "http://localhost:8000",    # API self
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
```

### Documentación Automática

-   **Swagger UI**: Disponible en `/docs` (con tema oscuro via `fastapi_swagger_dark`)
-   **ReDoc**: Disponible en `/redoc`

## 🚢 Despliegue

### Desarrollo

```bash
fastapi dev main.py
```

## 📊 Procedimientos Almacenados

La API interactúa con varios procedimientos almacenados en SQL Server:

-   **`ObtenerAlumnos`**: Lista todos los alumnos
-   **`AlumnoConMatricula`**: Busca por matrícula en BD nueva
-   **`AlumnoConCurpOMatricula`**: Busca en sistema SIA legacy
-   **`InsertarAlumno`**: Crea nuevo registro completo
-   **`ActualizarAlumno`**: Modifica registro existente

## 🧪 Testing

### Pruebas Manuales

Usar la interfaz Swagger en `http://127.0.0.1:8000/docs`

### Pruebas Automatizadas (Pendiente)

```bash
# Instalar pytest
pip install pytest httpx

# Ejecutar tests
pytest tests/
```

## 🗂️ Estructura del Proyecto

```
api/
├── main.py              # Aplicación FastAPI principal
├── db.py                # Configuración de base de datos
├── .env                 # Variables de entorno (no versionado)
├── .gitignore           # Archivos ignorados por Git
├── README.md            # Este archivo
├── uploads/             # Almacenamiento de documentos
│   └── documentos/      # PDFs subidos por usuarios
└── __pycache__/         # Cache de Python
```

## 📝 Roadmap

### Funcionalidades Pendientes

-   [ ] **Autenticación JWT**: Sistema de tokens para seguridad
-   [ ] **Rate Limiting**: Limitación de requests por IP
-   [ ] **Logging**: Sistema de logs estructurado
-   [ ] **Backup automático**: Respaldo de documentos subidos
-   [ ] **Compresión**: Optimización de archivos PDF

### Mejoras Técnicas

-   [ ] **Tests unitarios**: Cobertura completa con pytest
-   [ ] **CI/CD**: Pipeline de despliegue automático
-   [ ] **Monitoring**: Métricas de rendimiento
-   [ ] **Docker**: Containerización completa

### Comandos de Desarrollo

```bash
# Formatear código
black main.py db.py

# Linter
flake8 .

# Verificar tipos
mypy main.py
```

## 📞 Soporte

Para reportar bugs o solicitar nuevas funcionalidades, contactar al equipo de desarrollo de COBACH Chiapas.

**Endpoints de prueba disponibles en:** `http://127.0.0.1:8000/docs` (esto es cuando el servidor se encuentra servido)

---

*Desarrollado con ❤️ para el Colegio de Bachilleres de Chiapas*