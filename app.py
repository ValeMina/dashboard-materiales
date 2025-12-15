import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tablero de Control de Materiales", layout="wide")

# --- FUNCIÓN: GENERAR DATOS DE EJEMPLO (PREDEFINIDO) ---
def generar_datos_ejemplo():
    """
    Crea un DataFrame falso para que veas la app funcionando de inmediato.
    """
    data = {
        "NO. S.C.": ["SC-1001", "SC-1002", "SC-1003", "SC-1004", "SC-1005", "SC-1006"],
        "TITULO DE LA REQUISICION": [
            "TUBERÍA ACERO CARBON", 
            "VÁLVULAS MARIPOSA", 
            "BRIDAS 4 PULGADAS", 
            "SOLDADURA ELECTRODOS", 
            "PINTURA EPOXICA",
            "TORNILLERÍA G.5"
        ],
        "ESTATUS S.C.": ["APROBADA", "EN FIRMA", "APROBADA", "CANCELADA", "APROBADA", "APROBADA"],
        "ESTATUS O.C.": ["COLOCADA", "PENDIENTE", "ENTREGADA", "CANCELADA", "COLOCADA", "PARCIAL"],
        # Fechas simuladas
        "FECHA PROMETIDA": [
            datetime.date(2025, 1, 15), # Pasada
            datetime.date(2025, 2, 20),
            datetime.date(2025, 1, 10),
            None,
            datetime.date(2025, 1, 30), # Pasada
            datetime.date(2025, 3, 1)
        ],
        "FECHA DE LLEGADA": [
            None, # No ha llegado (Critico si fecha prometida ya pasó)
            None,
            datetime.date(2025, 1, 12),
            None,
            None,
            datetime.date(2025, 1, 5) # Llegó parcial
        ],
        "CANT DISPONIBLE": [0, 0, 50, 0, 10, 100]
    }
    return pd.DataFrame(data)

# --- FUNCIÓN: PROCESAMIENTO DE DATOS ---
def procesar_reporte(df):
    """
    Toma el Excel (o los datos de ejemplo) y calcula los KPIs.
    """
    # 1. Limpieza básica de nombres de columnas
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # 2. KPIs Generales
    total_partidas = len(df)
    
    col_sc = "ESTATUS S.C." if "ESTATUS S.C." in df.columns else df.columns[0]
    col_oc = "ESTATUS O.C." if "ESTATUS O.C." in df.columns else ""
    
    # Conteo para gráficas
    conteo_sc = df[col_sc].value_counts() if col_sc in df.columns else pd.Series()
    conteo_oc = df[col_oc].value_counts() if col_oc in df.columns else pd.Series()
    
    # 3. Detección de Críticos (Retrasos)
    df_criticos = pd.DataFrame()
    
    if "FECHA PROMETIDA" in df.columns and "FECHA DE LLEGADA" in df.columns:
        # Asegurar formato fecha
        df["FECHA PROMETIDA"] = pd.to_datetime(df["FECHA PROMETIDA"], errors='coerce')
        df["FECHA DE LLEGADA"] = pd.to_datetime(df["FECHA DE LLEGADA"], errors='coerce')
        
        hoy = pd.Timestamp.now()
        
        # Lógica: Fecha prometida vencida Y (No ha llegado O llegó después)
        # Nota: Simplificamos a "No ha llegado" para el ejemplo
        retrasados = (df["FECHA PROMETIDA"] < hoy) & (df["FECHA DE LLEGADA"].isna())
        
        # Filtramos cancelados para que no salgan como críticos
        no_cancelado = ~df[col_sc].astype(str).str.contains("CANCELADA", na=False)
        
        df_criticos = df[retrasados & no_cancelado].copy()
        
        # Seleccionar solo columnas útiles para mostrar
        cols_mostrar = ["NO. S.C.", "TITULO DE LA REQUISICION", "FECHA PROMETIDA", col_oc]
        # Intersección para evitar error si falta alguna columna
        cols_finales = [c for c in cols_mostrar if c in df_criticos.columns]
        df_criticos = df_criticos[cols_finales]

    return total_partidas, conteo_sc, conteo_oc, df_criticos, df

# --- INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("📊 Tablero de Control de Materiales")
st.markdown("Este ejemplo carga datos **automáticamente** para evitar errores. Puedes subir tu archivo en la barra lateral.")

# --- BARRA LATERAL: CONTROL DE DATOS ---
with st.sidebar:
    st.header("Origen de Datos")
    opcion_datos = st.radio("Selecciona fuente:", ["Usar Ejemplo Demo", "Subir Excel Propio"])
    
    df_trabajo = None
    
    if opcion_datos == "Usar Ejemplo Demo":
        df_trabajo = generar_datos_ejemplo()
        st.info("Visualizando datos ficticios del sistema.")
    else:
        uploaded_file = st.file_uploader("Cargar Control de Materiales", type=["xlsx", "xls"])
        if uploaded_file:
            try:
                df_trabajo = pd.read_excel(uploaded_file)
                st.success("Archivo cargado correctamente.")
            except Exception as e:
                st.error(f"Error leyendo archivo: {e}")

# --- DASHBOARD PRINCIPAL ---
if df_trabajo is not None:
    # Procesar los datos
    total, data_sc, data_oc, df_criticos, df_limpio = procesar_reporte(df_trabajo)
    
    st.markdown("---")
    
    # 1. METRICAS (KPIs)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Partidas", total)
    col2.metric("Partidas con Retraso", len(df_criticos), delta_color="inverse")
    
    # Calcular % de avance (si hay estatus OC 'ENTREGADA' o 'RECIBIDA')
    if not data_oc.empty:
        entregadas = data_oc.get("ENTREGADA", 0) + data_oc.get("RECIBIDA", 0) + data_oc.get("CERRADA", 0)
        avance = (entregadas / total) * 100 if total > 0 else 0
        col3.metric("% Avance Recepción", f"{avance:.1f}%")
    else:
        col3.metric("% Avance", "N/A")

    # 2. GRAFICAS
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        st.subheader("Estatus Requisiciones (S.C.)")
        st.bar_chart(data_sc)
        
    with c_chart2:
        st.subheader("Estatus Órdenes (O.C.)")
        st.bar_chart(data_oc)

    # 3. TABLAS DETALLADAS
    st.markdown("---")
    tab1, tab2 = st.tabs(["🚨 Materiales Críticos (Retrasados)", "📋 Base de Datos Completa"])
    
    with tab1:
        if not df_criticos.empty:
            st.error("Los siguientes materiales tienen Fecha Prometida vencida y no han registrado llegada:")
            st.dataframe(df_criticos, use_container_width=True)
        else:
            st.success("¡Excelente! No hay materiales con retraso crítico.")
            
    with tab2:
        st.write("Visualización completa de los datos cargados:")
        st.dataframe(df_limpio, use_container_width=True)

else:
    st.warning("Esperando datos... Selecciona 'Usar Ejemplo Demo' o sube un archivo.")
