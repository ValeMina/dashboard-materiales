import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero de Control R-1926", layout="wide", page_icon="⚓")

DB_FILE = "db_materiales.json"
PDF_DIR = "pdfs_listas_pedido"

# Crear directorio de PDFs si no existe
os.makedirs(PDF_DIR, exist_ok=True)

# --- PERSISTENCIA ---
def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_datos(lista_proyectos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(lista_proyectos, f, default=str)

if "proyectos" not in st.session_state:
    st.session_state.proyectos = cargar_datos()

# --- PROCESAMIENTO DEL EXCEL ---
def procesar_nuevo_excel(df_raw: pd.DataFrame):
    """
    Tabla basada en FECHA DE LLEGADA válida.
    Columnas usadas por índice:
    - 0 (A): No. S.C.
    - 3 (D): CANT ITEM S.C.
    - 5 (F): DESCRIPCION DE LA PARTIDA
    - 7 (H): No. O.C.
    - 12 (M): FECHA DE LLEGADA
    Solo se consideran filas donde la columna M se puede interpretar como fecha.
    """
    # Verificar columnas suficientes
    if df_raw.shape[1] < 13:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la M)."}

    # 1) Items solicitados: filas con cantidad en columna D (índice 3)
    df_solicitados =
