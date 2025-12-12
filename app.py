import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Dashboard Materiales", layout="wide")

st.title("📊 Comparador de Materiales v2.0")
st.markdown("Carga tus archivos. El sistema buscará automáticamente dónde comienzan los datos.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Cargar Archivos")
    file_control = st.file_uploader("1. Control de Materiales", type=['xlsx', 'csv'])
    file_trans = st.file_uploader("2. Entradas y Salidas", type=['xlsx', 'csv'])

# --- FUNCIÓN INTELIGENTE PARA ENCONTRAR ENCABEZADOS ---
def smart_load_control(file):
    """Lee el archivo y busca automáticamente la fila de encabezados"""
    try:
        # Leemos las primeras 15 filas sin asumir encabezados
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None, nrows=15)
        else:
            df_raw = pd.read_excel(file, header=None, nrows=15)
        
        # Buscamos en qué fila está la columna clave "CODIGO DE PIEZA"
        header_row_index = -1
        for i, row in df_raw.iterrows():
            # Convertimos la fila a texto para buscar
            row_text = [str(x).strip().upper() for x in row.values]
            if "CODIGO DE PIEZA" in row_text:
                header_row_index = i
                break
        
        if header_row_index == -1:
            st.error("❌ No encontré la columna 'CODIGO DE PIEZA' en las primeras 15 filas. Verifica tu archivo.")
            return None

        # Ahora recargamos el archivo saltando las filas incorrectas
        if file.name.endswith('.csv'):
            file.seek(0) # Regresar al inicio del archivo
            df = pd.read_csv(file, header=header_row_index)
        else:
            df = pd.read_excel(file, header=header_row_index)
            
        return df
        
    except Exception as e:
        st.error(f"Error leyendo el archivo: {e}")
        return None

# --- PROCESAMIENTO ---
def process_data(df_c, df_t):
    # 1. Limpieza de nombres de columnas
    df_c.columns = [str(c).replace('\n', ' ').strip() for c in df_c.columns]
    df_t.columns = [str(c).strip() for c in df_t.columns]
    
    # 2. Verificar columnas necesarias
    cols_necesarias = ['CODIGO DE PIEZA', 'CANT ITEM S.C.', 'CANT RECIBIDA', 'DESCRIPCION DE LA PARTIDA']
    missing = [c for c in cols_necesarias if c not in df_c.columns]
    
    if missing:
        st.error(f"⚠️ Faltan estas columnas en el archivo de Control: {missing}")
        st.write("Columnas encontradas:", list(df_c.columns))
        return None

    # 3. Preparar Control
    df_c_clean = df_c[cols_necesarias].copy()
    df_c_clean['CANT ITEM S.C.'] = pd.to_numeric(df_c_clean['CANT ITEM S.C.'], errors='coerce').fillna(0)
    
    df_c_agg = df_c_clean.groupby('CODIGO DE PIEZA').agg({
        'CANT ITEM S.C.': 'sum',
        'DESCRIPCION DE LA PARTIDA': 'first'
    }).reset_index()
    
    df_c_agg.rename(columns={'CANT ITEM S.C.': 'Solicitado', 'DESCRIPCION DE LA PARTIDA': 'Descripcion'}, inplace=True)

    # 4. Preparar Transacciones
    if 'TRANSACCION' not in df_t.columns or 'PIEZA' not in df_t.columns:
         st.error("El archivo de Entradas/Salidas no tiene columnas 'TRANSACCION' o 'PIEZA'.")
         return None
         
    df_t_pivot = df_t.pivot_table(index='PIEZA', columns='TRANSACCION', values='CANTIDAD', aggfunc='sum', fill_value=0).reset_index()
    
    if 'RECEPCIONES' not in df_t_pivot.columns: df_t_pivot['RECEPCIONES'] = 0
    if 'DESPACHOS' not in df_t_pivot.columns: df_t_pivot['DESPACHOS'] = 0
    
    df_t_pivot.rename(columns={'RECEPCIONES': 'Recibido_Real', 'DESPACHOS': 'Despachado_Real'}, inplace=True)

    # 5. Cruzar (Merge)
    df_merged = pd.merge(df_c_agg, df_t_pivot, left_on='CODIGO DE PIEZA', right_on='PIEZA', how='outer')
    df_merged.fillna(0, inplace=True)
    
    df_merged['Material'] = df_merged.apply(lambda x: x['CODIGO DE PIEZA'] if x['CODIGO DE PIEZA'] != 0 else x['PIEZA'], axis=1)
    
    # Cálculos Finales
    df_merged['Solicitado'] = pd.to_numeric(df_merged['Solicitado'])
    df_merged['Recibido_Real'] = pd.to_numeric(df_merged['Recibido_Real'])
    df_merged['Despachado_Real'] = pd.to_numeric(df_merged['Despachado_Real'])
    
    df_merged['Pendiente_Recepcion'] = (df_merged['Solicitado'] - df_merged['Recibido_Real']).clip(lower=0)
    df_merged['En_Inventario'] = (df_merged['Recibido_Real'] - df_merged['Despachado_Real'])

    return df_merged[(df_merged['Solicitado'] > 0) | (df_merged['Recibido_Real'] > 0) | (df_merged['Despachado_Real'] > 0)]

# --- EJECUCIÓN ---
if file_control and file_trans:
    with st.spinner('Analizando archivos...'):
        # Cargar archivo de transacciones simple
        if file_trans.name.endswith('.csv'):
            df_t = pd.read_csv(file_trans)
        else:
            df_t = pd.read_excel(file_trans)

        # Cargar archivo de control INTELIGENTE
        df_c = smart_load_control(file_control)
        
        if df_c is not None:
            df_result = process_data(df_c, df_t)
            
            if df_result is not None:
                st.success("✅ ¡Datos cruzados correctamente!")
                
                # Métricas
                c1, c2, c3 = st.columns(3)
                c1.metric("Items Solicitados", f"{df_result['Solicitado'].sum():,.0f}")
                c2.metric("Pendiente por Recibir", f"{df_result['Pendiente_Recepcion'].sum():,.0f}", delta_color="inverse")
                c3.metric("Stock Físico", f"{df_result['En_Inventario'].sum():,.0f}")
                
                st.divider()
                
                # Gráficos
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("⚠️ Faltantes (Top 10)")
                    top_pend = df_result.sort_values('Pendiente_Recepcion', ascending=False).head(10)
                    if not top_pend.empty:
                        fig1 = px.bar(top_pend, x='Pendiente_Recepcion', y='Descripcion', orientation='h', color='Pendiente_Recepcion', color_continuous_scale='Reds')
                        fig1.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                        st.plotly_chart(fig1, use_container_width=True)
                    else:
                        st.info("¡Nada pendiente!")

                with col2:
                    st.subheader("📦 Stock en Almacén (Top 10)")
                    top_stock = df_result.sort_values('En_Inventario', ascending=False).head(10)
                    if not top_stock.empty:
                        fig2 = px.bar(top_stock, x='En_Inventario', y='Descripcion', orientation='h', color='En_Inventario', color_continuous_scale='Greens')
                        fig2.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.info("Inventario vacío.")

                # Tabla
                st.dataframe(df_result, use_container_width=True)
                
                # Descarga
                csv = df_result.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Descargar CSV", csv, "reporte_materiales.csv", "text/csv")
