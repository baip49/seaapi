from typing import Union
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pyodbc
from pydantic import BaseModel
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from db import connect
from pydantic import field_validator, ConfigDict
import fastapi_swagger_dark as fsd
from fastapi import APIRouter
import os
import uuid

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

class DocumentoInfo(BaseModel):
    nombre_archivo: str
    ruta_archivo: str
    tamano_archivo: int
    fecha_subida: datetime

@api.post("/alumnos/insertar")
async def insertar_alumno(
    id: Optional[str] = Form(None),
    curp: str = Form(...),
    matricula: Optional[str] = Form(None),
    nombre: str = Form(...),
    apellidoPaterno: str = Form(...),
    apellidoMaterno: str = Form(...),
    fechaNacimiento: str = Form(...),
    sexo: str = Form(...),
    telefono: str = Form(...),
    correo: str = Form(...),
    idSede: int = Form(...),
    estadoCivil: str = Form(...),
    idNacionalidad: int = Form(...),
    hablaLengua: int = Form(...),
    idLengua: Optional[int] = Form(None),
    tieneBeca: int = Form(...),
    queBeca: Optional[str] = Form(None),
    hijoDeTrabjador: str = Form(...),
    idCapturo: str = Form(...),
    fechaTramite: Optional[str] = Form(...),
    fechaCaptura: Optional[str] = Form(...),
    idRol: Optional[int] = Form(0),
    tieneAlergias: int = Form(...),
    alergias: Optional[str] = Form(None),
    tipoSangre: str = Form(...),
    tieneDiscapacidad: int = Form(...),
    discapacidad: Optional[str] = Form(None),
    nombreTutor: Optional[str] = Form(None),
    apellidoPaternoTutor: Optional[str] = Form(None),
    apellidoMaternoTutor: Optional[str] = Form(None),
    telefonoTutor: Optional[str] = Form(None),
    codigoPostal: str = Form(...),
    calle: str = Form(...),
    entreCalles: Optional[str] = Form(None),
    numeroExterior: str = Form(...),
    numeroInterior: Optional[str] = Form(None),
    idLocalidad: str = Form(...),
    documentos: List[UploadFile] = File(...)
):
    conexion = connect()
    cursor = conexion.cursor()
    
    try:
        # Validar que los archivos sean PDF
        for documento in documentos:
            if not documento.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"El archivo {documento.filename} debe ser un PDF")
        
        # Crear directorio para almacenar archivos si no existe
        upload_dir = "uploads/documentos"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Crear tabla temporal para documentos
        cursor.execute("""
            CREATE TABLE #TempDocumentos (
                NombreArchivo NVARCHAR(255),
                RutaArchivo NVARCHAR(500),
                TamanoArchivo BIGINT,
                FechaSubida DATETIME
            )
        """)
        
        # Procesar y guardar archivos
        documentos_info = []
        for documento in documentos:
            # Generar nombre único para el archivo
            file_extension = os.path.splitext(documento.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Guardar archivo en el sistema de archivos
            content = await documento.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # Insertar información del documento en tabla temporal
            cursor.execute("""
                INSERT INTO #TempDocumentos (NombreArchivo, RutaArchivo, TamanoArchivo, FechaSubida)
                VALUES (?, ?, ?, ?)
            """, documento.filename, file_path, len(content), datetime.now())
        
        # Convertir valores int a boolean donde sea necesario
        habla_lengua_bool = hablaLengua == 1
        tiene_beca_bool = tieneBeca == 1
        hijo_trabajador_bool = hijoDeTrabjador.lower() == "true"
        tiene_alergias_bool = tieneAlergias == 1
        tiene_discapacidad_bool = tieneDiscapacidad == 1
        
        # Manejar campos vacíos
        discapacidad_valor = discapacidad if discapacidad and discapacidad.strip() else None
        
        # Manejar campos de tutor vacíos
        nombre_tutor_valor = nombreTutor if nombreTutor and nombreTutor.strip() else None
        apellido_paterno_tutor_valor = apellidoPaternoTutor if apellidoPaternoTutor and apellidoPaternoTutor.strip() else None
        apellido_materno_tutor_valor = apellidoMaternoTutor if apellidoMaternoTutor and apellidoMaternoTutor.strip() else None
        telefono_tutor_valor = telefonoTutor if telefonoTutor and telefonoTutor.strip() else None
        
        # Convertir fechas desde strings
        fecha_nacimiento = datetime.strptime(fechaNacimiento, '%Y-%m-%d').date()
        fecha_tramite = datetime.strptime(fechaTramite, '%Y-%m-%d').date()
        fecha_captura = datetime.strptime(fechaCaptura, '%Y-%m-%d')
        
        datos = (
            id,                                 # @IdAlumno
            curp,                              # @CURP
            matricula,                         # @Matricula
            nombre,                            # @Nombre
            apellidoPaterno,                   # @ApellidoPaterno
            apellidoMaterno,                   # @ApellidoMaterno
            fecha_nacimiento,                  # @FechaNacimiento
            sexo,                              # @Sexo
            telefono,                          # @Telefono
            correo,                            # @Correo
            idSede,                            # @IdSede
            estadoCivil,                       # @EstadoCivil
            idNacionalidad,                    # @IdNacionalidad
            habla_lengua_bool,                 # @HablaLengua
            idLengua,                          # @IdLengua
            tiene_beca_bool,                   # @TieneBeca
            queBeca,                           # @QueBeca
            hijo_trabajador_bool,              # @HijoDeTrabajador
            idCapturo,                         # @IdCapturo
            fecha_tramite,                     # @FechaTramite
            fecha_captura,                     # @FechaCaptura
            idRol,                             # @IdRol
            tiene_alergias_bool,               # @TieneAlergias
            alergias,                          # @Alergias
            tipoSangre,                        # @TipoSangre
            tiene_discapacidad_bool,           # @TieneDiscapacidad
            discapacidad_valor,                # @Discapacidad
            nombre_tutor_valor,                # @NombreTutor
            apellido_paterno_tutor_valor,      # @ApellidoPaternoTutor
            apellido_materno_tutor_valor,      # @ApellidoMaternoTutor
            telefono_tutor_valor,              # @TelefonoTutor
            codigoPostal,                      # @CodigoPostal
            calle,                             # @Calle
            entreCalles,                       # @EntreCalles
            numeroExterior,                    # @NumeroExterior
            numeroInterior if numeroInterior and numeroInterior.strip() else None,  # @NumeroInterior
            idLocalidad                        # @IdLocalidad
        )
        
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
        # Eliminar archivos subidos en caso de error
        for documento_info in documentos_info:
            if os.path.exists(documento_info['ruta_archivo']):
                os.remove(documento_info['ruta_archivo'])
        return {"error": f"Error al crear el alumno: {e}"}
    except Exception as e:
        print(f"Error general: {e}")
        conexion.rollback()
        return {"error": f"Error inesperado: {e}"}
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
    idNacionalidad: int = Field(gt=0, lt=5)
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
    telefonoTutor: Optional[str] = Field(default=None, max_length=15)
    codigoPostal: str = Field(max_length=10, min_length=5, pattern=r"^\d{5,10}$")
    calle: str = Field(max_length=100)
    entreCalles: Optional[str] = Field(default=None, max_length=100)
    numeroExterior: str = Field(max_length=10, min_length=1, pattern=r"^\d+$")
    numeroInterior: Optional[str] = Field(default=None, max_length=10)
    idLocalidad: str = Field(default="B0572553-592A-4A46-B730-000022504801")

@api.put("/alumnos/actualizar")
async def actualizar_alumno(
    id: str = Form(...),
    curp: str = Form(...),
    matricula: Optional[str] = Form(None),
    nombre: str = Form(...),
    apellidoPaterno: str = Form(...),
    apellidoMaterno: str = Form(...),
    fechaNacimiento: str = Form(...),
    sexo: str = Form(...),
    telefono: str = Form(...),
    correo: str = Form(...),
    idSede: int = Form(...),
    estadoCivil: str = Form(...),
    idNacionalidad: int = Form(...),
    hablaLengua: int = Form(...),
    idLengua: Optional[int] = Form(None),
    tieneBeca: int = Form(...),
    queBeca: Optional[str] = Form(None),
    hijoDeTrabjador: str = Form(...),
    idCapturo: str = Form(...),
    fechaTramite: Optional[date] = Form(...),
    fechaCaptura: Optional[date] = Form(...),
    idRol: int = Form(...),
    tieneAlergias: int = Form(...),
    alergias: Optional[str] = Form(None),
    tipoSangre: str = Form(...),
    tieneDiscapacidad: int = Form(...),
    discapacidad: Optional[str] = Form(None),
    nombreTutor: Optional[str] = Form(None),
    apellidoPaternoTutor: Optional[str] = Form(None),
    apellidoMaternoTutor: Optional[str] = Form(None),
    telefonoTutor: Optional[str] = Form(None),
    codigoPostal: str = Form(...),
    calle: str = Form(...),
    entreCalles: Optional[str] = Form(None),
    numeroExterior: str = Form(...),
    numeroInterior: Optional[str] = Form(None),
    idLocalidad: str = Form(default="B0572553-592A-4A46-B730-000022504801"),
    # Archivos PDF opcionales para actualización
    documentos: Optional[List[UploadFile]] = File(None)
):
    conexion = connect()
    cursor = conexion.cursor()
    
    try:
        # Si hay documentos nuevos, validar que sean PDF
        if documentos:
            for documento in documentos:
                if not documento.filename.lower().endswith('.pdf'):
                    raise HTTPException(status_code=400, detail=f"El archivo {documento.filename} debe ser un PDF")
        
        # Crear directorio para almacenar archivos si no existe
        upload_dir = "uploads/documentos"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Crear tabla temporal para documentos (solo si hay documentos nuevos)
        if documentos:
            cursor.execute("""
                CREATE TABLE #TempDocumentos (
                    NombreArchivo NVARCHAR(255),
                    RutaArchivo NVARCHAR(500),
                    TamanoArchivo BIGINT,
                    FechaSubida DATETIME
                )
            """)
            
            # Procesar y guardar archivos nuevos
            for documento in documentos:
                file_extension = os.path.splitext(documento.filename)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                file_path = os.path.join(upload_dir, unique_filename)
                
                content = await documento.read()
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                
                cursor.execute("""
                    INSERT INTO #TempDocumentos (NombreArchivo, RutaArchivo, TamanoArchivo, FechaSubida)
                    VALUES (?, ?, ?, ?)
                """, documento.filename, file_path, len(content), datetime.now())
        else:
            # Crear tabla temporal vacía si no hay documentos
            cursor.execute("""
                CREATE TABLE #TempDocumentos (
                    NombreArchivo NVARCHAR(255),
                    RutaArchivo NVARCHAR(500),
                    TamanoArchivo BIGINT,
                    FechaSubida DATETIME
                )
            """)
        
        # Resto de la lógica de actualización (misma que antes)
        habla_lengua_bool = hablaLengua == 1
        tiene_beca_bool = tieneBeca == 1
        hijo_trabajador_bool = hijoDeTrabjador.lower() == "true"
        tiene_alergias_bool = tieneAlergias == 1
        tiene_discapacidad_bool = tieneDiscapacidad == 1
        
        discapacidad_valor = discapacidad if discapacidad and discapacidad.strip() else None
        nombre_tutor_valor = nombreTutor if nombreTutor and nombreTutor.strip() else None
        apellido_paterno_tutor_valor = apellidoPaternoTutor if apellidoPaternoTutor and apellidoPaternoTutor.strip() else None
        apellido_materno_tutor_valor = apellidoMaternoTutor if apellidoMaternoTutor and apellidoMaternoTutor.strip() else None
        telefono_tutor_valor = telefonoTutor if telefonoTutor and telefonoTutor.strip() else None
        
        fecha_nacimiento = datetime.strptime(fechaNacimiento, '%Y-%m-%d').date()
        fecha_tramite = datetime.strptime(fechaTramite, '%Y-%m-%d').date()
        fecha_captura = datetime.strptime(fechaCaptura, '%Y-%m-%d')
        
        datos = (
            id, curp, matricula, nombre, apellidoPaterno, apellidoMaterno,
            fecha_nacimiento, sexo, telefono, correo, idSede, estadoCivil,
            idNacionalidad, habla_lengua_bool, idLengua, tiene_beca_bool,
            queBeca, hijo_trabajador_bool, idCapturo, fecha_tramite,
            fecha_captura, idRol, tiene_alergias_bool, alergias, tipoSangre,
            tiene_discapacidad_bool, discapacidad_valor, nombre_tutor_valor,
            apellido_paterno_tutor_valor, apellido_materno_tutor_valor,
            telefono_tutor_valor, codigoPostal, calle, entreCalles,
            numeroExterior, numeroInterior if numeroInterior and numeroInterior.strip() else None,
            idLocalidad
        )
        
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
    except Exception as e:
        print(f"Error general: {e}")
        conexion.rollback()
        return {"error": f"Error inesperado: {e}"}
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