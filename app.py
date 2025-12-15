import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Gestor Logístico Naval",
    page_icon="⚓",
    layout="wide"
)

# --- INICIALIZACIÓN DEL ESTADO (MEMORIA) ---
# Aquí es donde guardamos los proyectos para que no se borren al cambiar de vista
if 'proyectos' not in st.session_state:
    st.session_state['proyectos'] = {}  # Diccionario para guardar { "Nombre Proyecto": DataFrame }

# --- FUNCIONES DE CARGA Y LIMPIEZA ---
def procesar_archivo(uploaded_file):
    try:
        # Detectar tipo de archivo
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # Búsqueda dinámica del encabezado real (buscando "No. S.C.")
        if 'No. S.C.' not in df.columns:
            for i in range(15): # Busca en las primeras 15 filas
                if uploaded_file.name.endswith('.csv'):
                    # Rebobinar archivo para leer de nuevo
                    uploaded_file.seek(0)
                    df_temp = pd.read_csv(uploaded_file, header=i)
                else:
                    df_temp = pd.read_excel(uploaded_file, header=i)
                
                if 'No. S.C.' in df_temp.columns:
                    df = df_temp
                    break
        
        # Limpieza de fechas clave
        date_cols = ['FECHA PROMETIDA', 'FECHA DE LLEGADA']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        return None

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://img.icons8.com/ios-filled/100/1f77b4/cargo-ship.png", width=50)
    st.title("Navegación")
    
    # 1. SELECTOR DE VISTA (Admin vs Dashboard)
    modo = st.radio("Ir a:", ["📊 Dashboard Operativo", "⚙️ Administración"], index=0)
    
    st.markdown("---")
    
    # 2. SELECTOR DE PROYECTO (Solo visible si hay proyectos)
    proyecto_seleccionado = None
    if st.session_state['proyectos']:
        st.subheader("Seleccionar Proyecto")
        nombres_proyectos = list(st.session_state['proyectos'].keys())
        nombre_seleccionado = st.selectbox("Ver Control de:", nombres_proyectos)
        proyecto_seleccionado = st.session_state['proyectos'][nombre_seleccionado]
    else:
        st.info("No hay proyectos cargados. Ve a Administración.")

# --- LÓGICA: ADMINISTRACIÓN ---
if modo == "⚙️ Administración":
    st.header("⚙️ Panel de Administración de Controles")
    
    password = st.text_input("Contraseña de Administrador", type="password")
    
    if password == "admin123":
        st.success("Sesión de Administrador Activa")
        
        col_up1, col_up2 = st.columns(2)
        
        with col_up1:
            st.subheader("Subir Nuevo Control")
            nuevo_archivo = st.file_uploader("Cargar Excel/CSV", type=['xlsx', 'csv'])
            nombre_nuevo = st.text_input("Asignar Nombre al Proyecto (Ej: R-1916 Tropic Sun)")
            
            if st.button("Guardar Proyecto"):
                if nuevo_archivo and nombre_nuevo:
                    df_procesado = procesar_archivo(nuevo_archivo)
                    if df_procesado is not None:
                        st.session_state['proyectos'][nombre_nuevo] = df_procesado
                        st.success(f"Proyecto '{nombre_nuevo}' guardado exitosamente.")
                        st.rerun() # Recargar para actualizar lista
                else:
                    st.warning("Debes subir un archivo y ponerle un nombre.")
        
        with col_up2:
            st.subheader("Gestionar Proyectos Existentes")
            if st.session_state['proyectos']:
                for nombre in list(st.session_state['proyectos'].keys()):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"📂 **{nombre}**")
                    if c2.button("Eliminar", key=f"del_{nombre}"):
                        del st.session_state['proyectos'][nombre]
                        st.rerun()
            else:
                st.caption("No hay proyectos en memoria.")
    elif password:
        st.error("Contraseña incorrecta.")

