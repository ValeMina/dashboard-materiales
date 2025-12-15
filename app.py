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

# --- LÓGICA DE PROCESAMIENTO (ACTUALIZADA) ---
def procesar_nuevo_excel(df_raw):
    """
    Calcula KPIs y genera la Tabla Resumen con las columnas específicas.
    Aplica filtro numérico en columna A.
    """
    # Verificación mínima de columnas
    if df_raw.shape[1] < 15:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la O)."}

    # --- 0. FILTRADO INICIAL (NUEVO) ---
    # Convertimos la columna A (índice 0) a numérico, forzando errores a NaN
    # Esto elimina encabezados repetidos, filas vacías o texto basura.
    df_raw['SC_Numeric'] = pd.to_numeric(df_raw.iloc[:, 0], errors='coerce')
    
    # Creamos un dataframe limpio solo con las filas válidas
    df = df_raw[df_raw['SC_Numeric'].notna()].copy()

    # --- 1. CÁLCULO DE KPIs (Usando el DF filtrado) ---
    # Items Requisitados (Columna F = índice 5)
    items_requisitados = int(df.iloc[:, 5].count())
    
    # Items Recibidos (Columna O = índice 14, empieza con 'RE')
    columna_O = df.iloc[:, 14].astype(str).str.strip()
    items_recibidos = int(columna_O[columna_O.str.startswith('RE')].count())

    # Items sin OC (Columna H = índice 7, vacíos)
    # En pandas, isnull() o celdas vacías
    items_sin_oc = int(df.iloc[:, 7].isnull().sum())

    # Porcentaje de Avance
    if items_requisitados > 0:
        avance = (items_recibidos / items_requisitados) * 100
    else:
        avance = 0.0

    # --- 2. GENERACIÓN DE LA TABLA "LISTA DE PEDIDO" ---
    tabla_resumen = []
    
    # Iteramos sobre el dataframe YA FILTRADO
    for index, row in df.iterrows():
        # Mapeo según tus indicaciones:
        # "SC" = Celda A (índice 0)
        # "CANTIDAD" = Celda D (índice 3)
        # "ITEM" = Celda F (índice 5)
        # "ORDEN DE COMPRA" = Celda H (índice 7)
        # "FECHA DE LLEGADA" = Celda M (índice 12)
        
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
            "LISTA DE PEDIDO": ""  # Campo editable (inicialmente vacío)
        })

    # Datos completos para vista previa (usamos el df filtrado para que se vea limpio)
    # Eliminamos la columna auxiliar de filtrado antes de mostrar
    if 'SC_Numeric' in df.columns:
        df_clean_preview = df.drop(columns=['SC_Numeric'])
    else:
        df_clean_preview = df

    data_preview = df_clean_preview.fillna("").head(500).to_dict(orient='records')

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

# Estado de admin
es_admin = False

# --- BARRA LATERAL (ADMINISTRACIÓN) ---
with st.sidebar:
    st.header("⚙️ Panel de Administración")
    
    password = st.text_input("Clave de Acceso", type="password")
    
    if password == "1234":
        es_admin = True
        st.success("🔓 Modo Editor Activo")
        st.markdown("---")
        
        st.subheader("📤 Subir Nuevo Proyecto")
        nombre_proyecto = st.text_input("Nombre del Reporte (Ej. Semana 4)")
        archivo_subido = st.file_uploader("Archivo Excel", type=["xlsx", "xls", "csv"])
        
        if st.button("Procesar y Guardar"):
            if nombre_proyecto and archivo_subido:
                try:
                    # AJUSTE IMPORTANTE: header=5
                    # El índice 5 corresponde a la fila 6 (donde están los títulos)
                    # Los datos comenzarán en la fila 7.
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
                        st.success(f"Reporte '{nombre_proyecto}' guardado correctamente (Datos numéricos filtrados).")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error crítico al leer el archivo: {e}")
            else:
                st.warning("Debes poner un nombre y subir un archivo.")

        st.markdown("---")
        st.subheader("🗑️ Limpieza")
        if st.button("Borrar TODOS los reportes"):
            st.session_state.proyectos = []
            guardar_datos([])
            st.rerun()
            st.success("Base de datos limpia.")
            
    else:
        st.info("Introduce la clave '1234' para gestionar archivos.")

