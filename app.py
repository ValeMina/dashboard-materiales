import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Gestor Logístico Naval",
    page_icon="⚓",
    layout="wide"
)

# --- SISTEMA DE PERSISTENCIA (TU CÓDIGO REPLICADO) ---
DB_FILE = "db_proyectos.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_datos(lista_proyectos):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(lista_proyectos, f, default=str)

# Inicializar estado de la sesión
if 'proyectos' not in st.session_state:
    st.session_state.proyectos = cargar_datos()

# --- FUNCIONES DE PROCESAMIENTO ---
def procesar_archivo(uploaded_file):
    """Lee el archivo y detecta encabezados automáticamente."""
    try:
        # 1. Leer archivo
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # 2. Búsqueda dinámica del encabezado "No. S.C."
        if 'No. S.C.' not in df.columns:
            for i in range(20): 
                if uploaded_file.name.endswith('.csv'):
                    uploaded_file.seek(0)
                    df_temp = pd.read_csv(uploaded_file, header=i)
                else:
                    df_temp = pd.read_excel(uploaded_file, header=i)
                
                if 'No. S.C.' in df_temp.columns:
                    df = df_temp
                    break
        
        # 3. Limpieza de fechas (Crucial para el Dashboard)
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
    
    # Selector de Modo
    modo = st.radio("Ir a:", ["📊 Dashboard Operativo", "⚙️ Administración"], index=0)
    
    st.markdown("---")
    
    # Selector de Proyecto (Visual)
    proyecto_seleccionado = None
    if st.session_state.proyectos:
        st.subheader("Seleccionar Proyecto")
        # Creamos una lista solo con los nombres para el selectbox
        lista_nombres = [p['nombre'] for p in st.session_state.proyectos]
        nombre_sel = st.selectbox("Ver Control de:", lista_nombres)
        
        # Encontramos el proyecto completo en la lista
        proyecto_seleccionado = next((p for p in st.session_state.proyectos if p['nombre'] == nombre_sel), None)
    else:
        st.info("No hay proyectos cargados.")

# --- LÓGICA: ADMINISTRACIÓN ---
if modo == "⚙️ Administración":
    st.header("⚙️ Gestión de Controles")
    
    password = st.text_input("Contraseña de Administrador", type="password")
    
    if password == "admin123": # Puedes cambiar esto a "1234" si prefieres
        st.success("Modo Edición Activo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📥 Nuevo Proyecto")
            nuevo_archivo = st.file_uploader("Cargar Excel/CSV", type=['xlsx', 'csv'])
            nombre_nuevo = st.text_input("Nombre del Proyecto (Ej: R-1916)")
            
            if st.button("Guardar Proyecto", type="primary"):
                if nuevo_archivo and nombre_nuevo:
                    with st.spinner("Procesando..."):
                        df = procesar_archivo(nuevo_archivo)
                        if df is not None:
                            # TRUCO: Convertimos el DataFrame a JSON string para guardarlo
                            # usando tu sistema de persistencia
                            df_json = df.to_json(orient='split', date_format='iso')
                            
                            nuevo_obj = {
                                "nombre": nombre_nuevo,
                                "data": df_json,
                                "fecha_carga": str(datetime.now())
                            }
                            
                            # Agregar a la lista y guardar en archivo físico
                            st.session_state.proyectos.append(nuevo_obj)
                            guardar_datos(st.session_state.proyectos)
                            
                            st.success(f"✅ Proyecto '{nombre_nuevo}' guardado correctamente en db_proyectos.json")
                            st.rerun()
                else:
                    st.warning("Falta el archivo o el nombre.")
        
        with col2:
            st.markdown("### 🗑️ Eliminar Proyectos")
            if st.session_state.proyectos:
                # Mostrar lista para eliminar
                for i, proj in enumerate(st.session_state.proyectos):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"📂 **{proj['nombre']}**")
                    if c2.button("Borrar", key=f"del_{i}"):
                        st.session_state.proyectos.pop(i)
                        guardar_datos(st.session_state.proyectos)
                        st.rerun()
            else:
                st.caption("No hay proyectos guardados.")
                
    elif password:
        st.error("Contraseña incorrecta.")

