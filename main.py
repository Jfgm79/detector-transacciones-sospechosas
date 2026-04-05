# -*- coding: utf-8 -*-
"""
Detector de transacciones con puntuación de riesgo (solo biblioteca estándar).

Lee transacciones.csv, aplica reglas sencillas, muestra el informe en consola
y guarda una copia en informe.txt (transacciones sospechosas + resumen).
"""

import csv
from pathlib import Path

# Valores ajustables (umbral e horario) viven en config.py
from config import HORA_FIN, HORA_INICIO, UMBRAL_IMPORTE

# ---------------------------------------------------------------------------
# RUTAS Y RESTO DE AJUSTES (solo lo que no está en config.py)
# ---------------------------------------------------------------------------

CARPETA = Path(__file__).resolve().parent
ARCHIVO_CSV = CARPETA / "transacciones.csv"
ARCHIVO_INFORME = CARPETA / "informe.txt"

# Puntos que suma cada regla al "score" de una transacción
PUNTOS_IMPORTE_ELEVADO = 2
PUNTOS_FUERA_DE_HORARIO = 1

# Textos que verás en la lista de alertas (usan los números importados de config)
MENSAJE_IMPORTE = f"Importe elevado (mayor a {UMBRAL_IMPORTE})"
MENSAJE_HORARIO = (
    f"Fuera de horario permitido ({HORA_INICIO:02d}:00 a {HORA_FIN:02d}:00)"
)


# ---------------------------------------------------------------------------
# CARGA Y UTILIDADES DE HORA
# ---------------------------------------------------------------------------


def cargar_transacciones(ruta):
    """
    Lee el CSV y devuelve una lista de diccionarios (una fila = un diccionario).
    Convierte 'importe' a número float para poder comparar y formatear.
    """
    lista = []
    with open(ruta, encoding="utf-8") as f:
        lector = csv.DictReader(f)
        for fila in lector:
            fila["importe"] = float(fila["importe"])
            lista.append(fila)
    return lista


def minutos_desde_medianoche(hora_texto):
    """Pasa 'HH:MM' a minutos desde las 00:00 (para comparar horas fácilmente)."""
    partes = hora_texto.strip().split(":")
    horas = int(partes[0])
    minutos = int(partes[1]) if len(partes) > 1 else 0
    return horas * 60 + minutos


def esta_dentro_de_horario_permitido(hora_texto):
    """True si la hora está entre 08:00 y 22:00 inclusive."""
    m = minutos_desde_medianoche(hora_texto)
    inicio = HORA_INICIO * 60
    fin = HORA_FIN * 60
    return inicio <= m <= fin


# ---------------------------------------------------------------------------
# EVALUACIÓN DE RIESGO (reglas + score + nivel)
# ---------------------------------------------------------------------------


def evaluar_transaccion(transaccion):
    """
    Mira una transacción y calcula:
      - lista de mensajes de alerta (vacía si no hay nada raro)
      - score total (suma de puntos por cada regla que se cumpla)

    Devuelve un diccionario con copia de los datos útiles + score + alertas.
    Así el resto del programa solo trabaja con este "resultado enriquecido".
    """
    alertas = []
    score = 0

    # Regla 1: importe mayor al umbral → +2 puntos
    if transaccion["importe"] > UMBRAL_IMPORTE:
        score += PUNTOS_IMPORTE_ELEVADO
        alertas.append(MENSAJE_IMPORTE)

    # Regla 2: fuera de franja 08:00–22:00 → +1 punto
    if not esta_dentro_de_horario_permitido(transaccion["hora"]):
        score += PUNTOS_FUERA_DE_HORARIO
        alertas.append(MENSAJE_HORARIO)

    return {
        "id": transaccion["id"],
        "fecha": transaccion["fecha"],
        "hora": transaccion["hora"],
        "importe": transaccion["importe"],
        "descripcion": transaccion["concepto"],
        "destinatario": transaccion.get("destinatario", ""),
        "alertas": alertas,
        "score": score,
    }


def clasificar_nivel_riesgo(score):
    """
    Convierte el score en una etiqueta legible.

    - 0 puntos     → riesgo bajo
    - 1 o 2 puntos → riesgo medio
    - 3 o más      → riesgo alto

    (Con las reglas actuales el máximo posible es 3: importe + horario.)
    """
    if score == 0:
        return "Riesgo bajo"
    if score <= 2:
        return "Riesgo medio"
    return "Riesgo alto"


