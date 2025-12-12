import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración
st.set_page_config(page_title="Dashboard Materiales", layout="wide")
st.title("🕵️ Dashboard Modo Diagnóstico")
st.markdown("Si algo falla, este modo te dirá exactamente por qué.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Cargar Archivos")
    file_control = st.file_uploader("Control de Materiales (R-1933...)", type=['xlsx', 'csv'])
    file_trans = st.file_uploader("Entradas y Salidas", type=['xlsx', 'csv'])

# --- FUNCIONES ---
def smart_load_control(file):
    st.info(f"📂 Analizando archivo: {file.name}...")
    try:
        # Leemos sin encabezados primero
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None, nrows=15)
        else:
            df_raw = pd.read_excel(file, header=None, nrows=15)
        
        # Mostramos al usuario lo que vemos (para debug)
        with st.expander("Ver primeras filas del archivo crudo (Click aquí)"):
            st.dataframe(df_raw)

        # Buscamos la fila clave
        header_row = -1
        for i, row in df_raw.iterrows():
            # Convertimos toda la fila a texto mayúscula para buscar
            row_str = " ".join([str(x).upper() for x in row.values])
            
            # BUSQUEDA FLEXIBLE: Busca "CODIGO" y "PIEZA" (juntos o separados)
            if "CODIGO" in row_str and "PIEZA" in row_str:
                header_row = i
                st.success(f"✅ Encabezados encontrados en la fila {i+1}")
                break
        
        if header_row == -1:
            st.error("❌ ERROR CRÍTICO: No encontré 'CODIGO DE PIEZA' en las primeras 15 filas.")
            st.warning("Por favor, abre tu Excel y revisa que la columna se llame 'CODIGO DE PIEZA'.")
            return None

        # Recargar con el encabezado correcto
        if file.name.endswith('.csv'):
            file.seek(0)
            df = pd.read_csv(file, header=header_row)
        else:
            df = pd.read_excel(file, header=header_row)
            
        return df

    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return None

def process_data(df_c, df_t):
    st.write("---")
    st.info("🔄 Procesando datos...")
    
    # Limpieza de nombres de columnas
    df_c.columns = [str(c).replace('\n', ' ').strip().upper() for c in df_c.columns]
    df_t.columns = [str(c).strip().upper() for c in df_t.columns]

    # Debug: Mostrar columnas encontradas
    with st.expander("Ver nombres de columnas detectados"):
        st.write("Columnas Control:", list(df_c.columns))
        st.write("Columnas Transacciones:", list(df_t.columns))

    # Identificar columna de Código en Control
    col_codigo = next((c for c in df_c.columns if "CODIGO" in c and "PIEZA" in c), None)
    col_solicitado = next((c for c in df_c.columns if "CANT" in c and "S.C." in c), None)
    col_desc = next((c for c in df_c.columns if "DESCRIPCION" in c), None)

    if not col_codigo or not col_solicitado:
        st.error(f"❌ No encuentro las columnas necesarias. Busco parecidos a: 'CODIGO DE PIEZA' y 'CANT ITEM S.C.'")
        return None

    # Normalizar Control
    df_c_clean = df_c.copy()
    df_c_clean['Solicitado'] = pd.to_numeric(df_c_clean[col_solicitado], errors='coerce').fillna(0)
    
    # Agrupar Control
    df_c_agg = df_c_clean.groupby(col_codigo).agg({
        'Solicitado': 'sum',
        col_desc: 'first'
    }).reset_index()
    df_c_agg.rename(columns={col_codigo: 'Material', col_desc: 'Descripcion'}, inplace=True)

    # Preparar Transacciones
    if 'TRANSACCION' not in df_t.columns or 'PIEZA' not in df_t.columns:
        st.error(f"❌ El archivo de Transacciones necesita columnas 'TRANSACCION' y 'PIEZA'. Encontré: {list(df_t.columns)}")
        return None

    df_t_pivot = df_t.pivot_table(index='PIEZA', columns='TRANSACCION', values='CANTIDAD', aggfunc='sum', fill_value=0).reset_index()
    
    # Normalizar columnas de pivote
    if 'RECEPCIONES' not in df_t_pivot.columns: df_t_pivot['RECEPCIONES'] = 0
    if 'DESPACHOS' not in df_t_pivot.columns: df_t_pivot['DESPACHOS'] = 0
    
    # MERGE
    st.write("🔗 Cruzando bases de datos...")
    df_merged = pd.merge(df_c_agg, df_t_pivot, left_on='Material', right_on='PIEZA', how='outer')
    df_merged.fillna(0, inplace=True)
    
    # Arreglar columna Material y Descripción
    df_merged['Material'] = df_merged.apply(lambda x: x['Material'] if str(x['Material']) != '0' and str(x['Material']) != 'nan' else x['PIEZA'], axis=1)
    
    # Cálculos
    df_merged['Solicitado'] = pd.to_numeric(df_merged['Solicitado'])
    df_merged['Recibido_Real'] = pd.to_numeric(df_merged['RECEPCIONES'])
    df_merged['Despachado_Real'] = pd.to_numeric(df_merged['DESPACHOS'])
    
    df_merged['Pendiente_Recepcion'] = (df_merged['Solicitado'] - df_merged['Recibido_Real']).clip(lower=0)
    df_merged['En_Inventario'] = (df_merged['Recibido_Real'] - df_merged['Despachado_Real'])

    return df_merged

# --- EJECUCIÓN ---
if file_control and file_trans:
    df_c = smart_load_control(file_control)
    
    if df_c is not None:
        # Cargar Transacciones
        if file_trans.name.endswith('.csv'):
            df_t = pd.read_csv(file_trans)
        else:
            df_t = pd.read_excel(file_trans)
            
        df_result = process_data(df_c, df_t)
        
        if df_result is not None:
            st.success("✅ ¡Cálculos terminados exitosamente!")
            
            # --- PESTAÑAS (TABS) ---
            tab1, tab2, tab3 = st.tabs(["📋 SC Realizadas", "⚠️ Pendientes", "✅ Recibidas"])
            
            with tab1:
                st.metric("Total Solicitado", f"{df_result['Solicitado'].sum():,.0f}")
                st.dataframe(df_result)
            
            with tab2:
                pend = df_result[df_result['Pendiente_Recepcion'] > 0]
                if not pend.empty:
                    st.metric("Faltantes", f"{pend['Pendiente_Recepcion'].sum():,.0f}")
                    st.dataframe(pend)
                else:
                    st.success("Nada pendiente.")
            
            with tab3:
                rec = df_result[df_result['Recibido_Real'] > 0]
                st.dataframe(rec)

else:
    st.warning("👈 Esperando que subas AMBOS archivos en la barra lateral...")
