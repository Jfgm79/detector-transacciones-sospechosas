# -*- coding: utf-8 -*-
"""
Motor de detección: reglas, puntuación, niveles de riesgo y agrupaciones.

No lee ficheros ni imprime nada; solo recibe la lista de transacciones ya cargada
y devuelve resultados listos para que utils.py los muestre o guarde.
"""

import config


def esta_dentro_de_horario_permitido(fecha_hora):
    """
    True si la hora del datetime está entre HORA_INICIO y HORA_FIN (inclusive),
    mirando solo hora y minuto.
    """
    minutos_desde_medianoche = fecha_hora.hour * 60 + fecha_hora.minute
    inicio = config.HORA_INICIO * 60
    fin = config.HORA_FIN * 60
    return inicio <= minutos_desde_medianoche <= fin


def mapa_grupos_fraccionamiento(transacciones):
    """
    Fraccionamiento: muchos importes pequeños el mismo día calendario.

    Devuelve id (texto) -> código tipo FRAC-YYYY-MM-DD.
    """
    pequeñas_por_dia = {}
    for t in transacciones:
        if t["importe"] < config.UMBRAL_IMPORTE_PEQUEÑO:
            dia = t["fecha_hora"].date().isoformat()
            if dia not in pequeñas_por_dia:
                pequeñas_por_dia[dia] = []
            pequeñas_por_dia[dia].append(str(t["id"]))

    id_a_grupo = {}
    for fecha, lista_ids in pequeñas_por_dia.items():
        if len(lista_ids) >= config.MIN_PEQUEÑAS_MISMO_DIA:
            etiqueta = f"FRAC-{fecha}"
            for tid in lista_ids:
                id_a_grupo[tid] = etiqueta
    return id_a_grupo


def normalizar_descripcion(texto):
    """Minúsculas y un solo espacio entre palabras (conceptos y destinatarios)."""
    if not texto:
        return ""
    return " ".join(texto.strip().lower().split())


def palabras_clave_del_concepto(concepto):
    """Palabras del concepto quitando tópicos muy comunes (ver config)."""
    texto = normalizar_descripcion(concepto)
    if not texto:
        return set()
    return {
        p
        for p in texto.split()
        if len(p) >= 2 and p not in config.PALABRAS_IGNORADAS_EN_CONCEPTO
    }


def conceptos_relacionados(concepto_a, concepto_b):
    """True si queda al menos una palabra significativa en común."""
    clave_a = palabras_clave_del_concepto(concepto_a)
    clave_b = palabras_clave_del_concepto(concepto_b)
    if not clave_a or not clave_b:
        return False
    return bool(clave_a & clave_b)


def importes_parecidos(importe_a, importe_b):
    """Diferencia relativa al mayor estrictamente menor que el umbral configurado."""
    if importe_a <= 0 and importe_b <= 0:
        return importe_a == importe_b
    if importe_a <= 0 or importe_b <= 0:
        return False
    mayor = max(importe_a, importe_b)
    return abs(importe_a - importe_b) / mayor < config.UMBRAL_DIFERENCIA_IMPORTE_RELATIVA


def transacciones_mismo_patron(t_a, t_b):
    """Mismo destinatario normalizado, importes parecidos y concepto relacionado."""
    dest_a = normalizar_descripcion(t_a.get("destinatario", ""))
    dest_b = normalizar_descripcion(t_b.get("destinatario", ""))
    if not dest_a or dest_a != dest_b:
        return False
    if not importes_parecidos(t_a["importe"], t_b["importe"]):
        return False
    return conceptos_relacionados(t_a.get("concepto", ""), t_b.get("concepto", ""))