# --- ÁREA PRINCIPAL ---

if not st.session_state.proyectos:
    st.info("👋 No hay reportes cargados. Ve al panel admin y sube el Excel.")
else:
    # Selector de proyecto
    opciones = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("📂 Selecciona el reporte a visualizar:", opciones)
    
    indice_proyecto = next((i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion), None)
    proyecto = st.session_state.proyectos[indice_proyecto]
    
    if proyecto:
        datos = proyecto["contenido"]
        kpis = datos["kpis"]
        
        st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")
        
        # 1. KPI CARDS
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Items Requisitados", kpis["items_requisitados"], help="Conteo de Items válidos")
        with c2: st.metric("Items Recibidos", kpis["items_recibidos"], help="Estatus 'RECV' en Col O")
        with c3: st.metric("Items sin OC", kpis["items_sin_oc"], help="Columna H vacía")
        with c4: st.metric("Porcentaje de Avance", f"{kpis['avance']:.1f}%", delta="Progreso Global")
            
        st.write("---")
        
        # 2. GRÁFICAS
        col_graf, _ = st.columns([1, 0.1])
        with col_graf:
            df_graf = pd.DataFrame({
                'Estado': ['Requisitados', 'Recibidos', 'Sin OC'],
                'Cantidad': [kpis["items_requisitados"], kpis["items_recibidos"], kpis["items_sin_oc"]]
            })
            fig = px.bar(df_graf, x='Estado', y='Cantidad', color='Estado', text_auto=True,
                         color_discrete_map={'Requisitados': '#3498db', 'Recibidos': '#2ecc71', 'Sin OC': '#e74c3c'}, height=300)
            st.plotly_chart(fig, use_container_width=True)

        st.write("---")
        
        # 3. TABLA DE LISTA DE PEDIDO
        st.subheader("📋 Gestión de Pedidos y Detalles")
        
        raw_tabla = datos.get("tabla_resumen", [])
        
        if raw_tabla:
            df_tabla = pd.DataFrame(raw_tabla)

            column_config = {
                "SC": st.column_config.TextColumn("SC (Col A)", disabled=True),
                "ITEM": st.column_config.TextColumn("Item (Col F)", disabled=True),
                "CANTIDAD": st.column_config.TextColumn("Cant. (Col D)", disabled=True),
                "ORDEN DE COMPRA": st.column_config.TextColumn("O.C. (Col H)", disabled=True),
                "FECHA DE LLEGADA": st.column_config.TextColumn("Llegada (Col M)", disabled=True),
                "LISTA DE PEDIDO": st.column_config.TextColumn(
                    "📝 Lista de Pedido (Notas)", 
                    disabled=not es_admin,
                    width="medium",
                    help="Escribe aquí notas. Solo se guardan si eres Admin."
                )
            }

            st.info(f"Mostrando {len(df_tabla)} items importados (Filtrados numéricamente).")

            df_editado = st.data_editor(
                df_tabla,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"editor_{proyecto['id']}"
            )

            if es_admin:
                col_save, _ = st.columns([1, 4])
                with col_save:
                    if st.button("💾 Guardar Notas de Pedido", type="primary"):
                        st.session_state.proyectos[indice_proyecto]["contenido"]["tabla_resumen"] = df_editado.to_dict(orient="records")
                        guardar_datos(st.session_state.proyectos)
                        st.success("¡Notas guardadas exitosamente!")
                        st.rerun()
        else:
            st.warning("⚠️ Reporte antiguo o vacío. Borra y sube de nuevo.")

        st.write("---")

        # 4. VISTA PREVIA
        with st.expander("🔍 Ver Datos Originales (Filtrados)"):
            df_visual = pd.DataFrame(datos["data"])
            st.dataframe(df_visual)
