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
    Tabla basada en filtro de columna O que contenga 'RE' Y NO contenga 'SERVICIO' en columna F.
    Columnas usadas por índice:
    - 0 (A): No. S.C.
    - 3 (D): CANT ITEM S.C.
    - 5 (F): DESCRIPCION DE LA PARTIDA
    - 7 (H): No. O.C.
    - 12 (M): FECHA DE LLEGADA
    - 14 (O): ESTATUS
    """
    # Verificar columnas suficientes
    if df_raw.shape[1] < 15:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la O)."}

    # 1) Items solicitados: filas con cantidad en columna D (índice 3)
    df_solicitados = df_raw[df_raw.iloc[:, 3].notna()].copy()
    items_solicitados = int(len(df_solicitados))

    # 2) FILTRO DOBLE: columna O debe contener "RE" Y columna F NO debe contener "SERVICIO"
    col_o = df_solicitados.iloc[:, 14].astype(str).str.upper()      # COLUMNA O (ESTATUS)
    col_desc = df_solicitados.iloc[:, 5].astype(str).str.upper()    # COLUMNA F (DESCRIPCION)
    
    # Filtrar: RE en O Y NO SERVICIO en F
    mask_re = col_o.str.contains("RE", na=False)
    mask_no_servicio = ~col_desc.str.contains("SERVICIO", na=False)
    df_tabla = df_solicitados[mask_re & mask_no_servicio].copy()

    if df_tabla.empty:
        return {"error": "No hay filas donde la columna O contenga 'RE' y columna F NO contenga 'SERVICIO'."}

    # 3) Items recibidos (con 'RE' en O y sin 'SERVICIO' en F)
    items_recibidos = len(df_tabla)

    # 4) Items sin OC (excluyendo servicios)
    df_sin_servicio = df_solicitados[~col_desc.str.contains("SERVICIO", na=False)]
    items_sin_oc = int(df_sin_servicio.iloc[:, 7].isnull().sum())
    avance = (items_recibidos / items_solicitados * 100) if items_solicitados > 0 else 0.0

    # 5) Construir tabla_resumen SOLO con materiales (sin servicios)
    tabla_resumen = []
    for _, row in df_tabla.iterrows():
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
            "ESTATUS": estatus
        })

    # Datos originales para regeneración futura
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

# --- FUNCIÓN PARA REGENERAR TABLAS EXISTENTES ---
def regenerar_tablas_existentes():
    """Regenera tabla_resumen excluyendo SERVICIOS de columna F"""
    if st.session_state.proyectos:
        with st.spinner("🔄 Regenerando tablas (sin SERVICIOS en columna F)..."):
            for proyecto in st.session_state.proyectos:
                if "data" in proyecto["contenido"]:
                    df_raw = pd.DataFrame(proyecto["contenido"]["data"])
                    resultado = procesar_nuevo_excel(df_raw)
                    
                    if "error" not in resultado:
                        proyecto["contenido"] = resultado
            
            guardar_datos(st.session_state.proyectos)
            st.success("✅ Tablas regeneradas (SERVICIOS en columna F excluidos).")
            st.rerun()

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

        # BOTÓN REGENERAR
        if st.button("🔄 Regenerar Tablas (sin SERVICIOS)"):
            regenerar_tablas_existentes()

        st.markdown("---")

        # SUBIR NUEVOS PROYECTOS
        st.subheader("📤 Subir Nuevos Proyectos")
        archivos_subidos = st.file_uploader(
            "Archivos Excel/CSV",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
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
                            st.success(f"✅ '{nombre_proyecto}' guardado (sin SERVICIOS).")
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
        (i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion),
        None,
    )
    proyecto = st.session_state.proyectos[indice_proyecto]

    if proyecto:
        datos = proyecto["contenido"]
        kpis = datos["kpis"]

        st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")

        # KPIs (SIN SERVICIOS)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Items Solicitados", kpis["items_requisitados"])
        with c2:
            st.metric("Items con 'RE' (sin SERVICIOS)", kpis["items_recibidos"])
        with c3:
            st.metric("Items sin OC (sin SERVICIOS)", kpis["items_sin_oc"])
        with c4:
            st.metric("Avance", f"{kpis['avance']:.1f}%")
        st.write("---")

        # GRÁFICA (SIN SERVICIOS)
        col_graf, _ = st.columns([1, 0.1])
        with col_graf:
            df_graf = pd.DataFrame({
                "Estado": ["Solicitados", "Con 'RE' (sin SERVICIOS)", "Sin OC (sin SERVICIOS)"],
                "Cantidad": [kpis["items_requisitados"], kpis["items_recibidos"], kpis["items_sin_oc"]]
            })
            fig = px.bar(df_graf, x="Estado", y="Cantidad", color="Estado", text_auto=True,
                        color_discrete_map={
                            "Solicitados": "#3498db",
                            "Con 'RE' (sin SERVICIOS)": "#2ecc71",
                            "Sin OC (sin SERVICIOS)": "#e74c3c"
                        }, height=300)
            st.plotly_chart(fig, use_container_width=True)

        st.write("---")

        # TABLA (SIN SERVICIOS en COLUMNA F)
        st.subheader("📋 Items con 'RE' en O (SERVICIOS excluidos)")
        raw_tabla = datos.get("tabla_resumen", [])

        if raw_tabla:
            df_tabla = pd.DataFrame(raw_tabla)
            st.success(f"✅ {len(df_tabla)} items con 'RE' en O (sin SERVICIOS en F).")
            st.dataframe(df_tabla, use_container_width=True, hide_index=True)
        else:
            st.warning("❌ No hay items con 'RE' en O que no sean SERVICIOS.")
