import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero de Control R-1926", layout="wide", page_icon="⚓")

DB_FILE = "db_materiales.json"
PDF_DIR = "pdfs_listas_pedido"

# Crear directorio de PDFs si no existe
os.makedirs(PDF_DIR, exist_ok=True)

# --- LOGO Y TÍTULO ---
LOGO_URL = "https://github.com/ValeMina/dashboard-materiales/raw/8393550c123ddae68f49987994c72395e0339e67/logo%20tng.png"

col_logo, col_titulo = st.columns([1, 3])
with col_logo:
    st.image(LOGO_URL, use_column_width=True)
with col_titulo:
    st.markdown(
        """
        <h1 style='text-align: left; margin-bottom: 0;'>⚓ Dashboard: CONTROL DE MATERIALES</h1>
        <p style='text-align: left; margin-top: 0;'>Sistema de Control de Materiales</p>
        """,
        unsafe_allow_html=True,
    )

st.write("---")

# --- PERSISTENCIA ---
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

if "proyectos" not in st.session_state:
    st.session_state.proyectos = cargar_datos()

# --- PROCESAMIENTO DEL EXCEL ---
def procesar_nuevo_excel(df_raw: pd.DataFrame):
    """
    Tabla basada en FECHA DE LLEGADA válida.
    Columnas usadas por índice:
    - 0 (A): No. S.C.
    - 3 (D): CANT ITEM S.C.
    - 5 (F): DESCRIPCION DE LA PARTIDA
    - 7 (H): No. O.C.
    - 12 (M): FECHA DE LLEGADA
    Solo se consideran filas donde la columna M se puede interpretar como fecha.
    """
    # Verificar columnas suficientes
    if df_raw.shape[1] < 13:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la M)."}

    # 1) Items solicitados: filas con cantidad en columna D (índice 3)
    df_solicitados = df_raw[df_raw.iloc[:, 3].notna()].copy()
    items_solicitados = int(len(df_solicitados))

    # 2) Tabla: solo filas donde FECHA DE LLEGADA (M, índice 12) sea una fecha válida
    col_fecha_raw = df_solicitados.iloc[:, 12].astype(str).str.strip()
    fechas_parseadas = pd.to_datetime(col_fecha_raw, errors="coerce", dayfirst=True)
    df_tabla = df_solicitados[fechas_parseadas.notna()].copy()

    if df_tabla.empty:
        return {"error": 'No hay filas con FECHA DE LLEGADA en formato de fecha válido (por ejemplo "15/09/2025").'}

    # 3) Items recibidos (con fecha válida)
    items_recibidos = len(df_tabla)

    # 4) Otros KPIs (sobre solicitados)
    items_sin_oc = int(df_solicitados.iloc[:, 7].isnull().sum())  # No. O.C. (col H, índice 7)
    avance = (items_recibidos / items_solicitados * 100) if items_solicitados > 0 else 0.0

    # 5) Construir tabla_resumen
    tabla_resumen = []
    for _, row in df_tabla.iterrows():
        sc = str(row.iloc[0]) if pd.notnull(row.iloc[0]) else ""
        cant = str(row.iloc[3]) if pd.notnull(row.iloc[3]) else ""
        desc = str(row.iloc[5]) if pd.notnull(row.iloc[5]) else ""
        oc = str(row.iloc[7]) if pd.notnull(row.iloc[7]) else ""
        fecha = str(row.iloc[12]) if pd.notnull(row.iloc[12]) else ""

        tabla_resumen.append({
            "No. S.C.": sc,
            "CANT ITEM": cant,
            "DESCRIPCION": desc,
            "No. O.C.": oc,
            "FECHA LLEGADA": fecha,
            "LISTA DE PEDIDO": ""
        })

    # Datos originales (solicitados) para el expander
    data_preview = df_solicitados.fillna("").head(500).to_dict(orient="records")

    return {
        "kpis": {
            "items_requisitados": items_solicitados,
            "items_recibidos": items_recibidos,
            "items_sin_oc": items_sin_oc,
            "avance": avance,
        },
        "tabla_resumen": tabla_resumen,
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

# --- UI PRINCIPAL ---
es_admin = False

# --- SIDEBAR ---
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
                    if archivo_subido.name.endswith(".csv"):
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
                            "contenido": resultado,
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

# --- CONTENIDO PRINCIPAL ---
if not st.session_state.proyectos:
    st.info("👋 No hay reportes cargados.")
else:
    opciones = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("📂 Selecciona reporte:", opciones)

    indice_proyecto = next(
        (i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion),
        None,
    )
    proyecto = st.session_state.proyectos[indice_proyecto]

    if proyecto:
        datos = proyecto["contenido"]
        kpis = datos["kpis"]

        st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Items Solicitados", kpis["items_requisitados"])
        with c2:
            st.metric("Items con Fecha (válida)", kpis["items_recibidos"])
        with c3:
            st.metric("Items sin OC", kpis["items_sin_oc"])
        with c4:
            st.metric("Avance", f"{kpis['avance']:.1f}%")
        st.write("---")

        # GRÁFICA
        col_graf, _ = st.columns([1, 0.1])
        with col_graf:
            df_graf = pd.DataFrame(
                {
                    "Estado": ["Solicitados", "Con Fecha válida", "Sin OC"],
                    "Cantidad": [
                        kpis["items_requisitados"],
                        kpis["items_recibidos"],
                        kpis["items_sin_oc"],
                    ],
                }
            )
            fig = px.bar(
                df_graf,
                x="Estado",
                y="Cantidad",
                color="Estado",
                text_auto=True,
                color_discrete_map={
                    "Solicitados": "#3498db",
                    "Con Fecha válida": "#2ecc71",
                    "Sin OC": "#e74c3c",
                },
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.write("---")

        # TABLA DE GESTIÓN DE PEDIDOS
        st.subheader("📋 Gestión de Pedidos (Solo con FECHA DE LLEGADA válida)")
        raw_tabla = datos.get("tabla_resumen", [])

        if raw_tabla:
            df_tabla = pd.DataFrame(raw_tabla)

            st.success(f"✅ Mostrando {len(df_tabla)} items con FECHA DE LLEGADA válida.")

            column_config = {
                "No. S.C.": st.column_config.TextColumn("No. S.C.", disabled=True),
                "CANT ITEM": st.column_config.TextColumn("Cant.", disabled=True),
                "DESCRIPCION": st.column_config.TextColumn("Descripción", disabled=True),
                "No. O.C.": st.column_config.TextColumn("O.C.", disabled=True),
                "FECHA LLEGADA": st.column_config.TextColumn("Fecha Llegada", disabled=True),
                "LISTA DE PEDIDO": st.column_config.TextColumn(
                    "📝 Lista de Pedido", disabled=not es_admin, width="medium"
                ),
            }

            df_editado = st.data_editor(
                df_tabla,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"editor_{proyecto['id']}",
            )

            # Guardar tabla editada
            if es_admin:
                if st.button("💾 Guardar Tabla", type="primary"):
                    st.session_state.proyectos[indice_proyecto]["contenido"][
                        "tabla_resumen"
                    ] = df_editado.to_dict(orient="records")
                    guardar_datos(st.session_state.proyectos)
                    st.success("Tabla guardada.")
                    st.rerun()

            # SECCIÓN ADMIN: SUBIR PDFS POR No. S.C.
            if es_admin:
                st.write("---")
                st.subheader("📁 Gestión de PDFs (Admin)")

                scs_unicos = df_tabla["No. S.C."].unique().tolist()

                sc_seleccionado = st.selectbox(
                    "Selecciona No. S.C. para asignar PDF:",
                    options=scs_unicos,
                    key=f"sc_select
