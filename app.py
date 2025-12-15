import streamlit as st
import pandas as pd
import plotly.express as px 

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Dashboard R-1926", layout="wide")

st.markdown("<h1 style='text-align: center;'>⚓ Dashboard: R-1926 MONFORTE DE LEMOS</h1>", unsafe_allow_html=True)
st.write("---")

# --- CARGA DE ARCHIVO ---
archivo_subido = st.file_uploader("📂 Carga tu archivo Excel", type=["xlsx", "xls"])

if archivo_subido is not None:
    try:
        df = pd.read_excel(archivo_subido, header=0)

        # Verificamos columnas mínimas (hasta la O = 15 columnas)
        if df.shape[1] < 15:
            st.error("⚠️ El archivo no tiene suficientes columnas. Necesito al menos hasta la columna O.")
        else:
            # --- CÁLCULOS ACTUALIZADOS ---

            # 1. Items Requisitados (Columna F = índice 5)
            # Regla: Contar todas (repetidas cuentan como otro item diferente)
            columna_F = df.iloc[:, 5]
            # .count() cuenta todas las celdas que NO están vacías. 
            # Si quieres contar incluso filas vacías, usa len(df), pero .count() es más seguro para datos reales.
            items_requisitados = columna_F.count()

            # 2. Items Recibidos (Columna O = índice 14)
            # Regla: Empieza con "RE"
            columna_O = df.iloc[:, 14].astype(str).str.strip()
            items_recibidos = columna_O[columna_O.str.startswith('RE')].count()

            # Cálculo de Porcentaje
            if items_requisitados > 0:
                avance = (items_recibidos / items_requisitados) * 100
            else:
                avance = 0

            # --- VISUALIZACIÓN ---
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(label="Items Requisitados", value=items_requisitados, help="Total de datos en Columna F (incluye repetidos)")
            
            with col2:
                st.metric(label="Items Recibidos", value=items_recibidos, delta=f"{avance:.1f}%", help="Columna O que inicia con 'RE'")

            with col3:
                st.metric(label="Entregas a Tiempo (OTD)", value="--")
                
            with col4:
                st.metric(label="Retraso Promedio", value="--")

            # Gráfico simple para ver la proporción
            st.write("---")
            datos_grafica = pd.DataFrame({
                'Métrica': ['Requisitados', 'Recibidos'],
                'Cantidad': [items_requisitados, items_recibidos]
            })
            
            fig = px.bar(datos_grafica, x='Métrica', y='Cantidad', color='Métrica', 
                         title="Avance de Materiales", text_auto=True,
                         color_discrete_sequence=['#3498db', '#2ecc71'])
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Ver datos completos"):
                st.dataframe(df)

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
else:
    st.info("Esperando archivo... Sube el Excel para procesar.")