def analizar_todas_las_transacciones(lista_transacciones):
    """
    Evalúa cada fila del CSV y devuelve una lista de resultados enriquecidos,
    cada uno con el campo 'nivel' ya calculado.
    """
    resultados = []
    for t in lista_transacciones:
        r = evaluar_transaccion(t)
        r["nivel"] = clasificar_nivel_riesgo(r["score"])
        resultados.append(r)
    return resultados


# ---------------------------------------------------------------------------
# SALIDA: consola y, opcionalmente, archivo informe.txt
# ---------------------------------------------------------------------------


def emitir_linea(texto="", archivo=None, consola=True):
    """
    Si consola=True, muestra la línea en pantalla.
    Si 'archivo' no es None, escribe la misma línea en el fichero.

    Así reutilizamos el mismo texto para pantalla e informe sin duplicarlo dos veces
    en la misma ejecución (al guardar el .txt usamos consola=False).
    """
    if consola:
        print(texto)
    if archivo is not None:
        archivo.write(texto + "\n")


def imprimir_separador(caracter="=", longitud=60, archivo=None, consola=True):
    """Línea visual para separar secciones (consola y/o informe)."""
    emitir_linea(caracter * longitud, archivo, consola)


def imprimir_transaccion_sospechosa(r, archivo=None, consola=True):
    """
    Muestra el bloque profesional para UNA transacción con score > 0.

    Incluye: ID, fecha/hora, importe, descripción, alertas, score y nivel.
    Puedes escribir solo al fichero poniendo consola=False (ver guardar_informe_txt).
    """
    imprimir_separador("-", 56, archivo, consola)
    emitir_linea("  TRANSACCIÓN SOSPECHOSA", archivo, consola)
    imprimir_separador("-", 56, archivo, consola)
    emitir_linea(f"  ID:               {r['id']}", archivo, consola)
    emitir_linea(f"  Fecha y hora:     {r['fecha']}  {r['hora']}", archivo, consola)
    emitir_linea(f"  Importe:          {r['importe']:.2f} €", archivo, consola)
    emitir_linea(f"  Descripción:      {r['descripcion']}", archivo, consola)
    emitir_linea("  Alertas detectadas:", archivo, consola)
    for a in r["alertas"]:
        emitir_linea(f"      • {a}", archivo, consola)
    emitir_linea(f"  Score de riesgo:  {r['score']}", archivo, consola)
    emitir_linea(f"  Nivel de riesgo:  {r['nivel']}", archivo, consola)
    emitir_linea("", archivo, consola)


def imprimir_resumen(resultados, archivo=None, consola=True):
    """
    Cuenta cuántas transacciones hay en cada nivel y muestra totales
    en consola y, si indicas 'archivo', también en el informe.
    """
    total = len(resultados)
    bajo = sum(1 for r in resultados if r["score"] == 0)
    medio = sum(1 for r in resultados if 1 <= r["score"] <= 2)
    alto = sum(1 for r in resultados if r["score"] >= 3)

    # Cada regla disparada en una fila cuenta como una "incidencia"
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
    """
    Crea o sobrescribe informe.txt con:
      - el listado de transacciones sospechosas (o un mensaje si no hay ninguna)
      - el mismo resumen que ves al final en pantalla

    No repite la salida en consola (consola=False): eso ya lo hace main().
    """
    with open(ARCHIVO_INFORME, "w", encoding="utf-8") as informe:
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


def main():
    imprimir_separador("=")
    print("INFORME DE ANÁLISIS DE TRANSACCIONES")
    imprimir_separador("=")
    print()

    if not ARCHIVO_CSV.is_file():
        print(f"ERROR: No se encuentra el archivo '{ARCHIVO_CSV.name}'.")
        print("Colócalo en la misma carpeta que main.py y vuelve a ejecutar.")
        return

    transacciones = cargar_transacciones(ARCHIVO_CSV)
    resultados = analizar_todas_las_transacciones(transacciones)

    print(f"Archivo: {ARCHIVO_CSV.name}")
    print(f"Transacciones cargadas: {len(resultados)}\n")

    # Solo las que tienen al menos una alerta (score > 0)
    sospechosas = [r for r in resultados if r["score"] > 0]

    if not sospechosas:
        print("No hay transacciones sospechosas según las reglas actuales.\n")
    else:
        print(f"TRANSACCIONES SOSPECHOSAS ({len(sospechosas)})\n")
        for r in sospechosas:
            imprimir_transaccion_sospechosa(r)

    imprimir_resumen(resultados)

    # Misma información en informe.txt (sin volver a imprimir en pantalla)
    guardar_informe_txt(sospechosas, resultados)
    print(f"Informe guardado en: {ARCHIVO_INFORME.name}")


if __name__ == "__main__":
    main()
