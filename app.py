import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero de Control R-1926", layout="wide", page_icon="⚓")

# Archivo para persistencia de datos (base de datos simple)
DB_FILE = "db_materiales.json"

# --- FUNCIONES DE PERSISTENCIA ---
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

# Inicializar estado de sesión
if 'proyectos' not in st.session_state:
    st.session_state.proyectos = cargar_datos()

# --- LÓGICA DE PROCESAMIENTO (LA NUEVA LÓGICA DE KPIs) ---
def procesar_nuevo_excel(df):
    """
    Calcula los KPIs específicos (Columnas F, O, H) y prepara los datos para guardar.
    """
    # Verificación de estructura
    if df.shape[1] < 15:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la O)."}

    # 1. Items Requisitados (Columna F = índice 5)
    # Contar todos los datos no vacíos
    items_requisitados = int(df.iloc[:, 5].count())

    # 2. Items Recibidos (Columna O = índice 14)
    # Empiezan con "RE"
    columna_O = df.iloc[:, 14].astype(str).str.strip()
    items_recibidos = int(columna_O[columna_O.str.startswith('RE')].count())

    # 3. Items sin OC (Columna H = índice 7)
    # Contar vacíos
    items_sin_oc = int(df.iloc[:, 7].isnull().sum())

    # 4. Porcentaje
    if items_requisitados > 0:
        avance = (items_recibidos / items_requisitados) * 100
    else:
        avance = 0.0

    # Convertimos el DataFrame a diccionario para poder guardarlo en JSON
    # (Solo guardamos las primeras 500 filas para no hacer pesado el JSON, 
    # si necesitas todo, quita el .head(500))
    data_preview = df.fillna("").to_dict(orient='records')

    return {
        "kpis": {
            "items_requisitados": items_requisitados,
            "items_recibidos": items_recibidos,
            "items_sin_oc": items_sin_oc,
            "avance": avance
        },
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# --- INTERFAZ GRÁFICA ---

st.markdown("""
    <h1 style='text-align: center;'>⚓ Dashboard: R-1926 MONFORTE DE LEMOS</h1>
    <p style='text-align: center;'>Sistema de Control de Materiales</p>
    """, unsafe_allow_html=True)
st.write("---")

# --- BARRA LATERAL (ADMINISTRACIÓN) ---
with st.sidebar:
    st.header("⚙️ Panel de Administración")
    
    password = st.text_input("Clave de Acceso", type="password")
    
    if password == "1234":
        st.success("🔓 Modo Editor Activo")
        st.markdown("---")
        
        st.subheader("📤 Subir Nuevo Proyecto")
        nombre_proyecto = st.text_input("Nombre del Reporte (Ej. Semana 4)")
        archivo_subido = st.file_uploader("Archivo Excel", type=["xlsx", "xls"])
        
        if st.button("Procesar y Guardar"):
            if nombre_proyecto and archivo_subido:
                try:
                    df = pd.read_excel(archivo_subido, header=0)
                    resultado = procesar_nuevo_excel(df)
                    
                    if "error" in resultado:
                        st.error(resultado["error"])
                    else:
                        nuevo_registro = {
                            "id": f"rep_{datetime.datetime.now().timestamp()}",
                            "nombre": nombre_proyecto,
                            "contenido": resultado
                        }
                        
                        st.session_state.proyectos.append(nuevo_registro)
                        guardar_datos(st.session_state.proyectos)
                        st.success(f"Reporte '{nombre_proyecto}' guardado correctamente.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error crítico: {e}")
            else:
                st.warning("Debes poner un nombre y subir un archivo.")

        st.markdown("---")
        st.subheader("🗑️ Limpieza")
        if st.button("Borrar TODOS los reportes"):
            st.session_state.proyectos = []
            guardar_datos([])
            st.rerun()
            
    else:
        st.info("Introduce la clave '1234' para subir nuevos archivos.")

# --- ÁREA PRINCIPAL (VISUALIZACIÓN) ---

if not st.session_state.proyectos:
    st.info("👋 No hay reportes cargados en el sistema. Usa el panel izquierdo para subir el primer Excel.")
else:
    # Selector de proyecto
    opciones = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("📂 Selecciona el reporte a visualizar:", opciones)
    
    # Obtener datos del proyecto seleccionado
    proyecto = next((p for p in st.session_state.proyectos if p["nombre"] == seleccion), None)
    
    if proyecto:
        datos = proyecto["contenido"]
        kpis = datos["kpis"]
        
        st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")
        
        # --- 1. VISUALIZACIÓN DE MÉTRICAS (Igual al código anterior) ---
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.metric("Items Requisitados", kpis["items_requisitados"], help="Columna F")
        with c2:
            st.metric("Items Recibidos", kpis["items_recibidos"], help="Columna O ('RE')")
        with c3:
            st.metric("Items sin OC", kpis["items_sin_oc"], help="Vacíos en Columna H")
        with c4:
            st.metric("Porcentaje de Avance", f"{kpis['avance']:.1f}%", delta="Progreso Global")
            
        st.write("---")
        
        # --- 2. GRÁFICAS ---
        col_graf, col_tabla = st.columns([1, 2])
        
        with col_graf:
            st.subheader("Gráfica de Estado")
            df_graf = pd.DataFrame({
                'Estado': ['Requisitados', 'Recibidos', 'Sin OC'],
                'Cantidad': [kpis["items_requisitados"], kpis["items_recibidos"], kpis["items_sin_oc"]]
            })
            
            fig = px.bar(df_graf, x='Estado', y='Cantidad', color='Estado', text_auto=True,
                         color_discrete_map={'Requisitados': '#3498db', 'Recibidos': '#2ecc71', 'Sin OC': '#e74c3c'})
            st.plotly_chart(fig, use_container_width=True)
            
        with col_tabla:
            st.subheader("Vista Previa de Datos")
            # Reconstruimos el DataFrame desde el JSON
            df_visual = pd.DataFrame(datos["data"])
            st.dataframe(df_visual, height=400)
