def procesar_nuevo_excel(df_raw: pd.DataFrame):
    # Asegurar columnas clave
    cols = ["No. S.C.", "CANT ITEM S.C.", "DESCRIPCION DE LA PARTIDA",
            "No. O.C.", "FECHA DE LLEGADA", "ESTATUS GRN"]
    faltan = [c for c in cols if c not in df_raw.columns]
    if faltan:
        return {"error": f"Faltan columnas: {faltan}"}

    # 1) Items solicitados = todas las filas con cantidad
    df_solicitados = df_raw[df_raw["CANT ITEM S.C."].notna()].copy()
    items_solicitados = int(df_solicitados["CANT ITEM S.C."].count())

    # 2) Items recibidos = ESTATUS GRN == 'RECV'
    col_grn = df_raw["ESTATUS GRN"].astype(str).str.strip()
    df_recibidos = df_raw[col_grn == "RECV"].copy()
    items_recibidos = len(df_recibidos)

    # 3) Otros KPIs (opcionales) calculados sobre solicitados
    items_sin_oc = int(df_solicitados["No. O.C."].isna().sum())
    avance = (items_recibidos / items_solicitados * 100) if items_solicitados > 0 else 0.0

    # 4) TABLA = SOLO RECIBIDOS (prioridad ESTATUS GRN)
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

    data_preview = df_solicitados.fillna("").head(500).to_dict(orient="records")

    return {
        "kpis": {
            "items_requisitados": items_solicitados,
            "items_recibidos": items_recibidos,
            "items_sin_oc": items_sin_oc,
            "avance": avance
        },
        "tabla_resumen": tabla_resumen,   # SOLO los que tienen ESTATUS GRN = RECV
        "data": data_preview,
        "fecha_carga": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
