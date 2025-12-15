import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero de Control R-1926", layout="wide", page_icon="⚓")

# Archivo para persistencia de datos
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

# --- LÓGICA DE PROCESAMIENTO (MISMA LÓGICA QUE "Items recibidos") ---
def procesar_nuevo_excel(df_raw):
    """
    MISMOS CRITERIOS que "Items recibidos": 
    1. Col A numérica
    2. Col O empieza con 'RE'
    """
    if df_raw.shape[1] < 15:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la O)."}

    # --- FILTRADO 1: COLUMNA A (Número) ---
    df_raw['Temp_A_Num'] = pd.to_numeric(df_raw.iloc[:, 0], errors='coerce')
    df = df_raw[df_raw['Temp_A_Num'].notna()].copy()
    
    if df.empty:
        return {"error": "No se encontraron filas con SC numérico en la Columna A."}

    # --- FILTRADO 2: COLUMNA O empieza con 'RE' (IGUAL que Items recibidos) ---
    columna_O = df.iloc[:, 14].astype(str).str.strip()
    df = df[columna_O.str.startswith('RE')].copy()

    if df.empty:
        return {"error": "No hay items con estado 'RE' en columna O."}

    # --- CÁLCULO DE KPIs ---
    items_requisitados = int(df.iloc[:, 5].count())  # Items con RE
    items_recibidos = items_requisitados  # Todos los filtrados son recibidos
    items_sin_oc = int(df.iloc[:, 7].isnull().sum())
    avance = 100.0  # Todos son recibidos

    # --- TABLA RESUMEN (solo items con RE) ---
    tabla_resumen = []
    
    for index, row in df.iterrows():
        sc_val = str(row.iloc[0]) if pd.notnull(row.iloc[0]) else ""
        cant_val = str(row.iloc[3]) if pd.notnull(row.iloc[3]) else ""
        item_val = str(row.iloc[5]) if pd.notnull(row.iloc[5]) else ""
        oc_val = str(row.iloc[7]) if pd.notnull(row.iloc[7]) else ""
        fecha_val = str(row.iloc[12]) if pd.notnull(row.iloc[12]) else ""
        
        tabla_resumen.append({
            "SC": sc_val,
            "ITEM": item_val,
            "CANTIDAD": cant_val,
            "ORDEN DE COMPRA": oc_val,
            "FECHA DE LLEGADA": fecha_val,
            "LISTA DE PEDIDO": "",
            "ESTADO": "RE"  # Para referencia
        })

    data_preview = df.fillna("").head(500).to_dict(orient='records')

    return {
        "kpis": {
            "items_requisitados": items_requisitados,
            "items_recibidos": items_recibidos,
            "items_sin_oc": items_sin_oc,
            "avance": avance
        },
        "tabla_resumen": tabla_resumen,
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# --- INTERFAZ GRÁFICA ---
st.markdown("""
    <h1 style='text-align: center;'>⚓ Dashboard: R-1926 MONFORTE DE LEMOS</h1>
    <p style='text-align: center;'>Sistema de Control de Materiales</p>
    """, unsafe_allow_html=True)
st.write("---")

es_admin = False

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Panel de Administración")
    password = st.text_input("Clave de Acceso", type="password")
    
    if password == "1234":
        es_admin = True
        st.success("🔓 Modo Editor Activo")
        st.markdown("---")
        
        st.subheader("📤 Subir Nuevo Proyecto")
        nombre_proyecto = st.text_input("Nombre del Reporte (Ej. Semana 4)")
        archivo_subido = st.file_uploader("Archivo Excel/CSV", type=["xlsx", "xls", "csv"])
        
        if st.button("Procesar y Guardar"):
            if nombre_proyecto and archivo_subido:
                try:
                    if archivo_subido.name.endswith('.csv'):
                        df = pd.read_csv(archivo_subido, header=5)
                    else:
                        df = pd.read_excel(archivo_subido, header=5)
                    
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
                        st.success(f"Reporte '{nombre_proyecto}' guardado con éxito.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error crítico: {e}")
            else:
                st.warning("Falta nombre o archivo.")

        st.markdown("---")
        if st.button("🗑️ Borrar Todo"):
            st.session_state.proyectos = []
            guardar_datos([])
            st.rerun()
    else:
        st.info("Introduce la clave '1234'.")

# --- ÁREA PRINCIPAL ---
if not st.session_state.proyectos:
    st.info("👋 No hay reportes cargados.")
else:
    opciones = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("📂 Selecciona reporte:", opciones)
    
    indice_proyecto = next((i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion), None)
    proyecto = st.session_state.proyectos[indice_proyecto]
    
    if proyecto:
        datos = proyecto["contenido"]
        kpis = datos["kpis"]
        
        st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")
        
        # KPIS
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Items Recibidos", kpis["items_requisitados"], help="Col O = 'RE'")
        with c2: st.metric("Items Recibidos", kpis["items_recibidos"])
        with c3: st.metric("Items sin OC", kpis["items_sin_oc"])
        with c4: st.metric("Avance", f"{kpis['avance']:.1f}%")
        st.write("---")
        
        # GRÁFICA
        col_graf, _ = st.columns([1, 0.1])
        with col_graf:
            df_graf = pd.DataFrame({
                'Estado': ['Recibidos', 'Sin OC'],
                'Cantidad': [kpis["items_recibidos"], kpis["items_sin_oc"]]
            })
            fig = px.bar(df_graf, x='Estado', y='Cantidad', color='Estado', text_auto=True,
                         color_discrete_map={'Recibidos': '#2ecc71', 'Sin OC': '#e74c3c'}, height=300)
            st.plotly_chart(fig, use_container_width=True)

        st.write("---")
        
        # TABLA (SOLO items con 'RE' en columna O)
        st.subheader("📋 Gestión de Pedidos (Solo Items Recibidos)")
        raw_tabla = datos.get("tabla_resumen", [])
        
        if raw_tabla:
            df_tabla = pd.DataFrame(raw_tabla)
            
            column_config = {
                "SC": st.column_config.TextColumn("SC", disabled=True),
                "ITEM": st.column_config.TextColumn("Item", disabled=True),
                "CANTIDAD": st.column_config.TextColumn("Cant.", disabled=True),
                "ORDEN DE COMPRA": st.column_config.TextColumn("O.C.", disabled=True),
                "FECHA DE LLEGADA": st.column_config.TextColumn("Llegada", disabled=True),
                "ESTADO": st.column_config.TextColumn("Estado", disabled=True),
                "LISTA DE PEDIDO": st.column_config.TextColumn(
                    "📝 Lista de Pedido", 
                    disabled=not es_admin,
                    width="medium"
                )
            }
            
            st.info(f"🟢 Mostrando {len(df_tabla)} items RECIBIDOS (Col O = 'RE')")
            
            df_editado = st.data_editor(
                df_tabla,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"editor_{proyecto['id']}"
            )
            
            if es_admin:
                if st.button("💾 Guardar Notas", type="primary"):
                    st.session_state.proyectos[indice_proyecto]["contenido"]["tabla_resumen"] = df_editado.to_dict(orient="records")
                    guardar_datos(st.session_state.proyectos)
                    st.success("Guardado.")
                    st.rerun()
        else:
            st.warning("No hay items recibidos.")

        with st.expander("🔍 Ver Datos Originales"):
            st.dataframe(pd.DataFrame(datos["data"]))
