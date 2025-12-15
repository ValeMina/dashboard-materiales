import streamlit as st
import pandas as pd
import datetime
import os
import json
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión de Control de Materiales", layout="wide")

# Archivo de base de datos
DB_FILE = "db_proyectos_full.json"

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_datos():
    """Carga la lista de proyectos desde el JSON."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def guardar_datos(lista_proyectos):
    """Guarda la lista completa en el JSON."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(lista_proyectos, f, default=str)

def convertir_df_a_registros(df):
    """Convierte DataFrame a lista de diccionarios para guardar en JSON, manejando fechas."""
    # Convertir fechas a string para JSON
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%Y-%m-%d')
    return df.to_dict('records')

def procesar_datos_visualizacion(datos_lista):
    """
    Reconstruye el DataFrame desde la lista guardada y recastea tipos de datos.
    """
    df = pd.DataFrame(datos_lista)
    # Intentar recuperar fechas
    cols_posibles_fechas = ["FECHA PROMETIDA", "FECHA DE LLEGADA", "FECHA CREACION", "FECHA REQUERIDA"]
    for col in cols_posibles_fechas:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

# Inicializar estado
if 'proyectos' not in st.session_state:
    st.session_state.proyectos = cargar_datos()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 8px; border-left: 5px solid #1f4e79; }
    .header-title { color: #1f4e79; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏗️ Gestión Integral de Materiales")

# --- BARRA LATERAL (ADMIN) ---
with st.sidebar:
    st.header("⚙️ Administración")
    password = st.text_input("Clave de Acceso", type="password")
    
    if password == "1234":
        st.success("Modo Editor Activado")
        st.markdown("---")
        
        # 1. CARGA DE NUEVOS PROYECTOS
        with st.expander("📂 Cargar Nuevo Proyecto"):
            nuevo_nombre = st.text_input("Nombre del Proyecto")
            nuevo_archivo = st.file_uploader("Subir Excel", type=["xlsx", "xls"])
            
            if st.button("Procesar y Guardar"):
                if nuevo_nombre and nuevo_archivo:
                    try:
                        # Leer Excel
                        df = pd.read_excel(nuevo_archivo)
                        
                        # Limpiar nombres de columnas (Mayúsculas y sin espacios extra)
                        df.columns = [str(c).strip().upper() for c in df.columns]
                        
                        # Guardar estructura
                        nuevo_proyecto = {
                            "id": f"proj_{datetime.datetime.now().timestamp()}",
                            "nombre": nuevo_nombre,
                            "data": convertir_df_a_registros(df) # Guardamos TODA la data
                        }
                        
                        st.session_state.proyectos.append(nuevo_proyecto)
                        guardar_datos(st.session_state.proyectos)
                        st.success(f"Proyecto '{nuevo_nombre}' guardado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Falta nombre o archivo.")
        
        # 2. GESTIÓN (ELIMINAR)
        st.markdown("---")
        if st.button("🗑️ Eliminar TODOS los datos", type="primary"):
            st.session_state.proyectos = []
            guardar_datos([])
            st.rerun()

# --- ÁREA PRINCIPAL ---

if not st.session_state.proyectos:
    st.info("👈 No hay proyectos. Ingresa la clave '1234' en el menú lateral para cargar uno.")
else:
    # 1. SELECTOR DE PROYECTO
    nombres = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("Selecciona el Proyecto a visualizar/editar:", nombres)
    
    # Encontrar el índice del proyecto seleccionado
    idx_proyecto = next((i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion), None)
    
    if idx_proyecto is not None:
        proyecto_data_raw = st.session_state.proyectos[idx_proyecto]["data"]
        
        # Convertimos la data cruda a DataFrame para trabajar
        df_activo = procesar_datos_visualizacion(proyecto_data_raw)
        
        # --- PESTAÑAS DE TRABAJO ---
        tab_resumen, tab_detalle, tab_criticos = st.tabs(["📊 Resumen Ejecutivo", "📝 Edición y Detalle", "🚨 Críticos"])
        
        # --- TAB 1: RESUMEN (CÁLCULO EN TIEMPO REAL) ---
        with tab_resumen:
            st.markdown(f"### Estatus: {seleccion}")
            
            # Cálculos dinámicos (se actualizan si editas en la Tab 2)
            total_items = len(df_activo)
            
            # Verificar columnas existentes para evitar errores
            col_sc = "ESTATUS S.C." if "ESTATUS S.C." in df_activo.columns else df_activo.columns[0]
            col_oc = "ESTATUS O.C." if "ESTATUS O.C." in df_activo.columns else ""
            col_cant = "CANT DISPONIBLE" if "CANT DISPONIBLE" in df_activo.columns else ""
            
            # KPIs
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Partidas", total_items)
            
            if col_cant:
                total_disp = pd.to_numeric(df_activo[col_cant], errors='coerce').sum()
                c2.metric("Cantidad Disponible Total", f"{total_disp:,.2f}")
            
            # Gráficos
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("Estatus S.C.")
                if col_sc:
                    st.bar_chart(df_activo[col_sc].value_counts())
            
            with col_g2:
                st.subheader("Estatus O.C.")
                if col_oc:
                    st.bar_chart(df_activo[col_oc].value_counts())

        # --- TAB 2: EDICIÓN Y DETALLE (LO QUE PEDISTE) ---
        with tab_detalle:
            st.info("💡 Puedes editar las celdas directamente aquí. Al finalizar, presiona 'Guardar Cambios' abajo.")
            
            # EDITOR DE DATOS INTERACTIVO
            # num_rows="dynamic" permite añadir filas nuevas si quisieras
            df_editado = st.data_editor(
                df_activo, 
                num_rows="dynamic", 
                use_container_width=True,
                height=500,
                key="editor_datos"
            )
            
            # BOTÓN DE GUARDADO
            col_save, col_info = st.columns([1, 4])
            if col_save.button("💾 Guardar Cambios Realizados"):
                # Convertir el DF editado de vuelta a lista de diccionarios
                nueva_data = convertir_df_a_registros(df_editado)
                
                # Actualizar en memoria
                st.session_state.proyectos[idx_proyecto]["data"] = nueva_data
                
                # Guardar en archivo JSON
                guardar_datos(st.session_state.proyectos)
                
                st.success("✅ ¡Cambios guardados y reporte actualizado!")
                st.rerun() # Recargar para que los gráficos del Tab 1 tomen los nuevos datos

        # --- TAB 3: CRÍTICOS ---
        with tab_criticos:
            st.subheader("Filtrado Automático de Retrasos")
            
            # Lógica de críticos (igual que antes pero dinámica)
            if "FECHA PROMETIDA" in df_editado.columns and "FECHA DE LLEGADA" in df_editado.columns:
                hoy = pd.Timestamp.now()
                
                # Filtro: Fecha prometida vencida Y (Fecha llegada vacía O Estatus no entregado)
                # Esta lógica depende de tus datos, aquí un ejemplo genérico:
                mask_vencidos = (
                    (df_editado["FECHA PROMETIDA"] < hoy) & 
                    (df_editado["FECHA DE LLEGADA"].isna())
                )
                
                # Filtro: Cancelados
                mask_cancelados = pd.Series(False, index=df_editado.index)
                if col_sc:
                    mask_cancelados = df_editado[col_sc].astype(str).str.contains("CANCELADA", case=False, na=False)
                
                df_criticos = df_editado[mask_vencidos | mask_cancelados]
                
                if not df_criticos.empty:
                    st.error(f"Se encontraron {len(df_criticos)} partidas críticas.")
                    st.dataframe(df_criticos, use_container_width=True)
                else:
                    st.success("No hay materiales críticos pendientes por fecha.")
            else:
                st.warning("No se encontraron las columnas de fechas necesarias para calcular críticos.")
