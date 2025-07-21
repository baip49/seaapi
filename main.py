from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pyodbc
from pydantic import BaseModel
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from db import connect
from pydantic import field_validator, ConfigDict
import fastapi_swagger_dark as fsd
from fastapi import APIRouter

api = FastAPI()
api = FastAPI(docs_url=None)
router = APIRouter()
fsd.install(router)
api.include_router(router)

api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

conexion = connect()

# Obtener todos los alumnos
@api.get("/alumnos")
def leer_alumnos():
    cursor = conexion.cursor()
    try:
        rows = cursor.execute("exec ObtenerAlumnos").fetchall()
        if not rows:
            return {"error": "No se encontraron alumnos"}
        
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return {"error": f"Ocurrió un error: {e}"}

# Obtener los datos del alumno con matrícula (en la nueva base de datos)
@api.get("/alumnos/{matricula}")
def leer_alumno(matricula: str):
    cursor = conexion.cursor()
    try:
        row = cursor.execute("exec AlumnoConMatricula ?", matricula).fetchone()
        if row is None:
            return {"error": "Alumno no encontrado"}
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    except Exception as e:
        return {"error": f"Ocurrió un error: {e}"}

# Obtener los datos del alumno con CURP o matrícula (en la base de datos SIA)
@api.get("/alumnos/matricula/{matricula}")
def buscar_por_matricula(matricula: str):
    conexion = connect()
    cursor = conexion.cursor()
    try:
        cursor.execute("EXEC AlumnoConCurpOMatricula @Matricula = ?, @CURP = NULL", matricula)
        row = cursor.fetchone()
        
        if row is None:
            return {"error": "Alumno no encontrado con esa matrícula"}
            
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
        
    except pyodbc.Error as e:
        return {"error": f"Error al consultar el alumno: {e}"}
    finally:
        cursor.close()
        conexion.close()
@api.get("/alumnos/curp/{curp}")
def buscar_por_curp(curp: str):
    conexion = connect()
    cursor = conexion.cursor()
    try:
        cursor.execute("EXEC AlumnoConCurpOMatricula @Matricula = NULL, @CURP = ?", curp)
        row = cursor.fetchone()
        
        if row is None:
            return {"error": "Alumno no encontrado con esa CURP"}
            
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
        
    except pyodbc.Error as e:
        return {"error": f"Error al consultar el alumno: {e}"}
    finally:
        cursor.close()
        conexion.close()

