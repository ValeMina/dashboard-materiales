import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Dashboard Materiales", layout="wide")

st.title("📊 Comparador de Materiales: Control vs. Almacén")
st.markdown("Sube tus archivos de **Control de Materiales** y **Entradas/Salidas** para generar el reporte automático.")

# --- BARRA LATERAL PARA SUBIR ARCHIVOS ---
with st.sidebar:
    st.header("Cargar Archivos")
    file_control = st.file_uploader("1. Control de Materiales (R-1933...)", type=['xlsx', 'csv'])
    file_trans = st.file_uploader("2. Entradas y Salidas", type=['xlsx', 'csv'])
    
    st.info("Nota: El sistema asume que los encabezados del Control están en la fila 5.")

# --- LÓGICA DE PROCESAMIENTO ---
def load_data(file_c, file_t):
    # Cargar Transacciones
    if file_t.name.endswith('.csv'):
        df_t = pd.read_csv(file_t)
    else:
        df_t = pd.read_excel(file_t)

    # Cargar Control (Saltando filas del encabezado visual)
    if file_c.name.endswith('.csv'):
        df_c = pd.read_csv(file_c, header=4)
    else:
        df_c = pd.read_excel(file_c, header=4)
        
    return df_c, df_t

def process_data(df_c, df_t):
    # 1. Limpieza de nombres de columnas
    df_c.columns = [str(c).replace('\n', ' ').strip() for c in df_c.columns]
    df_t.columns = [str(c).strip() for c in df_t.columns]
    
    # 2. Preparar Control
    cols_necesarias = ['CODIGO DE PIEZA', 'CANT ITEM S.C.', 'CANT RECIBIDA', 'DESCRIPCION DE LA PARTIDA']
    # Verificar existencia de columnas (manejo de errores básico)
    if not all(col in df_c.columns for col in cols_necesarias):
        st.error("El archivo de Control no tiene las columnas esperadas. Verifica el formato.")
        return None

    df_c_clean = df_c[cols_necesarias].copy()
    df_c_clean['CANT ITEM S.C.'] = pd.to_numeric(df_c_clean['CANT ITEM S.C.'], errors='coerce').fillna(0)
    
    # Agrupar por Código
    df_c_agg = df_c_clean.groupby('CODIGO DE PIEZA').agg({
        'CANT ITEM S.C.': 'sum',
        'DESCRIPCION DE LA PARTIDA': 'first'
    }).reset_index()
    
    df_c_agg.rename(columns={
        'CANT ITEM S.C.': 'Solicitado',
        'DESCRIPCION DE LA PARTIDA': 'Descripcion'
    }, inplace=True)

    # 3. Preparar Transacciones
    # Pivoteamos para sumar RECEPCIONES y DESPACHOS
    if 'TRANSACCION' not in df_t.columns or 'PIEZA' not in df_t.columns:
         st.error("El archivo de Entradas/Salidas no tiene columnas 'TRANSACCION' o 'PIEZA'.")
         return None
         
    df_t_pivot = df_t.pivot_table(
        index='PIEZA', 
        columns='TRANSACCION', 
        values='CANTIDAD', 
        aggfunc='sum', 
        fill_value=0
    ).reset_index()
    
    # Normalizar columnas
    if 'RECEPCIONES' not in df_t_pivot.columns: df_t_pivot['RECEPCIONES'] = 0
    if 'DESPACHOS' not in df_t_pivot.columns: df_t_pivot['DESPACHOS'] = 0
    
    df_t_pivot.rename(columns={'RECEPCIONES': 'Recibido_Real', 'DESPACHOS': 'Despachado_Real'}, inplace=True)
    df_t_pivot.columns.name = None

    # 4. Cruzar Información (Merge)
    df_merged = pd.merge(df_c_agg, df_t_pivot, left_on='CODIGO DE PIEZA', right_on='PIEZA', how='outer')
    df_merged.fillna(0, inplace=True)
    
    # Definir Material y Descripción Final
    df_merged['Material'] = df_merged.apply(lambda x: x['CODIGO DE PIEZA'] if x['CODIGO DE PIEZA'] != 0 else x['PIEZA'], axis=1)
    
    # Cálculos Finales
    df_merged['Solicitado'] = pd.to_numeric(df_merged['Solicitado'])
    df_merged['Recibido_Real'] = pd.to_numeric(df_merged['Recibido_Real'])
    df_merged['Despachado_Real'] = pd.to_numeric(df_merged['Despachado_Real'])
    
    df_merged['Pendiente_Recepcion'] = (df_merged['Solicitado'] - df_merged['Recibido_Real']).clip(lower=0)
    df_merged['En_Inventario'] = (df_merged['Recibido_Real'] - df_merged['Despachado_Real'])

    # Limpieza final
    df_final = df_merged[['Material', 'Descripcion', 'Solicitado', 'Recibido_Real', 'Despachado_Real', 'Pendiente_Recepcion', 'En_Inventario']].copy()
    
    # Filtrar filas vacías (sin actividad)
    df_final = df_final[(df_final['Solicitado'] > 0) | (df_final['Recibido_Real'] > 0) | (df_final['Despachado_Real'] > 0)]
    
    return df_final

# --- EJECUCIÓN ---
if file_control and file_trans:
    with st.spinner('Procesando y cruzando bases de datos...'):
        try:
            raw_c, raw_t = load_data(file_control, file_trans)
            df_result = process_data(raw_c, raw_t)
            
            if df_result is not None:
                st.success("¡Análisis completado con éxito!")
                
                # METRICAS GENERALES
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Solicitado (Items)", f"{df_result['Solicitado'].sum():,.0f}")
                c2.metric("Pendiente por Recibir", f"{df_result['Pendiente_Recepcion'].sum():,.0f}", delta_color="inverse")
                c3.metric("Stock Actual en Sitio", f"{df_result['En_Inventario'].sum():,.0f}")
                
                st.divider()
                
                # GRAFICAS INTERACTIVAS
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.subheader("⚠️ Top Pendientes de Recepción")
                    top_pendientes = df_result.sort_values('Pendiente_Recepcion', ascending=False).head(10)
                    fig1 = px.bar(top_pendientes, x='Pendiente_Recepcion', y='Descripcion', orientation='h',
                                  title="Lo que falta que llegue (Top 10)", color='Pendiente_Recepcion', color_continuous_scale='Oranges')
                    fig1.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                    st.plotly_chart(fig1, use_container_width=True)

                with col_chart2:
                    st.subheader("📦 Top Stock (Sin Despachar)")
                    top_stock = df_result.sort_values('En_Inventario', ascending=False).head(10)
                    fig2 = px.bar(top_stock, x='En_Inventario', y='Descripcion', orientation='h',
                                  title="Material detenido en almacén (Top 10)", color='En_Inventario', color_continuous_scale='Purples')
                    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)
                
                # TABLA DE DATOS
                st.subheader("Detalle Completo")
                st.dataframe(df_result, use_container_width=True)
                
                # DESCARGA
                csv = df_result.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar Reporte Unificado (CSV)",
                    data=csv,
                    file_name='comparativo_materiales_master.csv',
                    mime='text/csv',
                )
                
        except Exception as e:
            st.error(f"Ocurrió un error al procesar los archivos: {e}")
            st.warning("Asegúrate de que estás subiendo los archivos correctos (Control y Transacciones).")

else:
    st.info("👆 Sube ambos archivos en la barra lateral para comenzar.")