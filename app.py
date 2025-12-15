import pandas as pd
import streamlit as st

# Supongamos que tu dataframe principal se llama 'df'
# Asegúrate de que 'df' ya esté cargado con pd.read_excel(...)

try:
    # --- CÁLCULO DE MÉTRICAS ---

    # 1. SC Generadas
    # Regla: Columna A, contar únicos (repetidas valen por 1).
    # iloc[:, 0] selecciona la primera columna (Columna A).
    total_sc_generadas = df.iloc[:, 0].nunique()

    # 2. SC Recibidas
    # Regla: Columna O, debe contener datos y empezar con "RE".
    # La columna O es la número 15, por lo tanto es el índice 14 (empezando de 0).
    
    # Primero convertimos a string para poder buscar texto y quitamos espacios vacíos
    columna_o = df.iloc[:, 14].astype(str).str.strip()
    
    # Filtramos: Que empiece con "RE"
    # Nota: Esto automáticamente excluye las celdas vacías o con otros datos
    sc_recibidas = columna_o[columna_o.str.startswith('RE')].count()


    # --- VISUALIZACIÓN EN STREAMLIT ---
    
    # Creamos columnas para mostrar los datos uno al lado del otro
    kpi1, kpi2, kpi3 = st.columns(3) # Dejo 3 por si quieres centrar o agregar otro, si no usa st.columns(2)

    with kpi1:
        st.metric(label="SC Generadas", value=total_sc_generadas)
    
    with kpi2:
        st.metric(label="SC Recibidas", value=sc_recibidas)
        
    # Opcional: Calcular un porcentaje de cumplimiento simple
    with kpi3:
        if total_sc_generadas > 0:
            porcentaje = (sc_recibidas / total_sc_generadas) * 100
            st.metric(label="% Avance", value=f"{porcentaje:.1f}%")
        else:
            st.metric(label="% Avance", value="0%")

except Exception as e:
    st.error(f"Error al calcular las métricas: {e}. Verifica que el Excel tenga columnas A y O.")
