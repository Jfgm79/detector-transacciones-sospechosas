# -*- coding: utf-8 -*-
"""
Parámetros y rutas del proyecto.

Aquí van números y textos que puedes tocar sin leer toda la lógica.
El detector (detector.py) y las utilidades (utils.py) leen estos valores.
"""

from pathlib import Path

# Carpeta donde están main.py, config.py, el CSV por defecto e informe.txt
CARPETA_PROYECTO = Path(__file__).resolve().parent
NOMBRE_CSV_POR_DEFECTO = "transacciones.csv"
ARCHIVO_INFORME = CARPETA_PROYECTO / "informe.txt"

# --- Umbrales generales (también usados en las alertas) ---
UMBRAL_IMPORTE = 3000
HORA_INICIO = 8
HORA_FIN = 22

# --- Puntos por regla ---
PUNTOS_IMPORTE_ELEVADO = 2
PUNTOS_FUERA_DE_HORARIO = 1

# --- Fraccionamiento (muchos pagos pequeños el mismo día) ---
UMBRAL_IMPORTE_PEQUEÑO = 1000
MIN_PEQUEÑAS_MISMO_DIA = 3
SCORE_MINIMO_FRACCIONAMIENTO = 3

# --- Patrón repetitivo (mismo destinatario, importe parecido, varios días) ---
PUNTOS_PATRON_REPETITIVO = 2
UMBRAL_DIFERENCIA_IMPORTE_RELATIVA = 0.20
MIN_OCURRENCIAS_PATRON = 3
MIN_DIAS_DISTINTOS_PATRON = 3

# --- Mensajes que ven los usuarios en el informe ---
MENSAJE_IMPORTE = f"Importe elevado (mayor a {UMBRAL_IMPORTE})"
MENSAJE_HORARIO = (
    f"Fuera de horario permitido ({HORA_INICIO:02d}:00 a {HORA_FIN:02d}:00)"
)
MENSAJE_FRACCIONAMIENTO = (
    "Grupo de transacciones sospechosas (posible fraccionamiento)"
)
MENSAJE_PATRON_REPETITIVO = "Patrón repetitivo de transacciones"

# Palabras muy genéricas en el concepto (se ignoran al buscar la “idea” principal)
PALABRAS_IGNORADAS_EN_CONCEPTO = frozenset(
    {
        "cuota",
        "mensual",
        "abril",
        "enero",
        "febrero",
        "marzo",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "y",
        "a",
        "en",
    }
)
