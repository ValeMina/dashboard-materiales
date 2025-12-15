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
    Calcula KPIs y genera la Tabla Resumen específica solicitada.
    """
    if df.shape[1] < 15:
        return {"error": "El archivo no tiene suficientes columnas (mínimo hasta la O)."}

    # 1. KPIs (Lógica Intacta)
    items_requisitados = int(df.iloc[:, 5].count())
    
    columna_O = df.iloc[:, 14].astype(str).str.strip()
    items_recibidos = int(columna_O[columna_O.str.startswith('RE')].count())

    items_sin_oc = int(df.iloc[:, 7].isnull().sum())

    if items_requisitados > 0:
        avance = (items_recibidos / items_requisitados) * 100
    else:
        avance = 0.0

    # 2. NUEVA FUNCIONALIDAD: Crear la tabla específica para "Lista de Pedido"
    # Extraemos solo las columnas solicitadas: A(0), F(5), D(3), H(7), M(12)
    # Rellenamos NaNs para evitar errores en JSON
    tabla_resumen = []
    
    # Iteramos sobre el dataframe para construir la lista limpia
    for index, row in df.iterrows():
        # Verificamos que existan índices antes de acceder (protección extra)
        sc_val = str(row.iloc[0]) if pd.notnull(row.iloc[0]) else ""
        item_val = str(row.iloc[5]) if pd.notnull(row.iloc[5]) else ""
        cant_val = str(row.iloc[3]) if pd.notnull(row.iloc[3]) else ""
        oc_val = str(row.iloc[7]) if pd.notnull(row.iloc[7]) else ""
        fecha_val = str(row.iloc[12]) if pd.notnull(row.iloc[12]) else ""
        
        tabla_resumen.append({
            "SC": sc_val,
            "ITEM": item_val,
            "CANTIDAD": cant_val,
            "ORDEN DE COMPRA": oc_val,
            "FECHA DE LLEGADA": fecha_val,
            "LISTA DE PEDIDO": ""  # Campo nuevo editable vacio inicialmente
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
        "tabla_resumen": tabla_resumen, # Guardamos la nueva tabla
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# --- INTERFAZ GRÁFICA ---

st.markdown("""
    <h1 style='text-align: center;'>⚓ Dashboard: R-1926 MONFORTE DE LEMOS</h1>
    <p style='text-align: center;'>Sistema de Control de Materiales</p>
    """, unsafe_allow_html=True)
st.write("---")

# Variable para controlar estado de admin en el main
es_admin = False

# --- BARRA LATERAL (ADMINISTRACIÓN) ---
with st.sidebar:
    st.header("⚙️ Panel de Administración")
    
    password = st.text_input("Clave de Acceso", type="password")
    
    if password == "1234":
        es_admin = True # Activamos bandera de admin
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
        st.info("Introduce la clave '1234' para subir archivos o editar pedidos.")

# --- ÁREA PRINCIPAL (VISUALIZACIÓN) ---

if not st.session_state.proyectos:
    st.info("👋 No hay reportes cargados en el sistema. Usa el panel izquierdo para subir el primer Excel.")
else:
    # Selector de proyecto
    opciones = [p["nombre"] for p in st.session_state.proyectos]
    seleccion = st.selectbox("📂 Selecciona el reporte a visualizar:", opciones)
    
    # Obtener el índice del proyecto seleccionado para poder modificarlo después
    indice_proyecto = next((i for i, p in enumerate(st.session_state.proyectos) if p["nombre"] == seleccion), None)
    proyecto = st.session_state.proyectos[indice_proyecto]
    
    if proyecto:
        datos = proyecto["contenido"]
        kpis = datos["kpis"]
        
        st.markdown(f"### Reporte: {proyecto['nombre']} (Cargado: {datos['fecha_carga']})")
        
        # 1. MÉTRICAS (Igual)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Items Requisitados", kpis["items_requisitados"])
        with c2: st.metric("Items Recibidos", kpis["items_recibidos"])
        with c3: st.metric("Items sin OC", kpis["items_sin_oc"])
        with c4: st.metric("Porcentaje de Avance", f"{kpis['avance']:.1f}%", delta="Progreso Global")
            
        st.write("---")
        
        # 2. GRÁFICAS (Igual)
        col_graf, _ = st.columns([1, 0.1]) # Truco para centrar o usar espacio
        with col_graf:
            df_graf = pd.DataFrame({
                'Estado': ['Requisitados', 'Recibidos', 'Sin OC'],
                'Cantidad': [kpis["items_requisitados"], kpis["items_recibidos"], kpis["items_sin_oc"]]
            })
            fig = px.bar(df_graf, x='Estado', y='Cantidad', color='Estado', text_auto=True,
                         color_discrete_map={'Requisitados': '#3498db', 'Recibidos': '#2ecc71', 'Sin OC': '#e74c3c'}, height=300)
            st.plotly_chart(fig, use_container_width=True)

        st.write("---")
        
        # --- 3. NUEVA SECCIÓN: TABLA DETALLADA CON EDICIÓN ---
        st.subheader("📋 Detalle de Materiales y Lista de Pedido")
        
        # Recuperamos la tabla resumen guardada
        # (Si es un proyecto viejo que no tiene esta tabla, manejamos el error creando lista vacia)
        raw_tabla = datos.get("tabla_resumen", [])
        df_tabla = pd.DataFrame(raw_tabla)

        if not df_tabla.empty:
            # Configuración de columnas para el editor
            column_config = {
                "SC": st.column_config.TextColumn("SC", disabled=True),
                "ITEM": st.column_config.TextColumn("Item", disabled=True),
                "CANTIDAD": st.column_config.TextColumn("Cant.", disabled=True),
                "ORDEN DE COMPRA": st.column_config.TextColumn("O.C.", disabled=True),
                "FECHA DE LLEGADA": st.column_config.TextColumn("Llegada", disabled=True),
                "LISTA DE PEDIDO": st.column_config.TextColumn(
                    "📝 Lista de Pedido (Editable)", 
                    disabled=not es_admin,  # Aquí está la magia: SOLO ADMIN PUEDE EDITAR
                    help="Escribe aquí notas sobre el pedido (Solo Admin)"
                )
            }

            # Mostramos el editor
            df_editado = st.data_editor(
                df_tabla,
                column_config=column_config,
                use_container_width=True,
                hide_index=True,
                key=f"editor_{proyecto['id']}" # Clave única para que no se mezcle
            )

            # LÓGICA DE GUARDADO DE EDICIÓN
            if es_admin:
                # Comparamos si hubo cambios
                # Convertimos a json string para comparar facil o usamos equals
                # Para ser eficiente, ponemos un boton de guardar
                if st.button("💾 Guardar Cambios en 'Lista de Pedido'", type="primary"):
                    # Actualizamos el diccionario en memoria
                    st.session_state.proyectos[indice_proyecto]["contenido"]["tabla_resumen"] = df_editado.to_dict(orient="records")
                    # Guardamos en disco
                    guardar_datos(st.session_state.proyectos)
                    st.success("¡Cambios guardados exitosamente!")
                    st.rerun()
        else:
            st.warning("Este reporte es antiguo y no tiene la estructura para la tabla resumen. Por favor cárgalo de nuevo.")

        st.write("---")

        # 4. VISTA PREVIA ORIGINAL (Igual)
        with st.expander("🔍 Ver Base de Datos Completa (Original)"):
            df_visual = pd.DataFrame(datos["data"])
            st.dataframe(df_visual)
