import pyodbc
import dotenv
import os

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