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
    # AQUI ESTABA EL ERROR: Asegurate de copiar esto en una sola linea
    if 'TRANSACCION' not in df_t.columns or 'PIEZA' not in df_t.columns:
         st.error("El archivo Entradas/Salidas necesita columnas 'TRANSACCION' y 'PIEZA'.")
         return None
         
    df_t_pivot = df_t.pivot_table(
        index='PIEZA', 
        columns='TRANSACCION', 
        values='CANTIDAD', 
        aggfunc='sum', 
        fill_value=0
    ).reset_index()
    
    # Asegurar columnas aunque no existan en el archivo
    if 'RECEPCIONES' not in df_t_pivot.columns: df_t_pivot['RECEPCIONES'] = 0
    if 'DESPACHOS' not in df_t_pivot.columns: df_t_pivot['DESPACHOS'] = 0
    
    df_t_pivot.rename(columns={'RECEPCIONES': 'Recibido_Real', 'DESPACHOS': 'Despachado_Real'}, inplace=True)

    # 5. Cruzar Tablas (Merge)
    df_merged = pd.merge(df_c_agg, df_t_pivot, left_on='CODIGO DE PIEZA', right_on='PIEZA', how='outer')
    df_merged.fillna(0, inplace=True)
    
    # Crear columna unificada de Material
    df_merged['Material'] = df_merged.apply(lambda x: x['CODIGO DE PIEZA'] if x['CODIGO DE PIEZA'] != 0 else x['PIEZA'], axis=1)
    
    # 6. Cálculos Finales
    df_merged['Solicitado'] = pd.to_numeric(df_merged['Solicitado'])
    df_merged['Recibido_Real'] = pd.to_numeric(df_merged['Recibido_Real'])
    df_merged['Despachado_Real'] = pd.to_numeric(df_merged['Despachado_Real'])
    
    # Pendiente = Solicitado - Recibido (No permitimos negativos)
    df_merged['Pendiente_Recepcion'] = (df_merged['Solicitado'] - df_merged['Recibido_Real']).clip(lower=0)
    
    # En Inventario = Recibido - Despachado
    df_merged['En_Inventario'] = (df_merged['Recibido_Real'] - df_merged['Despachado_Real'])

    # Filtrar basura (filas donde todo es 0)
    mask = (df_merged['Solicitado'] > 0) | (df_merged['Recibido_Real'] > 0) | (df_merged['Despachado_Real'] > 0)
    return df_merged[mask].copy()
