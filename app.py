import streamlit as st
import pandas as pd
import plotly.express as px  # Opcional: por si queremos gráficas bonitas

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Dashboard R-1926",
    page_icon="⚓",
    layout="wide"
)

# Título Principal con estilo
st.markdown("""
    <h1 style='text-align: center;'>
        ⚓ Dashboard: R-1926 MONFORTE DE LEMOS
    </h1>
    """, unsafe_allow_html=True)

st.write("---") # Línea divisoria

# --- 2. CARGA DE ARCHIVO ---
archivo_subido = st.file_uploader("📂 Carga tu archivo Excel de Materiales", type=["xlsx", "xls"])

# --- 3. PROCESAMIENTO DE DATOS ---
if archivo_subido is not None:
    try:
        # Leemos el Excel
        df = pd.read_excel(archivo_subido, header=0)

        # Verificamos que el archivo tenga suficientes columnas (al menos hasta la O, que es la 15)
        if df.shape[1] < 15:
            st.error("⚠️ El archivo cargado no tiene suficientes columnas. Necesito al menos hasta la columna O.")
        else:
            # --- CÁLCULO DE MÉTRICAS (TU REQUERIMIENTO) ---
            
            # 1. SC Generadas (Columna A = índice 0)
            # "Dame el total de datos contando las repetidas como si fueran el mismo" -> .nunique()
            columna_A = df.iloc[:, 0]
            total_sc_generadas = columna_A.nunique()

            # 2. SC Recibidas (Columna O = índice 14)
            # "Considera solo las que empiecen con 'RE'"
            columna_O = df.iloc[:, 14].astype(str).str.strip() # Convertimos a texto y limpiamos espacios
            # Filtramos solo las que empiezan con RE
            sc_recibidas = columna_O[columna_O.str.startswith('RE')].count()
            
            # 3. Cálculo de porcentaje de avance (Opcional pero útil)
            if total_sc_generadas > 0:
                avance = (sc_recibidas / total_sc_generadas) * 100
            else:
                avance = 0

            # --- 4. VISUALIZACIÓN DE LOS KPIs ---
            
            # Usamos columnas para que se vea alineado como en tu imagen
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(label="📋 SC Generadas", value=total_sc_generadas, help="Total de SC únicas en Columna A")
            
            with col2:
                st.metric(label="📦 SC Recibidas", value=sc_recibidas, delta=f"{avance:.1f}% Avance", help="Celdas en Columna O que inician con 'RE'")
            
            with col3:
                # Aquí puedes poner tus otras métricas si las tienes calculadas
                st.metric(label="Entregas a Tiempo (OTD)", value="En desarrollo")
                
            with col4:
                st.metric(label="Retraso Promedio", value="En desarrollo")

            st.write("---")

            # --- 5. (EXTRA) VISUALIZACIÓN GRÁFICA ---
            # Agrego esto para que el dashboard no se vea vacío
            st.subheader("Visualización de Progreso")
            
            datos_grafica = pd.DataFrame({
                'Estado': ['Generadas', 'Recibidas'],
                'Cantidad': [total_sc_generadas, sc_recibidas]
            })
            
            fig = px.bar(datos_grafica, x='Estado', y='Cantidad', 
                         color='Estado', 
                         title="Comparativa Generadas vs Recibidas",
                         text_auto=True,
                         color_discrete_sequence=['#1f77b4', '#2ca02c']) # Colores azul y verde
            
            st.plotly_chart(fig, use_container_width=True)

            # Mostrar tabla de datos al final (dentro de un desplegable para no ocupar espacio)
            with st.expander("🔍 Ver Base de Datos Completa"):
                st.dataframe(df)

    except Exception as e:
        st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
else:
    # Mensaje de bienvenida cuando no hay archivo
    st.info("👋 Hola. Por favor carga el archivo Excel para calcular los indicadores.")