# --- LÓGICA: DASHBOARD (VISUALIZACIÓN) ---
elif modo == "📊 Dashboard Operativo":
    if proyecto_seleccionado is not None:
        df = proyecto_seleccionado
        
        # --- CÁLCULOS KPI ---
        total_items = len(df)
        if 'ESTATUS GRN' in df.columns:
            recibidos = df[df['ESTATUS GRN'] == 'RECV'].shape[0]
            pct_avance = (recibidos / total_items) * 100 if total_items > 0 else 0
        else:
            recibidos = 0
            pct_avance = 0
            
        # OTD (On Time Delivery)
        otd_rate = 0
        dias_retraso_promedio = 0
        if 'FECHA PROMETIDA' in df.columns and 'FECHA DE LLEGADA' in df.columns:
            df['Dias_Retraso'] = (df['FECHA DE LLEGADA'] - df['FECHA PROMETIDA']).dt.days
            entregados = df.dropna(subset=['FECHA DE LLEGADA'])
            a_tiempo = entregados[entregados['Dias_Retraso'] <= 0].shape[0]
            otd_rate = (a_tiempo / len(entregados)) * 100 if len(entregados) > 0 else 0
            dias_retraso_promedio = entregados[entregados['Dias_Retraso'] > 0]['Dias_Retraso'].mean()

        # --- ENCABEZADO DASHBOARD ---
        st.title(f"⚓ Tablero de Control: {nombre_seleccionado}")
        
        # KPIs Superiores
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Partidas", total_items)
        k2.metric("Material Recibido", recibidos, f"{pct_avance:.1f}% Avance")
        k3.metric("OTD (A Tiempo)", f"{otd_rate:.1f}%", delta_color="inverse" if otd_rate < 85 else "normal")
        k4.metric("Promedio Retraso (Días)", f"{dias_retraso_promedio:.1f}", delta_color="inverse")
        
        st.divider()

        # --- PESTAÑAS DE ANÁLISIS ---
        tab_graf, tab_time, tab_data = st.tabs(["📊 Análisis Visual", "⏱️ Tiempos de Entrega", "📋 Datos Crudos"])
        
        with tab_graf:
            c1, c2 = st.columns(2)
            with c1:
                if 'ESTATUS GRN' in df.columns:
                    st.subheader("Estatus de Recepción")
                    fig_pie = px.pie(df, names='ESTATUS GRN', hole=0.4, title="Distribución de Estatus")
                    st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                if 'DESCRIPCION DE LA PARTIDA' in df.columns:
                    st.subheader("Top Materiales")
                    top = df['DESCRIPCION DE LA PARTIDA'].value_counts().head(8)
                    fig_bar = px.bar(top, orientation='h', title="Materiales más solicitados")
                    st.plotly_chart(fig_bar, use_container_width=True)

        with tab_time:
            st.subheader("Cumplimiento de Fechas: Promesa vs Realidad")
            if 'FECHA PROMETIDA' in df.columns and 'FECHA DE LLEGADA' in df.columns:
                df_clean = df.dropna(subset=['FECHA PROMETIDA', 'FECHA DE LLEGADA'])
                fig_sc = px.scatter(df_clean, x='FECHA PROMETIDA', y='FECHA DE LLEGADA', 
                                    color='Dias_Retraso', 
                                    hover_data=['No. S.C.', 'DESCRIPCION DE LA PARTIDA'],
                                    color_continuous_scale='RdYlGn_r')
                # Línea de referencia
                fig_sc.add_shape(type="line", line=dict(dash="dash", color="gray"),
                    x0=df_clean['FECHA PROMETIDA'].min(), x1=df_clean['FECHA PROMETIDA'].max(),
                    y0=df_clean['FECHA PROMETIDA'].min(), y1=df_clean['FECHA PROMETIDA'].max())
                st.plotly_chart(fig_sc, use_container_width=True)
                st.caption("Nota: Puntos sobre la línea punteada indican retraso.")
            else:
                st.warning("No se encontraron columnas de fecha válidas para este análisis.")

        with tab_data:
            st.dataframe(df, use_container_width=True)

    else:
        st.markdown("""
        <div style='text-align: center; margin-top: 50px;'>
            <h3>👈 Selecciona un proyecto en el menú lateral</h3>
            <p>O ve a la pestaña de <b>Administración</b> para cargar nuevos controles.</p>
        </div>
        """, unsafe_allow_html=True)
