# -*- coding: utf-8 -*-
"""
Utilidades: leer el CSV, formatear texto en consola/archivo y guardar informe.txt.

No contiene reglas de negocio; solo entrada/salida.
"""

import csv
from datetime import datetime, time

import config


def parsear_fecha_hora(fecha_str, hora_str):
    """
    Une las columnas 'fecha' y 'hora' del CSV en un datetime.

    Fecha: YYYY-MM-DD. Hora: HH, HH:MM o HH:MM:SS.
    """
    fecha_str = fecha_str.strip()
    hora_str = hora_str.strip()
    partes_h = hora_str.split(":")
    h = int(partes_h[0])
    mi = int(partes_h[1]) if len(partes_h) > 1 else 0
    s = int(partes_h[2]) if len(partes_h) > 2 else 0
    solo_fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    return datetime.combine(solo_fecha, time(h, mi, s))


def cargar_transacciones(ruta):
    """
    Lee el CSV: importe numérico, fecha+hora -> campo fecha_hora (datetime).
    Elimina las columnas sueltas fecha y hora del diccionario.
    """
    lista = []
    with open(ruta, encoding="utf-8") as f:
        lector = csv.DictReader(f)
        for fila in lector:
            fila["importe"] = float(fila["importe"])
            fila["fecha_hora"] = parsear_fecha_hora(fila["fecha"], fila["hora"])
            del fila["fecha"]
            del fila["hora"]
            lista.append(fila)
    return lista


def emitir_linea(texto="", archivo=None, consola=True):
    """Imprime y/o escribe una línea (mismo texto para consola e informe)."""
    if consola:
        print(texto)
    if archivo is not None:
        archivo.write(texto + "\n")


def imprimir_separador(caracter="=", longitud=60, archivo=None, consola=True):
    """Línea decorativa."""
    emitir_linea(caracter * longitud, archivo, consola)


def imprimir_transaccion_sospechosa(r, archivo=None, consola=True):
    """Bloque detallado de una transacción con score > 0."""
    imprimir_separador("-", 56, archivo, consola)
    emitir_linea("  TRANSACCIÓN SOSPECHOSA", archivo, consola)
    imprimir_separador("-", 56, archivo, consola)
    emitir_linea(f"  ID:               {r['id']}", archivo, consola)
    emitir_linea(f"  Fecha y hora:     {r['fecha']}  {r['hora']}", archivo, consola)
    emitir_linea(f"  Importe:          {r['importe']:.2f} €", archivo, consola)
    emitir_linea(f"  Descripción:      {r['descripcion']}", archivo, consola)
    grupo = r.get("grupo_fraccionamiento")
    if grupo:
        emitir_linea(
            f"  Grupo relacionado:  {grupo}  (misma fecha, patrón conjunto)",
            archivo,
            consola,
        )
    patron = r.get("patron_repetitivo")
    if patron:
        emitir_linea(
            f"  Patrón temporal:    {patron}  (misma conducta en días distintos)",
            archivo,
            consola,
        )
    emitir_linea("  Alertas detectadas:", archivo, consola)
    for a in r["alertas"]:
        emitir_linea(f"      • {a}", archivo, consola)
    emitir_linea(f"  Score de riesgo:  {r['score']}", archivo, consola)
    emitir_linea(f"  Nivel de riesgo:  {r['nivel']}", archivo, consola)
    emitir_linea("", archivo, consola)


def imprimir_resumen(resultados, archivo=None, consola=True):
    """Totales por nivel de riesgo e incidencias."""
    total = len(resultados)
    bajo = sum(1 for r in resultados if r["score"] == 0)
    medio = sum(1 for r in resultados if 1 <= r["score"] <= 2)
    alto = sum(1 for r in resultados if r["score"] >= 3)
    total_incidencias = sum(len(r["alertas"]) for r in resultados)

    imprimir_separador("=", 60, archivo, consola)
    emitir_linea("RESUMEN DEL ANÁLISIS", archivo, consola)
    imprimir_separador("=", 60, archivo, consola)
    emitir_linea(f"  Transacciones analizadas:     {total}", archivo, consola)
    emitir_linea(f"  · Riesgo bajo (0 puntos):     {bajo}", archivo, consola)
    emitir_linea(f"  · Riesgo medio (1-2 puntos):  {medio}", archivo, consola)
    emitir_linea(f"  · Riesgo alto (3+ puntos):    {alto}", archivo, consola)
    emitir_linea("", archivo, consola)
    emitir_linea(
        f"  Total de incidencias (reglas disparadas): {total_incidencias}",
        archivo,
        consola,
    )
    emitir_linea("", archivo, consola)


def guardar_informe_txt(sospechosas, resultados):
    """Escribe informe.txt en la carpeta del proyecto (solo fichero, sin duplicar prints)."""
    with open(config.ARCHIVO_INFORME, "w", encoding="utf-8") as informe:
        if not sospechosas:
            emitir_linea(
                "No hay transacciones sospechosas según las reglas actuales.",
                informe,
                consola=False,
            )
            emitir_linea("", informe, consola=False)
        else:
            emitir_linea(
                f"TRANSACCIONES SOSPECHOSAS ({len(sospechosas)})",
                informe,
                consola=False,
            )
            emitir_linea("", informe, consola=False)
            for r in sospechosas:
                imprimir_transaccion_sospechosa(r, informe, consola=False)

        imprimir_resumen(resultados, informe, consola=False)
