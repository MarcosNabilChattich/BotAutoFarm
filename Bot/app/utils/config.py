import json
import os

RUTA_PERFILES = "resources/profiles"

def guardar_perfil(nombre_archivo, data):
    """Guarda un diccionario de datos en un archivo JSON en la carpeta de perfiles."""
    os.makedirs(RUTA_PERFILES, exist_ok=True)
    ruta_completa = os.path.join(RUTA_PERFILES, nombre_archivo)
    
    try:
        with open(ruta_completa, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Perfil guardado en {ruta_completa}")
        return True
    except Exception as e:
        print(f"Error al guardar perfil {nombre_archivo}: {e}")
        return False

def cargar_perfil(nombre_archivo):
    """Carga datos desde un archivo JSON en la carpeta de perfiles."""
    ruta_completa = os.path.join(RUTA_PERFILES, nombre_archivo)
    
    if not os.path.exists(ruta_completa):
        print(f"Error: No se encuentra el perfil {ruta_completa}")
        return None
        
    try:
        with open(ruta_completa, 'r') as f:
            data = json.load(f)
        print(f"Perfil {nombre_archivo} cargado.")
        return data
    except Exception as e:
        print(f"Error al cargar perfil {nombre_archivo}: {e}")
        return None