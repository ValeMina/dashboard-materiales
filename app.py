import pandas as pd
import numpy as np

def procesar_inventario(ruta_archivo):
    # 1. Cargar el archivo
    # 'header=5' indica que el encabezado está en la fila 6 (índice 5), 
    # por lo que los datos comienzan en la fila 7.
    df = pd.read_csv(ruta_archivo, header=5)

    # 2. Filtrar filas válidas (Regla: Columna A debe ser numérica)
    # Convertimos la columna 'No. S.C.' (Columna A) a numérico, forzando errores a NaN
    df['No. S.C. Numeric'] = pd.to_numeric(df['No. S.C.'], errors='coerce')
    
    # Eliminamos las filas donde no haya un número (ej. filas vacías o texto extra)
    df_filtrado = df[df['No. S.C. Numeric'].notna()].copy()

    # 3. Seleccionar las columnas según tus indicaciones
    # Mapeo:
    # A -> 'No. S.C.'
    # F -> 'DESCRIPCION DE LA PARTIDA'
    # D -> 'CANT ITEM S.C.'
    # H -> 'No. O.C.'
    # M -> 'FECHA DE LLEGADA'
    columnas_deseadas = [
        'No. S.C.', 
        'DESCRIPCION DE LA PARTIDA', 
        'CANT ITEM S.C.', 
        'No. O.C.', 
        'FECHA DE LLEGADA'
    ]
    
    nueva_tabla = df_filtrado[columnas_deseadas].copy()

    # 4. Renombrar las columnas a los nombres finales
    nueva_tabla.columns = [
        'SC', 
        'ITEM', 
        'CANTIDAD', 
        'ORDEN DE COMPRA', 
        'FECHA DE LLEGADA'
    ]

    # 5. Agregar la columna especial "LISTA DE PEDIDO"
    # Se inicializa vacía para que el sistema admin pueda escribir en ella
    nueva_tabla['LISTA DE PEDIDO'] = ""

    return nueva_tabla

# --- Ejemplo de uso ---
# Reemplaza 'nombre_de_tu_archivo.csv' con la ruta real de tu archivo
archivo_entrada = 'R-1916 TROPIC SUN - CONTROL DE MATERIALES (15-09-25).xlsx - R-1916.csv'

try:
    df_resultado = procesar_inventario(archivo_entrada)
    
    # Mostrar las primeras filas
    print("Tabla procesada correctamente:")
    print(df_resultado.head())
    
    # Guardar el resultado en un nuevo CSV
    df_resultado.to_csv('Tabla_Final_Procesada.csv', index=False)
    print("\nArchivo guardado como 'Tabla_Final_Procesada.csv'")

except FileNotFoundError:
    print("Error: No se encontró el archivo especificado.")