# Crear un nuevo alumno
class InsertarAlumno(BaseModel):
    IdAlumno: None
    CURP: str = Field(max_length=18, min_length=18)
    Matricula: Optional[str] = Field(default=None, max_length=15, min_length=15)
    Nombre: str = Field(max_length=80)
    ApellidoPaterno: str = Field(max_length=50)
    ApellidoMaterno: str = Field(max_length=50)
    FechaNacimiento: date
    Sexo: str = Field(max_length=1, min_length=1, pattern="^[MFP]$")
    Telefono: str = Field(max_length=15, min_length=10, pattern=r"^\d+$")
    Correo: str = Field(default="cesar@cobach.mx", max_length=80, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    IdSede: int = Field(gt=0, lt=5)
    EstadoCivil: str = Field(max_length=1, min_length=1, pattern="^(S|C|D|V)$")
    IdNacionalidad: int = Field(gt=0, lt=5)
    HablaLengua: bool
    IdLengua: int = Field(gt=0, lt=68)
    TieneBeca: bool
    QueBeca: Optional[str] = Field(default=None, max_length=50)
    HijoDeTrabajador: bool
    IdCapturo: None
    FechaTramite: Optional[date] = None
    FechaCaptura: Optional[datetime] = None
    IdRol: Optional[int] = None
    TieneAlergias: bool
    Alergias: Optional[str] = Field(default=None, max_length=200)
    TipoSangre: str = Field(max_length=2, pattern="^(A|B|AB|O)[+-]$")
    TieneDiscapacidad: bool
    Discapacidad: Optional[str] = Field(default=None, max_length=200)
    NombreTutor: Optional[str] = Field(default=None, max_length=80)
    ApellidoPaternoTutor: Optional[str] = Field(default=None, max_length=50)
    ApellidoMaternoTutor: Optional[str] = Field(default=None, max_length=50)
    TelefonoTutor: Optional[str] = Field(default=None, max_length=15, min_length=10, pattern=r"^\d+$")
    CodigoPostal: str = Field(max_length=10, min_length=5, pattern=r"^\d{5,10}$")
    Calle: str = Field(max_length=100)
    EntreCalles: Optional[str] = Field(default=None, max_length=100)
    NumeroExterior: str = Field(max_length=10, min_length=1, pattern=r"^\d+$")
    NumeroInterior: Optional[str] = Field(default=None, max_length=10, min_length=1, pattern=r"^\d+$")
    IdLocalidad: str = Field(default="B0572553-592A-4A46-B730-000022504801")
@api.post("/alumnos/insertar")
def insertar_alumno(alumno: InsertarAlumno):
    cursor = conexion.cursor()
    
    datos = (
        alumno.IdAlumno,
        alumno.CURP,
        alumno.Matricula,
        alumno.Nombre,
        alumno.ApellidoPaterno,
        alumno.ApellidoMaterno,
        alumno.FechaNacimiento,
        alumno.Sexo,
        alumno.Telefono,
        alumno.Correo,
        alumno.IdSede,
        alumno.EstadoCivil,
        alumno.IdNacionalidad,
        alumno.HablaLengua,
        alumno.IdLengua,
        alumno.TieneBeca,
        alumno.QueBeca,
        alumno.HijoDeTrabajador,
        alumno.IdCapturo,
        alumno.FechaTramite,
        alumno.FechaCaptura,
        alumno.IdRol,
        alumno.TieneAlergias,
        alumno.Alergias,
        alumno.TipoSangre,
        alumno.TieneDiscapacidad,
        alumno.Discapacidad,
        alumno.NombreTutor,
        alumno.ApellidoPaternoTutor,
        alumno.ApellidoMaternoTutor,
        alumno.TelefonoTutor,
        alumno.CodigoPostal,
        alumno.Calle,
        alumno.EntreCalles,
        alumno.NumeroExterior,
        alumno.NumeroInterior,
        alumno.IdLocalidad
    )
    try:
        cursor.execute(
            "exec InsertarAlumno ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?",
            *datos
        )
        result = cursor.fetchone()
        conexion.commit()
        
        if result:
            columns = [column[0] for column in cursor.description]
            result_dict = dict(zip(columns, result))
            return {"data": result_dict}
        
        return {"message": "Alumno insertado correctamente"}

    except pyodbc.Error as e:
        print(f"Error de base de datos: {e}")
        conexion.rollback()
        return {"error": f"Error al crear el alumno: {e}"}
    finally:
        cursor.close()
        conexion.close()

# Actualizar un alumno
# Modelo para actualizar un alumno
class ActualizarAlumno(BaseModel):
    id: str
    curp: str = Field(max_length=18, min_length=18)
    matricula: Optional[str] = Field(default=None, max_length=15)
    nombre: str = Field(max_length=80)
    apellidoPaterno: str = Field(max_length=50)
    apellidoMaterno: str = Field(max_length=50)
    fechaNacimiento: date
    sexo: str = Field(max_length=1, min_length=1, pattern="^[HM]$")
    telefono: str = Field(max_length=15, min_length=10, pattern=r"^\d+$")
    correo: str = Field(max_length=80, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    idSede: int = Field(gt=0, lt=5)
    estadoCivil: str = Field(max_length=20)
    idNacionalidad: int = Field(gt=0, lt=5)  # Corregido: removido max_length
    hablaLengua: int = Field(ge=0, le=1)
    idLengua: Optional[int] = Field(gt=0, lt=68)
    tieneBeca: int = Field(ge=0, le=1)
    queBeca: Optional[str] = Field(default=None, max_length=50)
    hijoDeTrabjador: str = Field(max_length=5, pattern="^(true|false)$")
    idCapturo: str
    fechaTramite: date
    fechaCaptura: date
    idRol: int
    tieneAlergias: int = Field(ge=0, le=1)
    alergias: Optional[str] = Field(default=None, max_length=20)
    tipoSangre: str = Field(max_length=3, pattern="^(A|B|AB|O)[+-]$")
    tieneDiscapacidad: int = Field(ge=0, le=1)
    discapacidad: Optional[str] = Field(default=None, max_length=200)
    nombreTutor: Optional[str] = Field(default=None, max_length=80)
    apellidoPaternoTutor: Optional[str] = Field(default=None, max_length=50)
    apellidoMaternoTutor: Optional[str] = Field(default=None, max_length=50)
    telefonoTutor: Optional[str] = Field(default=None, max_length=15)  # Removido min_length y pattern porque es Optional
    codigoPostal: str = Field(max_length=10, min_length=5, pattern=r"^\d{5,10}$")
    calle: str = Field(max_length=100)
    entreCalles: Optional[str] = Field(default=None, max_length=100)
    numeroExterior: str = Field(max_length=10, min_length=1, pattern=r"^\d+$")
    numeroInterior: Optional[str] = Field(default=None, max_length=10)
    idLocalidad: str = Field(default="B0572553-592A-4A46-B730-000022504801")

@api.put("/alumnos/actualizar")
def actualizar_alumno(alumno: ActualizarAlumno):
    conexion = connect()
    cursor = conexion.cursor()
    
    # Convertir valores int a boolean donde sea necesario
    habla_lengua_bool = alumno.hablaLengua == 1
    tiene_beca_bool = alumno.tieneBeca == 1
    hijo_trabajador_bool = alumno.hijoDeTrabjador.lower() == "true"
    tiene_alergias_bool = alumno.tieneAlergias == 1
    tiene_discapacidad_bool = alumno.tieneDiscapacidad == 1
    
    # Manejar campos vacíos
    discapacidad_valor = alumno.discapacidad if alumno.discapacidad and alumno.discapacidad.strip() else None
    
    # Manejar campos de tutor vacíos
    nombre_tutor_valor = alumno.nombreTutor if alumno.nombreTutor and alumno.nombreTutor.strip() else None
    apellido_paterno_tutor_valor = alumno.apellidoPaternoTutor if alumno.apellidoPaternoTutor and alumno.apellidoPaternoTutor.strip() else None
    apellido_materno_tutor_valor = alumno.apellidoMaternoTutor if alumno.apellidoMaternoTutor and alumno.apellidoMaternoTutor.strip() else None
    telefono_tutor_valor = alumno.telefonoTutor if alumno.telefonoTutor and alumno.telefonoTutor.strip() else None
    
    # Convertir fechas a formato datetime.date si vienen como strings
    from datetime import datetime
    if isinstance(alumno.fechaNacimiento, str):
        fecha_nacimiento = datetime.strptime(alumno.fechaNacimiento, '%Y-%m-%d').date()
    else:
        fecha_nacimiento = alumno.fechaNacimiento
    
    if isinstance(alumno.fechaTramite, str):
        fecha_tramite = datetime.strptime(alumno.fechaTramite, '%Y-%m-%d').date()
    else:
        fecha_tramite = alumno.fechaTramite
    
    if isinstance(alumno.fechaCaptura, str):
        fecha_captura = datetime.strptime(alumno.fechaCaptura, '%Y-%m-%d')
    else:
        fecha_captura = alumno.fechaCaptura
    
    # 37 parámetros según el stored procedure
    datos = (
        alumno.id,                          # @IdAlumno
        alumno.curp,                        # @CURP
        alumno.matricula,                   # @Matricula
        alumno.nombre,                      # @Nombre
        alumno.apellidoPaterno,             # @ApellidoPaterno
        alumno.apellidoMaterno,             # @ApellidoMaterno
        fecha_nacimiento,                   # @FechaNacimiento
        alumno.sexo,                        # @Sexo
        alumno.telefono,                    # @Telefono
        alumno.correo,                      # @Correo
        alumno.idSede,                      # @IdSede
        alumno.estadoCivil,                 # @EstadoCivil
        alumno.idNacionalidad,              # @IdNacionalidad
        habla_lengua_bool,                  # @HablaLengua
        alumno.idLengua,                    # @IdLengua
        tiene_beca_bool,                    # @TieneBeca
        alumno.queBeca,                     # @QueBeca
        hijo_trabajador_bool,               # @HijoDeTrabajador
        alumno.idCapturo,                   # @IdCapturo
        fecha_tramite,                      # @FechaTramite
        fecha_captura,                      # @FechaCaptura
        alumno.idRol,                       # @IdRol
        tiene_alergias_bool,                # @TieneAlergias
        alumno.alergias,                    # @Alergias
        alumno.tipoSangre,                  # @TipoSangre
        tiene_discapacidad_bool,            # @TieneDiscapacidad
        discapacidad_valor,                 # @Discapacidad
        nombre_tutor_valor,                 # @NombreTutor
        apellido_paterno_tutor_valor,       # @ApellidoPaternoTutor
        apellido_materno_tutor_valor,       # @ApellidoMaternoTutor
        telefono_tutor_valor,               # @TelefonoTutor
        alumno.codigoPostal,                # @CodigoPostal
        alumno.calle,                       # @Calle
        alumno.entreCalles,                 # @EntreCalles
        alumno.numeroExterior,              # @NumeroExterior
        alumno.numeroInterior if alumno.numeroInterior and alumno.numeroInterior.strip() else None,  # @NumeroInterior
        alumno.idLocalidad                  # @IdLocalidad
    )
    
    try:
        cursor.execute(
            "exec dbo.ActualizarAlumno ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?",
            *datos
        )
        result = cursor.fetchone()
        conexion.commit()
        
        if result:
            columns = [column[0] for column in cursor.description]
            result_dict = dict(zip(columns, result))
            return {"data": result_dict, "message": "Alumno actualizado correctamente"}
        
        return {"message": "Alumno actualizado correctamente"}

    except pyodbc.Error as e:
        print(f"Error de base de datos: {e}")
        conexion.rollback()
        return {"error": f"Error al actualizar el alumno: {e}"}
    finally:
        cursor.close()
        conexion.close()
        
# Obtener lengua ingresada
@api.get("/lenguas/{lengua}")
def obtener_lenguas(lengua: str):
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM Catalogos.Lenguas WHERE Nombre LIKE ?", f"%{lengua}%")
        rows = cursor.fetchall()
        
        if not rows:
            return {"error": "No se encontraron lenguas"}
        
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except pyodbc.Error as e:
        return {"error": f"Error al consultar las lenguas: {e}"}
       
# Obtener lengua por id
@api.get("/lenguas/id/{id_lengua}")
def obtener_lengua_por_id(id_lengua: int):
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM Catalogos.Lenguas WHERE Id = ?", id_lengua)
        row = cursor.fetchone()
        
        if row is None:
            return {"error": "Lengua no encontrada"}
        
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    except pyodbc.Error as e:
        return {"error": f"Error al consultar la lengua: {e}"}

# Obtener localidades
@api.get("/localidades/{localidad}")
def obtener_localidad(localidad: str):
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM SIA.Catalogos.Localidades WHERE NombreLocalidad LIKE ?", f"%{localidad}%")
        rows = cursor.fetchall()
        
        if not rows:
            return {"error": "No se encontraron localidades"}
        
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except pyodbc.Error as e:
        return {"error": f"Error al consultar las localidades: {e}"}

# Obtener sangre
@api.get("/sangre")
def obtener_sangre():
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM SIA.Catalogos.TiposSangres")
        rows = cursor.fetchall()
        
        if not rows:
            return {"error": "No se encontraron tipos de sangre"}
        
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    except pyodbc.Error as e:
        return {"error": f"Error al consultar los tipos de sangre: {e}"}