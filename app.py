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

        if df.shape[1] < 15:
            st.error("⚠️ El archivo no tiene suficientes columnas. Se requiere al menos hasta la columna O.")
        else:
            # --- CÁLCULOS DE MÉTRICAS ---

            # 1. Items Requisitados (Columna F = índice 5)
            # Cuenta todos los datos (incluyendo repetidos)
            items_requisitados = df.iloc[:, 5].count()

            # 2. Items Recibidos (Columna O = índice 14)
            # Solo los que empiezan con "RE"
            columna_O = df.iloc[:, 14].astype(str).str.strip()
            items_recibidos = columna_O[columna_O.str.startswith('RE')].count()

            # 3. Items sin OC (Columna H = índice 7)
            # "Dame el recuento de los ITEMS que no tengan datos en H"
            # .isnull().sum() cuenta las celdas vacías (NaN)
            items_sin_oc = df.iloc[:, 7].isnull().sum()

            # 4. Porcentaje de Avance (Recibidos vs Requisitados)
            if items_requisitados > 0:
                porcentaje = (items_recibidos / items_requisitados) * 100
            else:
                porcentaje = 0

            # --- VISUALIZACIÓN ---
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(label="Items Requisitados", value=items_requisitados, help="Total en Columna F")
            
            with col2:
                st.metric(label="Items Recibidos", value=items_recibidos, help="Columna O inicia con 'RE'")

            with col3:
                # Mostramos los items que faltan de OC (vacíos en H)
                st.metric(label="Items sin OC", value=items_sin_oc, help="Celdas vacías en Columna H")
                
            with col4:
                # Destacado en verde
                # Usamos 'delta' con un texto positivo para forzar el color verde en Streamlit
                st.metric(
                    label="Porcentaje de Avance", 
                    value=f"{porcentaje:.1f}%", 
                    delta="Progreso Global"  # El delta sale en verde por defecto si es positivo
                )

            st.write("---")

            # GRÁFICA DE APOYO
            st.subheader("Estado General")
            datos_grafica = pd.DataFrame({
                'Estado': ['Requisitados', 'Recibidos', 'Sin OC'],
                'Cantidad': [items_requisitados, items_recibidos, items_sin_oc]
            })
            
            # Gráfica de barras simple
            fig = px.bar(
                datos_grafica, x='Estado', y='Cantidad', 
                color='Estado', 
                text_auto=True,
                color_discrete_map={
                    'Requisitados': '#3498db', # Azul
                    'Recibidos': '#2ecc71',    # Verde
                    'Sin OC': '#e74c3c'        # Rojo
                }
            )
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Ver Base de Datos"):
                st.dataframe(df)

    except Exception as e:
        st.error(f"Error al procesar: {e}")
else:
    st.info("Esperando archivo Excel...")
