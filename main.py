# -*- coding: utf-8 -*-
"""
Lee transacciones desde transacciones.csv y muestra alertas en consola.
Solo usa la biblioteca estándar de Python (no hace falta instalar nada).
"""

import csv
from pathlib import Path

# El CSV debe estar en la misma carpeta que este archivo
CARPETA = Path(__file__).resolve().parent
ARCHIVO_CSV = CARPETA / "transacciones.csv"

# Reglas de detección (puedes cambiar estos números)
UMBRAL_IMPORTE = 3000  # alerta si el importe es MAYOR que este valor
HORA_INICIO = 8       # 08:00 inclusive
HORA_FIN = 22         # 22:00 inclusive

# Texto fijo que verás en pantalla para cada tipo de alerta
ETIQUETA_IMPORTE = "[ALERTA - IMPORTE ELEVADO]"
ETIQUETA_HORARIO = "[ALERTA - FUERA DE HORARIO]"


def cargar_transacciones(ruta):
    """
    Abre el CSV y devuelve una lista de diccionarios.
    Cada diccionario es una fila: claves = nombres de columnas.
    """
    lista = []
    with open(ruta, encoding="utf-8") as f:
        lector = csv.DictReader(f)
        for fila in lector:
            # El CSV trae el importe como texto; lo convertimos a número
            fila["importe"] = float(fila["importe"])
            lista.append(fila)
    return lista


def minutos_desde_medianoche(hora_texto):
    """
    Convierte "HH:MM" o "HH:MM:SS" en minutos totales desde las 00:00.
    Así podemos comparar horas fácilmente.
    """
    partes = hora_texto.strip().split(":")
    horas = int(partes[0])
    minutos = int(partes[1]) if len(partes) > 1 else 0
    return horas * 60 + minutos


def hora_es_valida(hora_texto):
    """
    True si la hora está entre 08:00 y 22:00 (ambos inclusive).
    """
    m = minutos_desde_medianoche(hora_texto)
    inicio = HORA_INICIO * 60
    fin = HORA_FIN * 60
    return inicio <= m <= fin


def main():
    print("--- Detector de transacciones ---\n")

    if not ARCHIVO_CSV.is_file():
        print(f"ERROR: No existe el archivo {ARCHIVO_CSV.name}")
        print("Colócalo en la misma carpeta que main.py")
        return

    transacciones = cargar_transacciones(ARCHIVO_CSV)
    print(f"Leídas {len(transacciones)} transacciones.\n")

    # Listas donde guardaremos lo que dispare alertas
    alertas_importe = []
    alertas_horario = []

    for t in transacciones:
        # Regla 1: importe mayor a 3000
        if t["importe"] > UMBRAL_IMPORTE:
            alertas_importe.append(t)

        # Regla 2: fuera de 08:00 - 22:00
        if not hora_es_valida(t["hora"]):
            alertas_horario.append(t)

    # --- Mostrar alertas (cada línea lleva su etiqueta de tipo) ---
    print("DETALLE DE ALERTAS\n")

    if not alertas_importe:
        print(f"{ETIQUETA_IMPORTE}")
        print("   Sin incidencias en esta categoría.\n")
    else:
        for t in alertas_importe:
            print(ETIQUETA_IMPORTE)
            print(
                f"   ID {t['id']} | {t['fecha']} {t['hora']} | "
                f"{t['importe']:.2f} € | {t['destinatario']} | {t['concepto']}"
            )
            print()

    if not alertas_horario:
        print(f"{ETIQUETA_HORARIO}")
        print("   Sin incidencias en esta categoría.\n")
    else:
        for t in alertas_horario:
            print(ETIQUETA_HORARIO)
            print(
                f"   ID {t['id']} | {t['fecha']} {t['hora']} | "
                f"{t['importe']:.2f} € | {t['destinatario']} | {t['concepto']}"
            )
            print()

    # Cada fila que cumple una regla cuenta como 1 alerta (una misma transacción puede sumar 2)
    total_alertas = len(alertas_importe) + len(alertas_horario)

    print("-" * 50)
    print("RESUMEN")
    print("-" * 50)
    print(f"  Alertas por importe elevado (> {UMBRAL_IMPORTE}): {len(alertas_importe)}")
    print(f"  Alertas por fuera de horario (08:00–22:00):     {len(alertas_horario)}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Total de alertas detectadas:                     {total_alertas}")
    print()


if __name__ == "__main__":
    main()