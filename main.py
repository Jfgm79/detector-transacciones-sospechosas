# -*- coding: utf-8 -*-
"""
Punto de entrada del programa: argumentos, carga, análisis y presentación.

La lógica de reglas está en detector.py; CSV e informe en utils.py; números en config.py.

Uso:
  python main.py
  python main.py --file otro_archivo.csv
  python main.py -f datos/mis_transacciones.csv
"""

import argparse
from pathlib import Path

import config
from detector import analizar_todas_las_transacciones
from utils import (
    cargar_transacciones,
    guardar_informe_txt,
    imprimir_resumen,
    imprimir_separador,
    imprimir_transaccion_sospechosa,
)


def parsear_argumentos():
    """Lee la línea de comandos (--file / -f)."""
    parser = argparse.ArgumentParser(
        description="Analiza transacciones en CSV y genera informe de riesgo."
    )
    parser.add_argument(
        "--file",
        "-f",
        dest="archivo_csv",
        default=None,
        metavar="ARCHIVO.csv",
        help=(
            f'Ruta al CSV de transacciones. Por defecto: "{config.NOMBRE_CSV_POR_DEFECTO}" '
            "en la carpeta del programa."
        ),
    )
    return parser.parse_args()


def resolver_ruta_csv(nombre_o_ruta_opcional):
    """
    Sin --file: CSV por defecto junto al proyecto.
    Con ruta relativa: respecto a la carpeta desde la que ejecutaste python.
    """
    if nombre_o_ruta_opcional is None:
        return config.CARPETA_PROYECTO / config.NOMBRE_CSV_POR_DEFECTO

    p = Path(nombre_o_ruta_opcional).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (Path.cwd() / p).resolve()


def main():
    args = parsear_argumentos()
    archivo_csv = resolver_ruta_csv(args.archivo_csv)

    imprimir_separador("=")
    print("INFORME DE ANÁLISIS DE TRANSACCIONES")
    imprimir_separador("=")
    print()

    if not archivo_csv.is_file():
        print("ERROR: No se encuentra el archivo CSV:")
        print(f"       {archivo_csv}")
        print()
        print("Comprueba la ruta o usa: python main.py --file tu_archivo.csv")
        return

    # 1) Cargar filas del CSV (utils)
    transacciones = cargar_transacciones(archivo_csv)
    # 2) Analizar con todas las reglas (detector)
    resultados = analizar_todas_las_transacciones(transacciones)

    print(f"Archivo: {archivo_csv}")
    print(f"Transacciones cargadas: {len(resultados)}\n")

    sospechosas = [r for r in resultados if r["score"] > 0]

    if not sospechosas:
        print("No hay transacciones sospechosas según las reglas actuales.\n")
    else:
        print(f"TRANSACCIONES SOSPECHOSAS ({len(sospechosas)})\n")
        for r in sospechosas:
            imprimir_transaccion_sospechosa(r)

    imprimir_resumen(resultados)

    guardar_informe_txt(sospechosas, resultados)
    print(f"Informe guardado en: {config.ARCHIVO_INFORME.name}")


if __name__ == "__main__":
    main()
