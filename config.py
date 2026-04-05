# -*- coding: utf-8 -*-
"""
Parámetros del detector que puedes cambiar sin tocar la lógica del programa.

Edita solo los números de aquí; main.py los leerá automáticamente al arrancar.
"""

# Si el importe de una transacción es MAYOR que este número, cuenta como "elevado"
UMBRAL_IMPORTE = 3000

# Franja horaria permitida (hora en formato 24 h, sin minutos si no las usas)
# Una transacción está "en horario" si cae entre HORA_INICIO y HORA_FIN (inclusive).
HORA_INICIO = 8
HORA_FIN = 22
