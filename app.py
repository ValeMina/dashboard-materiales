import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tablero de Control R-1926", layout="wide", page_icon="⚓")

DB_FILE = "db_materiales.json"

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

# --- PROCESAMIENTO DEL EXCEL (prioriza ESTATUS GRN) ---
def procesar_nuevo_excel(df_raw: pd.DataFrame):
    """
    Lógica:
    - Items solicitados: todas las filas con 'CANT ITEM S.C.' no nulo.
    - Items recibidos: filas con ESTATUS GRN == 'RECV'.
    - Tabla Gestión de Pedidos: SOLO items recibidos.
    Columnas clave según tu archivo. [file:3]
    """
    columnas_necesarias = [
        "No. S.C.",
        "CANT ITEM S.C.",
        "DESCRIPCION DE LA PARTIDA",
        "No. O.C.",
        "FECHA DE LLEGADA",
        "ESTATUS GRN",
    ]
    faltan = [c for c in columnas_necesarias if c not in df_raw.columns]
    if faltan:
        return {"error": f"Faltan columnas en el archivo: {faltan}"}

    # 1) Items solicitados: simplemente filas con cantidad en CANT ITEM S.C.
    df_solicitados = df_raw[df_raw["CANT ITEM S.C."].notna()].copy()
    items_solicitados = int(df_solicitados["CANT ITEM S.C."].count())

    # 2) Items recibidos: ESTATUS GRN == 'RECV' (PRIORIDAD)
    col_grn = df_raw["ESTATUS GRN"].astype(str).str.strip()
    df_recibidos = df_raw[col_grn == "RECV"].copy()
    items_recibidos = len(df_recibidos)

    # 3) Otros KPIs (respecto a solicitados)
    items_sin_oc = int(df_solicitados["No. O.C."].isna().sum())
    avance = (items_recibidos / items_solicitados * 100) if items_solicitados > 0 else 0.0

    # 4) TABLA: SOLO ITEMS RECIBIDOS (filtrados por ESTATUS GRN)
    tabla_resumen = []
    for _, row in df_recibidos.iterrows():
        tabla_resumen.append({
            "SC": str(row["No. S.C."]) if pd.notnull(row["No. S.C."]) else "",
            "ITEM": str(row["DESCRIPCION DE LA PARTIDA"]) if pd.notnull(row["DESCRIPCION DE LA PARTIDA"]) else "",
            "CANTIDAD": str(row["CANT ITEM S.C."]) if pd.notnull(row["CANT ITEM S.C."]) else "",
            "ORDEN DE COMPRA": str(row["No. O.C."]) if pd.notnull(row["No. O.C."]) else "",
            "FECHA DE LLEGADA": str(row["FECHA DE LLEGADA"]) if pd.notnull(row["FECHA DE LLEGADA"]) else "",
            "ESTATUS GRN": str(row["ESTATUS GRN"]) if pd.notnull(row["ESTATUS GRN"]) else "",
            "LISTA DE PEDIDO": ""
        })

    # Para el expander de datos originales, mostramos solicitados
    data_preview = df_solicitados.fillna("").head(500).to_dict(orient="records")

    return {
        "kpis": {
            "items_requisitados": items_solicitados,
            "items_recibidos": items_recibidos,
            "items_sin_oc": items_sin_oc,
            "avance": avance,
        },
        "tabla_resumen": tabla_resumen,   # SOLO recibidos
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

# --- UI PRINCIPAL ---
st.markdown(
    """
    <h1 style='text-align: center;'>⚓ Dashboard: R-1926 MONFORTE DE LEMOS</h1>
    <p style='text-align: center;'>Sistema de Control de Materiales</p>
    """,
    unsafe_allow_html=True,
)
st.write("---")

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
            st.metric("Items Recibidos (GRN=RECV)", kpis["items_recibidos"])
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

        # TABLA: SOLO ITEMS RECIBIDOS (ESTATUS GRN = RECV)
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
                "ESTATUS GRN": st.column_config.TextColumn("Estatus GRN", disabled=True),
                "LISTA DE PEDIDO": st.column_config.TextColumn(
                    "📝 Lista de Pedido", disabled=not es_admin, width="medium"
                ),
            }

            st.success(
                f"✅ Mostrando {len(df_tabla)} items RECIBIDOS (ESTATUS GRN = 'RECV')."
            )

            df_editado = st.data_editor(
                df_tabla,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"editor_{proyecto['id']}",
            )

            if es_admin:
                if st.button("💾 Guardar Notas", type="primary"):
                    st.session_state.proyectos[indice_proyecto]["contenido"][
                        "tabla_resumen"
                    ] = df_editado.to_dict(orient="records")
                    guardar_datos(st.session_state.proyectos)
                    st.success("Guardado.")
                    st.rerun()
        else:
            st.warning("❌ No hay items con ESTATUS GRN = 'RECV'.")

        with st.expander("🔍 Ver Datos Originales (Items Solicitados)"):
            st.dataframe(pd.DataFrame(datos["data"]))