# --- LÓGICA: DASHBOARD ---
elif modo == "📊 Dashboard Operativo":
    if proyecto_seleccionado is not None:
        # RECUPERAR DATOS: Reconvertimos el JSON guardado a DataFrame real
        try:
            df = pd.read_json(proyecto_seleccionado['data'], orient='split')
            
            # Asegurar que las fechas sean fechas (el JSON a veces las deja como texto)
            cols_fechas = ['FECHA PROMETIDA', 'FECHA DE LLEGADA']
            for col in cols_fechas:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    
        except Exception as e:
            st.error(f"Error recuperando datos del proyecto: {e}")
            st.stop()
        
        # --- AQUI EMPIEZA EL DASHBOARD EJECUTIVO (KPIs, GRAFICOS) ---
        
        # 1. Cálculos
        total_items = len(df)
        recibidos = df[df['ESTATUS GRN'] == 'RECV'].shape[0] if 'ESTATUS GRN' in df.columns else 0
        pct_avance = (recibidos / total_items) * 100 if total_items > 0 else 0
            
        otd_rate = 0
        dias_retraso_avg = 0
        if 'FECHA PROMETIDA' in df.columns and 'FECHA DE LLEGADA' in df.columns:
            df['Dias_Retraso'] = (df['FECHA DE LLEGADA'] - df['FECHA PROMETIDA']).dt.days
            entregados = df.dropna(subset=['FECHA DE LLEGADA'])
            a_tiempo = entregados[entregados['Dias_Retraso'] <= 0].shape[0]
            otd_rate = (a_tiempo / len(entregados)) * 100 if len(entregados) > 0 else 0
            retrasos = entregados[entregados['Dias_Retraso'] > 0]
            dias_retraso_avg = retrasos['Dias_Retraso'].mean() if not retrasos.empty else 0

        # 2. Título y KPIs
        st.title(f"⚓ Dashboard: {proyecto_seleccionado['nombre']}")
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Items", total_items)
        k2.metric("Material Recibido", recibidos, f"{pct_avance:.1f}%")
        k3.metric("Entregas a Tiempo (OTD)", f"{otd_rate:.1f}%", delta_color="inverse" if otd_rate < 80 else "normal")
        k4.metric("Retraso Promedio", f"{dias_retraso_avg:.1f} días", delta_color="inverse")
        
        st.markdown("---")
        
        # 3. Pestañas de Gráficos
        tab1, tab2, tab3 = st.tabs(["📊 Análisis Visual", "⏱️ Tiempos de Entrega", "📋 Base de Datos"])
        
        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                if 'ESTATUS GRN' in df.columns:
                    st.subheader("Distribución de Estatus")
                    fig = px.pie(df, names='ESTATUS GRN', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
            with c2:
                if 'DESCRIPCION DE LA PARTIDA' in df.columns:
                    st.subheader("Top Materiales Solicitados")
                    top = df['DESCRIPCION DE LA PARTIDA'].value_counts().head(10)
                    fig = px.bar(top, orientation='h')
                    st.plotly_chart(fig, use_container_width=True)
                    
        with tab2:
            st.subheader("Comparativa: Fecha Promesa vs. Real")
            st.markdown("Evaluación de cumplimiento de proveedores.")
            if 'FECHA PROMETIDA' in df.columns and 'FECHA DE LLEGADA' in df.columns:
                df_clean = df.dropna(subset=['FECHA PROMETIDA', 'FECHA DE LLEGADA'])
                fig = px.scatter(df_clean, x='FECHA PROMETIDA', y='FECHA DE LLEGADA', 
                                 color='Dias_Retraso', color_continuous_scale='RdYlGn_r',
                                 hover_data=['No. S.C.', 'DESCRIPCION DE LA PARTIDA'])
                # Línea de referencia ideal
                fig.add_shape(type="line", line=dict(dash="dash", color="gray"),
                    x0=df_clean['FECHA PROMETIDA'].min(), x1=df_clean['FECHA PROMETIDA'].max(),
                    y0=df_clean['FECHA PROMETIDA'].min(), y1=df_clean['FECHA PROMETIDA'].max())
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Este archivo no contiene columnas de fechas compatibles.")
        
        with tab3:
            st.subheader("Explorador de Datos")
            busqueda = st.text_input("🔍 Buscar material:")
            if busqueda:
                df_show = df[df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)]
                st.dataframe(df_show, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
            
    else:
        st.info("👈 Por favor selecciona un proyecto en el menú lateral.")
