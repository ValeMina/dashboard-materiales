import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard Materiales", layout="wide")

st.title("📊 Control de Materiales: Dashboard Interactivo")
st.markdown("Carga tus archivos para generar el reporte comparativo automáticamente.")

# --- BARRA LATERAL (CARGA DE ARCHIVOS) ---
with st.sidebar:
    st.header("📂 Cargar Archivos")
    st.info("Sube aquí tus documentos actualizados.")
    file_control = st.file_uploader("1. Control de Materiales (Excel/CSV)", type=['xlsx', 'csv'])
    file_trans = st.file_uploader("2. Entradas y Salidas (Excel/CSV)", type=['xlsx', 'csv'])

# --- FUNCIONES DE LÓGICA (EL CEREBRO DE LA APP) ---

def smart_load_control(file):
    """
    Lee el archivo de Control buscando inteligentemente en qué fila 
    empiezan los encabezados reales (busca 'CODIGO DE PIEZA').
    """
    try:
        # Leemos un pedazo del archivo para escanear
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None, nrows=20)
        else:
            df_raw = pd.read_excel(file, header=None, nrows=20)
        
        # Buscamos la fila que tenga el texto clave
        header_row_index = -1
        for i, row in df_raw.iterrows():
            row_text = [str(x).strip().upper() for x in row.values]
            if "CODIGO DE PIEZA" in row_text:
                header_row_index = i
                break
        
        if header_row_index == -1:
            st.error("❌ No encontré la columna 'CODIGO DE PIEZA' en el inicio del archivo. Verifica el formato.")
            return None

        # Recargamos el archivo saltando las filas basura
        if file.name.endswith('.csv'):
            file.seek(0)
            df = pd.read_csv(file, header=header_row_index)
        else:
            df = pd.read_excel(file, header=header_row_index)
            
        return df
        
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

def process_data(df_c, df_t):
    """
    Limpia, cruza y calcula las diferencias entre Control y Almacén.
    """
    # 1. Limpieza básica de nombres de columnas
    df_c.columns = [str(c).replace('\n', ' ').strip() for c in df_c.columns]
    df_t.columns = [str(c).strip() for c in df_t.columns]
    
    # 2. Verificar columnas necesarias
    cols_necesarias = ['CODIGO DE PIEZA', 'CANT ITEM S.C.', 'DESCRIPCION DE LA PARTIDA']
    missing = [c for c in cols_necesarias if c not in df_c.columns]
    
    if missing:
        st.error(f"⚠️ Faltan columnas clave en el Control: {missing}")
        return None

    # 3. Preparar Datos de Control
    df_c_clean = df_c[cols_necesarias].copy()
    # Convertir a números, errores se vuelven 0
    df_c_clean['CANT ITEM S.C.'] = pd.to_numeric(df_c_clean['CANT ITEM S.C.'], errors='coerce').fillna(0)
    
    # Agrupar por Código (por si hay duplicados)
    df_c_agg = df_c_clean.groupby('CODIGO DE PIEZA').agg({
        'CANT ITEM S.C.': 'sum',
        'DESCRIPCION DE LA PARTIDA': 'first'
    }).reset_index()
    
    df_c_agg.rename(columns={'CANT ITEM S.C.': 'Solicitado', 'DESCRIPCION DE LA PARTIDA': 'Descripcion'}, inplace=True)

    # 4. Preparar Datos de Transacciones (Pivote)
    if 'TRANSACCION' not in df_t.columns or 'PIEZA' not in df_t.columns:
         st.error("El archivo de Entradas/Salidas debe tener columnas 'TRANSACCION' y 'PI
