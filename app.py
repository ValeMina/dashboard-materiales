import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import datetime
import base64

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

# --- FUNCIONES PARA PDFs ---
def guardar_pdf(nombre_pdf, contenido_pdf):
    ruta_pdf = os.path.join(PDF_DIR, nombre_pdf)
    with open(ruta_pdf, "wb") as f:
        f.write(contenido_pdf)
    return nombre_pdf

def get_download_link(nombre_pdf):
    if nombre_pdf and os.path.exists(os.path.join(PDF_DIR, nombre_pdf)):
        with open(os.path.join(PDF_DIR, nombre_pdf), "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f"[📥 Descargar](data:application/pdf;base64,{b64})"
    return "❌ Sin LP Asignada"

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

# --- PROCESAR EXCEL ---
def procesar_nuevo_excel(df_raw: pd.DataFrame):
    """
    Filtra:
    - Columna O contiene 'RE'
    - Columna F (DESCRIPCION) NO contiene 'SERVICIO'
    Devuelve tabla con:
    A: No. S.C., D: CANT ITEM, F: DESCRIPCION, H: No. O.C.,
    M: FECHA LLEGADA, LISTA DE PEDIDO (texto editable), O: ESTATUS.
    """
    if df_raw.shape[1] < 15:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la O)."}

    # 1) Todos los items solicitados (D no nulo)
    df_solicitados = df_raw[df_raw.iloc[:, 3].notna()].copy()
    items_solicitados = int(len(df_solicitados))

    # Columnas para filtros
    col_o = df_solicitados.iloc[:, 14].astype(str).str.upper()   # O = estatus
    col_desc = df_solicitados.iloc[:, 5].astype(str).str.upper() # F = descripción

    # 2) Filtro: RE en O y NO "SERVICIO" en F
    mask_re = col_o.str.contains("RE", na=False)
    mask_no_servicio = ~col_desc.str.contains("SERVICIO", na=False)
    df_tabla = df_solicitados[mask_re & mask_no_servicio].copy()

    if df_tabla.empty:
        return {"error": "No hay filas con 'RE' en O y sin 'SERVICIO' en F."}

    # 3) Items recibidos (materiales con RE)
    items_recibidos = len(df_tabla)

    # 4) Items sin OC SOBRE TODOS LOS SOLICITADOS (columna H nula)
    items_sin_oc = int(df_solicitados.iloc[:, 7].isnull().sum())

    # 5) Avance global
    avance = (items_recibidos / items_solicitados * 100) if items_solicitados > 0 else 0.0

    # 6) Tabla resumen (solo materiales, sin servicios)
    tabla_resumen = []
    for idx, row in df_tabla.iterrows():
        sc = str(row.iloc[0]) if pd.notnull(row.iloc[0]) else ""
        cant = str(row.iloc[3]) if pd.notnull(row.iloc[3]) else ""
        desc = str(row.iloc[5]) if pd.notnull(row.iloc[5]) else ""
        oc = str(row.iloc[7]) if pd.notnull(row.iloc[7]) else ""
        fecha = str(row.iloc[12]) if pd.notnull(row.iloc[12]) else ""
        estatus = str(row.iloc[14]) if pd.notnull(row.iloc[14]) else ""

        tabla_resumen.append({
            "No. S.C.": sc,
            "CANT ITEM": cant,
            "DESCRIPCION": desc,
            "No. O.C.": oc,
            "FECHA LLEGADA": fecha,
            "LISTA DE PEDIDO": "",   # texto editable por admin
            "ESTATUS": estatus,
            "_row_index": int(idx),
        })

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

# --- REGENERAR EXISTENTES ---
def regenerar_tablas_existentes():
    if st.session_state.proyectos:
        with st.spinner("🔄 Regenerando tablas..."):
            for proyecto in st.session_state.proyectos:
                if "data" in proyecto["contenido"]:
                    df_raw = pd.DataFrame(proyecto["contenido"]["data"])
                    resultado = procesar_nuevo_excel(df_raw)
                    if "error" not in resultado:
                        proyecto["contenido"] = resultado
            guardar_datos(st.session_state.proyectos)
        st.success("✅ Tablas regeneradas.")
        st.rerun()

