import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import datetime
from pathlib import Path

st.set_page_config(page_title="Tablero de Control R-1926", layout="wide", page_icon="⚓")

DB_FILE = "db_materiales.json"

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
        json.dump(lista_proyectos, f, indent=2, ensure_ascii=False)

def procesar_nuevo_excel(df_raw):
    # 1) Items solicitados: filas con No. S.C. numérico (columna A, índice 0)
    df_solicitados = df_raw[pd.to_numeric(df_raw.iloc[:, 0], errors='coerce').notna()].copy()
    items_solicitados = int(len(df_solicitados))
    
    # 2) Filtrar por FECHA DE LLEGADA válida (columna M, índice 12)
    df_solicitados['fecha_temp'] = pd.to_datetime(df_solicitados.iloc[:, 12], dayfirst=True, errors='coerce')
    df_tabla = df_solicitados[df_solicitados['fecha_temp'].notna()].copy()
    
    if df_tabla.shape[1] <= 7:
        return {"error": "El archivo no tiene la columna H (índice 7) para O.C."}
    
    # ✅ NUEVO FILTRO: SOLO códigos numéricos en No. O.C. (columna H, índice 7), ORDENADOS
    col_oc_raw = df_tabla.iloc[:, 7].astype(str).str.strip()
    df_con_oc_numeric = df_tabla[col_oc_raw.str.contains(r'\d{3,}', regex=True, na=False)].copy()
    df_con_oc_numeric = df_con_oc_numeric.sort_values(by=df_con_oc_numeric.columns[7])
    
    # Construir tabla_resumen SOLO con O.C. numéricos
    tabla_resumen = []
    for _, row in df_con_oc_numeric.iterrows():
        sc = str(row.iloc[0]) if pd.notnull(row.iloc[0]) else ""      # Col A: No. S.C.
        cant = str(row.iloc[3]) if pd.notnull(row.iloc[3]) else ""    # Col D: CANT ITEM
        desc = str(row.iloc[5]) if pd.notnull(row.iloc[5]) else ""    # Col F: DESCRIPCION
        oc = str(row.iloc[7]) if pd.notnull(row.iloc[7]) else ""      # Col H: No. O.C. (NUMÉRICO)
        fecha = str(row.iloc[12]) if pd.notnull(row.iloc[12]) else "" # Col M: FECHA LLEGADA
        
        tabla_resumen.append({
            "No. S.C.": sc,
            "CANT ITEM": cant,
            "DESCRIPCION": desc,
            "No. O.C.": oc,
            "FECHA LLEGADA": fecha,
            "LISTA DE PEDIDO": ""
        })
    
    # KPIs
    items_recibidos = len(tabla_resumen)
    items_sin_oc = items_recibidos  # Ajustar según necesites
    avance = (items_recibidos / items_solicitados * 100) if items_solicitados > 0 else 0
    
    # Datos originales para expander
    data_preview = df_raw.head(100).to_dict('records')
    
    return {
        "kpis": {
            "items_solicitados": items_solicitados,
            "items_recibidos": items_recibidos,
            "items_sin_oc": items_sin_oc,
            "avance": round(avance, 1)
        },
        "tabla_resumen": tabla_resumen,
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# SIDEBAR - PASSWORD
password = st.sidebar.text_input("🔑 Clave de acceso:", type="password")
if password == "1234":
    st.sidebar.success("✅ Acceso autorizado")
else:
    st.sidebar.info("Introduce la clave '1234'.")
    st.stop()

# TÍTULO PRINCIPAL
st.title("⚓ Tablero de Control Materiales R-1926")

# CARGA DE ARCHIVO
uploaded_file = st.file_uploader("📁 Sube tu Excel", type=["xlsx", "xls"])
proyectos = cargar_datos()

if uploaded_file is not None:
    # Procesar Excel
    df_raw = pd.read_excel(uploaded_file)
    datos = procesar_nuevo_excel(df_raw)
    
    if "error" in datos:
        st.error(datos["error"])
        st.stop()
    
    # NOMBRE DEL PROYECTO (de C4)
    nombre_proyecto = df_raw.iloc[3, 2] if len(df_raw) > 3 and len(df_raw.columns) > 2 else "Sin nombre"
    
    # AGREGAR O ACTUALIZAR PROYECTO
    proyecto_existente = next((p for p in proyectos if p["nombre"] == str(nombre_proyecto)), None)
    if proyecto_existente:
        proyecto_existente.update(datos)
        proyecto_existente["ultima_actualizacion"] = datos["fecha_carga"]
    else:
        proyectos.append({
            "nombre": str(nombre_proyecto),
            **datos,
            "fecha_carga": datos["fecha_carga"],
            "ultima_actualizacion": datos["fecha_carga"]
        })
    
    guardar_datos(proyectos)
    st.success(f"✅ {nombre_proyecto} procesado y guardado!")
    
    # SELECCIÓN DE PROYECTO
    proyecto_seleccionado = st.selectbox(
        "📋 Selecciona proyecto:",
        ["Último cargado"] + [p["nombre"] for p in proyectos]
    )
    
    if proyecto_seleccionado == "Último cargado":
        datos = proyectos[-1] if proyectos else {}
    else:
        datos = next((p for p in proyectos if p["nombre"] == proyecto_seleccionado), {})
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Items Solicitados", datos["kpis"]["items_solicitados"])
    with col2:
        st.metric("Items Recibidos", datos["kpis"]["items_recibidos"])
    with col3:
        st.metric("Items sin O.C.", datos["kpis"]["items_sin_oc"])
    with col4:
        st.metric("Avance", f"{datos['kpis']['avance']}%")
    
    # GRÁFICA
    fig = px.pie(
        values=[datos["kpis"]["items_recibidos"], datos["kpis"]["items_solicitados"] - datos["kpis"]["items_recibidos"]],
        names=["Recibidos", "Pendientes"],
        color_discrete_map={"Recibidos": "#2ecc71", "Pendientes": "#e74c3c"},
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.write("")
    
    # 📋 TABLA GESTIÓN DE PEDIDOS (SOLO O.C. NUMÉRICO, ORDENADO)
    st.subheader("📋 Gestión de Pedidos (Solo con O.C. NUMÉRICO)")
    raw_tabla = datos.get("tabla_resumen", [])
    
    if raw_tabla:
        df_tabla = pd.DataFrame(raw_tabla)
        
        # EDITOR (SOLO ADMIN)
        if password == "1234":
            edited_df = st.data_editor(
                df_tabla,
                column_config={
                    "LISTA DE PEDIDO": st.column_config.TextColumn("LISTA DE PEDIDO", disabled=False)
                },
                use_container_width=True,
                hide_index=False
            )
            
            if st.button("💾 Guardar cambios"):
                # Actualizar proyecto en memoria
                if proyecto_seleccionado == "Último cargado":
                    proyectos[-1]["tabla_resumen"] = edited_df.to_dict('records')
                else:
                    for p in proyectos:
                        if p["nombre"] == proyecto_seleccionado:
                            p["tabla_resumen"] = edited_df.to_dict('records')
                            break
                guardar_datos(proyectos)
                st.success("Guardado.")
                st.rerun()
        else:
            st.dataframe(df_tabla, use_container_width=True)
    else:
        st.warning("❌ No hay items con O.C. NUMÉRICO (OC-123, ABC456, 12345, etc.)")
    
    # EXPANDER DATOS ORIGINALES
    with st.expander("🔍 Ver Datos Originales (Solicitados)"):
        st.dataframe(pd.DataFrame(datos["data"]))
