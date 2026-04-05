# Detector de transacciones sospechosas

Herramienta básica para detectar patrones sospechosos en transacciones financieras mediante reglas simples.

## Funcionalidades

- Detección de transacciones con importe elevado
- Detección de operaciones fuera de horario permitido
- Sistema de puntuación de riesgo
- Clasificación de riesgo (bajo, medio, alto)
- Generación de informe automático (`informe.txt`)

## Reglas de detección

- Importe mayor a 3000 €
- Transacciones fuera del horario 08:00 - 22:00

## Ejecución

```bash
python main.py