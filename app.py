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

# --- LÓGICA DE PROCESAMIENTO ---
def procesar_nuevo_excel(df):
    """
    Calcula KPIs y genera la Tabla Resumen con las columnas específicas:
    A (SC), F (Item), D (Cantidad), H (OC), M (Llegada).
    """
    # Verificación mínima de columnas (necesitamos hasta la O que es la 14)
    if df.shape[1] < 15:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la O)."}

    # --- 1. CÁLCULO DE KPIs (Lógica anterior) ---
    # Items Requisitados (Columna F = índice 5)
    items_requisitados = int(df.iloc[:, 5].count())
    
    # Items Recibidos (Columna O = índice 14, empieza con 'RE')
    columna_O = df.iloc[:, 14].astype(str).str.strip()
    items_recibidos = int(columna_O[columna_O.str.startswith('RE')].count())

    # Items sin OC (Columna H = índice 7, vacíos)
    items_sin_oc = int(df.iloc[:, 7].isnull().sum())

    # Porcentaje de Avance
    if items_requisitados > 0:
        avance = (items_recibidos / items_requisitados) * 100
    else:
        avance = 0.0

    # --- 2. GENERACIÓN DE LA TABLA "LISTA DE PEDIDO" ---
    # Extraemos solo las columnas solicitadas por índice:
    # A=0 (SC), D=3 (Cantidad), F=5 (Item), H=7 (Orden Compra), M=12 (Fecha Llegada)
    
    tabla_resumen = []
    
    for index, row in df.iterrows():
        # Extracción segura de datos (convirtiendo a string para evitar errores)
        sc_val = str(row.iloc[0]) if pd.notnull(row.iloc[0]) else ""       # Columna A
        cant_val = str(row.iloc[3]) if pd.notnull(row.iloc[3]) else ""     # Columna D
        item_val = str(row.iloc[5]) if pd.notnull(row.iloc[5]) else ""     # Columna F
        oc_val = str(row.iloc[7]) if pd.notnull(row.iloc[7]) else ""       # Columna H
        fecha_val = str(row.iloc[12]) if pd.notnull(row.iloc[12]) else ""  # Columna M
        
        # Filtramos filas totalmente vacías para que no se llene de basura
        if sc_val == "" and item_val == "":
            continue

        tabla_resumen.append({
            "SC": sc_val,
            "ITEM": item_val,
            "CANTIDAD": cant_val,
            "ORDEN DE COMPRA": oc_val,
            "FECHA DE LLEGADA": fecha_val,
            "LISTA DE PEDIDO": ""  # Campo nuevo editable (inicia vacío)
        })

    # Datos completos para la vista previa inferior (primeras 500 filas)
    data_preview = df.fillna("").head(500).to_dict(orient='records')

    return {
        "kpis": {
            "items_requisitados": items_requisitados,
            "items_recibidos": items_recibidos,
            "items_sin_oc": items_sin_oc,
            "avance": avance
        },
        "tabla_resumen": tabla_resumen, # Aquí va la nueva tabla filtrada
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# --- INTERFAZ GRÁFICA ---

st.markdown("""
    <h1 style='text-align: center;'>⚓ Dashboard: R-1926 MONFORTE DE LEMOS</h1>
    <p style='text-align: center;'>Sistema de Control de Materiales</p>
    """, unsafe_allow_html=True)
st.write("---")

# Variable para controlar si el usuario es admin en esta sesión
es_admin = False

# --- BARRA LATERAL (ADMINISTRACIÓN) ---
with st.sidebar:
    st.header("⚙️ Panel de Administración")
    
    password = st.text_input("Clave de Acceso", type="password")
    
    if password == "1234":
        es_admin = True # ¡Contraseña correcta!
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
            st.success("Base de datos limpia. Sube los archivos de nuevo.")
            
    else:
        st.info("Introduce la clave '1234' para gestionar archivos y editar pedidos.")

# --- ÁREA PRINCIPAL (VISUALIZACIÓN) ---

if not st.session_state.proyectos:
    st.info("👋 No hay reportes cargados. Por favor, ingresa como admin (izquierda) y sube el archivo Excel para ver la nueva tabla.")
else:
    # Selector de proyecto
    opciones = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("📂 Selecciona el reporte a visualizar:", opciones)
    
    # Buscamos el índice para poder guardar cambios si se edita
    indice_proyecto = next((i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion), None)
    proyecto = st.session_state.proyectos[indice_proyecto]
    
    if proyecto:
        datos = proyecto["contenido"]
        kpis = datos["kpis"]
        
        st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")
        
        # 1. KPI CARDS
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Items Requisitados", kpis["items_requisitados"], help="Columna F")
        with c2: st.metric("Items Recibidos", kpis["items_recibidos"], help="Columna O ('RE')")
        with c3: st.metric("Items sin OC", kpis["items_sin_oc"], help="Columna H vacía")
        with c4: st.metric("Porcentaje de Avance", f"{kpis['avance']:.1f}%", delta="Progreso Global")
            
        st.write("---")
        
        # 2. GRÁFICAS KPI
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
        
        # --- 3. NUEVA SECCIÓN: TABLA DE LISTA DE PEDIDO ---
        st.subheader("📋 Gestión de Pedidos y Detalles")
        
        # Obtenemos la tabla generada en el procesamiento
        raw_tabla = datos.get("tabla_resumen", [])
        
        if raw_tabla:
            df_tabla = pd.DataFrame(raw_tabla)

            # CONFIGURACIÓN DE COLUMNAS (Qué se puede editar y qué no)
            column_config = {
                "SC": st.column_config.TextColumn("SC (Col A)", disabled=True),
                "ITEM": st.column_config.TextColumn("Item (Col F)", disabled=True),
                "CANTIDAD": st.column_config.TextColumn("Cant. (Col D)", disabled=True),
                "ORDEN DE COMPRA": st.column_config.TextColumn("O.C. (Col H)", disabled=True),
                "FECHA DE LLEGADA": st.column_config.TextColumn("Llegada (Col M)", disabled=True),
                # ESTA ES LA ÚNICA EDITABLE:
                "LISTA DE PEDIDO": st.column_config.TextColumn(
                    "📝 Lista de Pedido (Notas)", 
                    disabled=not es_admin,  # Bloqueado si no pusiste la clave 1234
                    width="medium",
                    help="Escribe aquí notas. Solo se guardan si eres Admin."
                )
            }

            st.info(f"Mostrando {len(df_tabla)} items. " + 
                    ("✅ Eres Admin: Puedes editar 'Lista de Pedido'." if es_admin else "🔒 Modo Lectura: Ingresa clave para editar."))

            # EDITOR DE DATOS
            df_editado = st.data_editor(
                df_tabla,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed", # No dejar agregar filas, solo editar las existentes
                key=f"editor_{proyecto['id']}"
            )

            # BOTÓN DE GUARDADO (Solo visible para Admin)
            if es_admin:
                col_save, _ = st.columns([1, 4])
                with col_save:
                    if st.button("💾 Guardar Notas de Pedido", type="primary"):
                        # Actualizamos la memoria
                        st.session_state.proyectos[indice_proyecto]["contenido"]["tabla_resumen"] = df_editado.to_dict(orient="records")
                        # Actualizamos el archivo
                        guardar_datos(st.session_state.proyectos)
                        st.success("¡Notas guardadas exitosamente!")
                        st.rerun()

        else:
            # Mensaje por si el usuario no ha borrado los reportes viejos
            st.warning("⚠️ Los datos guardados son antiguos. Por favor, ve al panel de Admin, borra los reportes y sube el Excel de nuevo.")

        st.write("---")

        # 4. VISTA PREVIA COMPLETA
        with st.expander("🔍 Ver Base de Datos Completa (Excel Original)"):
            df_visual = pd.DataFrame(datos["data"])
            st.dataframe(df_visual)