def mapa_patrones_repetitivos(transacciones):
    """
    Une filas similares (union-find). Un grupo válido tiene al menos
    MIN_OCURRENCIAS_PATRON movimientos y MIN_DIAS_DISTINTOS_PATRON fechas distintas.

    Devuelve id -> PATRON-001, PATRON-002, ...
    """
    n = len(transacciones)
    if n < config.MIN_OCURRENCIAS_PATRON:
        return {}

    padre = list(range(n))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def unir(i, j):
        ri, rj = raiz(i), raiz(j)
        if ri != rj:
            padre[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if transacciones_mismo_patron(transacciones[i], transacciones[j]):
                unir(i, j)

    componentes = {}
    for i in range(n):
        r = raiz(i)
        if r not in componentes:
            componentes[r] = []
        componentes[r].append(i)

    grupos_sospechosos = []
    for indices in componentes.values():
        if len(indices) < config.MIN_OCURRENCIAS_PATRON:
            continue
        fechas_distintas = {
            transacciones[k]["fecha_hora"].date().isoformat() for k in indices
        }
        if len(fechas_distintas) < config.MIN_DIAS_DISTINTOS_PATRON:
            continue
        grupos_sospechosos.append(indices)

    def clave_orden(indices):
        filas = [transacciones[k] for k in indices]
        return (min(f["fecha_hora"] for f in filas), min(str(f["id"]) for f in filas))

    grupos_sospechosos.sort(key=clave_orden)

    id_a_patron = {}
    for num, indices in enumerate(grupos_sospechosos, start=1):
        codigo = f"PATRON-{num:03d}"
        for k in indices:
            id_a_patron[str(transacciones[k]["id"])] = codigo
    return id_a_patron


def evaluar_transaccion(transaccion):
    """
    Reglas que miran una sola fila: importe alto y horario.

    Devuelve diccionario con datos para el informe + score + lista de alertas.
    """
    alertas = []
    score = 0

    if transaccion["importe"] > config.UMBRAL_IMPORTE:
        score += config.PUNTOS_IMPORTE_ELEVADO
        alertas.append(config.MENSAJE_IMPORTE)

    if not esta_dentro_de_horario_permitido(transaccion["fecha_hora"]):
        score += config.PUNTOS_FUERA_DE_HORARIO
        alertas.append(config.MENSAJE_HORARIO)

    fh = transaccion["fecha_hora"]
    return {
        "id": transaccion["id"],
        "fecha": fh.strftime("%Y-%m-%d"),
        "hora": fh.strftime("%H:%M"),
        "importe": transaccion["importe"],
        "descripcion": transaccion["concepto"],
        "destinatario": transaccion.get("destinatario", ""),
        "alertas": alertas,
        "score": score,
    }


def clasificar_nivel_riesgo(score):
    """Etiqueta humana según el score total."""
    if score == 0:
        return "Riesgo bajo"
    if score <= 2:
        return "Riesgo medio"
    return "Riesgo alto"


def analizar_todas_las_transacciones(lista_transacciones):
    """
    Punto de entrada del análisis: aplica reglas por fila y reglas globales
    (fraccionamiento y patrón repetitivo), y devuelve la lista de resultados.
    """
    grupos_fraccionamiento = mapa_grupos_fraccionamiento(lista_transacciones)
    patrones_repetitivos = mapa_patrones_repetitivos(lista_transacciones)

    resultados = []
    for t in lista_transacciones:
        r = evaluar_transaccion(t)
        tid = str(t["id"])

        if tid in grupos_fraccionamiento:
            r["alertas"].append(config.MENSAJE_FRACCIONAMIENTO)
            r["grupo_fraccionamiento"] = grupos_fraccionamiento[tid]
            r["score"] = max(r["score"], config.SCORE_MINIMO_FRACCIONAMIENTO)

        if tid in patrones_repetitivos:
            r["alertas"].append(config.MENSAJE_PATRON_REPETITIVO)
            r["patron_repetitivo"] = patrones_repetitivos[tid]
            r["score"] += config.PUNTOS_PATRON_REPETITIVO

        r["nivel"] = clasificar_nivel_riesgo(r["score"])
        resultados.append(r)
    return resultados