# --- SIDEBAR / ADMIN ---
es_admin = False
with st.sidebar:
    st.header("⚙️ Panel de Administración")
    password = st.text_input("Clave de Acceso", type="password")

    if password == "1234":
        es_admin = True
        st.success("🔓 Modo Editor Activo")
        st.markdown("---")

        if st.button("🔄 Regenerar Tablas"):
            regenerar_tablas_existentes()

        st.markdown("---")
        st.subheader("📤 Subir Nuevos Proyectos")
        archivos_subidos = st.file_uploader(
            "Archivos Excel/CSV", type=["xlsx", "xls", "csv"], accept_multiple_files=True
        )

        if st.button("Procesar y Guardar"):
            if archivos_subidos:
                for archivo_subido in archivos_subidos:
                    try:
                        if archivo_subido.name.endswith(".csv"):
                            df = pd.read_csv(archivo_subido, header=5)
                            archivo_subido.seek(0)
                            df_nombre = pd.read_csv(archivo_subido, header=None)
                        else:
                            df = pd.read_excel(archivo_subido, header=5)
                            archivo_subido.seek(0)
                            df_nombre = pd.read_excel(archivo_subido, header=None)

                        try:
                            nombre_proyecto = str(df_nombre.iloc[3, 2]).strip()
                        except Exception:
                            nombre_proyecto = archivo_subido.name

                        if not nombre_proyecto:
                            nombre_proyecto = archivo_subido.name

                        resultado = procesar_nuevo_excel(df)
                        if "error" in resultado:
                            st.error(f"{archivo_subido.name}: {resultado['error']}")
                        else:
                            nuevo_registro = {
                                "id": f"rep_{datetime.datetime.now().timestamp()}",
                                "nombre": nombre_proyecto,
                                "contenido": resultado,
                            }
                            st.session_state.proyectos.append(nuevo_registro)
                            guardar_datos(st.session_state.proyectos)
                            st.success(f"✅ '{nombre_proyecto}' guardado.")
                    except Exception as e:
                        st.error(f"{archivo_subido.name}: {e}")
                st.rerun()
            else:
                st.warning("Selecciona archivos.")

        st.markdown("---")
        if st.button("🗑️ Borrar Todo"):
            st.session_state.proyectos = []
            guardar_datos([])
            st.rerun()

# --- CONTENIDO PRINCIPAL ---
if not st.session_state.proyectos:
    st.info("👋 No hay reportes cargados.")
else:
    opciones = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("📂 Selecciona reporte:", opciones)

    indice_proyecto = next(
        (i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion), None
    )
    proyecto = st.session_state.proyectos[indice_proyecto]

    datos = proyecto["contenido"]
    kpis = datos["kpis"]

    st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Items Solicitados", kpis["items_requisitados"])
    with c2:
        st.metric("Items Recibidos", kpis["items_recibidos"])
    with c3:
        st.metric("Items sin OC", kpis["items_sin_oc"])
    with c4:
        st.metric("Avance", f"{kpis['avance']:.1f}%")
    st.write("---")

    col_graf, _ = st.columns([1, 0.1])
    with col_graf:
        df_graf = pd.DataFrame(
            {
                "Estado": ["Solicitados", "Recibidos", "Sin OC"],
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
                "Recibidos": "#2ecc71",
                "Sin OC": "#e74c3c",
            },
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.write("---")

    st.subheader("📋 Items con 'RE' en O (SERVICIOS excluidos)")
    raw_tabla = datos.get("tabla_resumen", [])

    if raw_tabla:
        df_tabla = pd.DataFrame(raw_tabla)

        # Para visualización: mostrar texto existente o mensaje por defecto
        df_mostrar = df_tabla.copy()
        for idx, row in df_mostrar.iterrows():
            nombre_lp = row.get("LISTA DE PEDIDO", "")
            df_mostrar.at[idx, "LISTA DE PEDIDO"] = (
                nombre_lp if nombre_lp else "❌ Sin LP Asignada"
            )

        column_config = {
            "No. S.C.": st.column_config.TextColumn("No. S.C.", disabled=True),
            "CANT ITEM": st.column_config.TextColumn("Cant.", disabled=True),
            "DESCRIPCION": st.column_config.TextColumn(
                "Descripción", width="medium", disabled=True
            ),
            "No. O.C.": st.column_config.TextColumn("O.C.", disabled=True),
            "FECHA LLEGADA": st.column_config.TextColumn("Fecha Llegada", disabled=True),
            "LISTA DE PEDIDO": st.column_config.TextColumn(
                "📋 Lista de Pedido",
                disabled=not es_admin,   # editable solo para admin
            ),
            "ESTATUS": st.column_config.TextColumn("Estatus", disabled=True),
        }

        df_editado = st.data_editor(
            df_mostrar.drop(columns=["_row_index"]),
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key=f"editor_{proyecto['id']}",
        )

        if es_admin:
            if st.button("💾 Guardar cambios en Lista de Pedido", type="primary"):
                df_tabla["LISTA DE PEDIDO"] = df_editado["LISTA DE PEDIDO"]
                st.session_state.proyectos[indice_proyecto]["contenido"]["tabla_resumen"] = (
                    df_tabla.to_dict(orient="records")
                )
                guardar_datos(st.session_state.proyectos)
                st.success("✅ Cambios guardados.")
                st.rerun()
    else:
        st.warning("❌ No hay items válidos.")
