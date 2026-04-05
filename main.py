# -*- coding: utf-8 -*-
"""
Detector de transacciones con puntuación de riesgo (solo biblioteca estándar).

Lee un CSV de transacciones, aplica reglas sencillas, muestra el informe en consola
y guarda una copia en informe.txt (transacciones sospechosas + resumen).

Uso:
  python main.py
  python main.py --file otro_archivo.csv
  python main.py -f datos/mis_transacciones.csv
"""

import argparse
import csv
from datetime import datetime, time
from pathlib import Path

# Valores ajustables (umbral e horario) viven en config.py
from config import HORA_FIN, HORA_INICIO, UMBRAL_IMPORTE

# ---------------------------------------------------------------------------
# RUTAS Y RESTO DE AJUSTES (solo lo que no está en config.py)
# ---------------------------------------------------------------------------

CARPETA = Path(__file__).resolve().parent
NOMBRE_CSV_POR_DEFECTO = "transacciones.csv"
ARCHIVO_INFORME = CARPETA / "informe.txt"

# Puntos que suma cada regla al "score" de una transacción
PUNTOS_IMPORTE_ELEVADO = 2
PUNTOS_FUERA_DE_HORARIO = 1

# Fraccionamiento: varios pagos "pequeños" el mismo día (posible división de un pago grande)
UMBRAL_IMPORTE_PEQUEÑO = 1000  # importes por debajo cuentan como "pequeños" para esta regla
MIN_PEQUEÑAS_MISMO_DIA = 3  # si hay tantas o más en un día, formamos un grupo sospechoso
# Si entras en un grupo de fraccionamiento, el score no puede quedar por debajo de esto (riesgo alto)
SCORE_MINIMO_FRACCIONAMIENTO = 3

# Textos que verás en la lista de alertas (usan los números importados de config)
MENSAJE_IMPORTE = f"Importe elevado (mayor a {UMBRAL_IMPORTE})"
MENSAJE_HORARIO = (
    f"Fuera de horario permitido ({HORA_INICIO:02d}:00 a {HORA_FIN:02d}:00)"
)
MENSAJE_FRACCIONAMIENTO = (
    "Grupo de transacciones sospechosas (posible fraccionamiento)"
)

# Patrón repetitivo en el tiempo (mismo destinatario, importe parecido, concepto relacionado)
PUNTOS_PATRON_REPETITIVO = 2
UMBRAL_DIFERENCIA_IMPORTE_RELATIVA = 0.20  # importes con menos del 20 % de diferencia (vs. el mayor)
MIN_OCURRENCIAS_PATRON = 3  # al menos tantas transacciones en el grupo
MIN_DIAS_DISTINTOS_PATRON = 3  # deben caer en al menos tantas fechas distintas
MENSAJE_PATRON_REPETITIVO = "Patrón repetitivo de transacciones"

# Palabras que quitamos del concepto antes de buscar la “idea” principal (muy genéricas)
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


# ---------------------------------------------------------------------------
# ARGUMENTOS DE LÍNEA DE COMANDOS (sin librerías externas: solo argparse)
# ---------------------------------------------------------------------------


def parsear_argumentos():
    """
    Lee lo que escribiste después de 'python main.py'.
    Si no pones --file, devuelve None y más abajo usaremos el CSV por defecto.
    """
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
            f'Ruta al CSV de transacciones. Por defecto: "{NOMBRE_CSV_POR_DEFECTO}" '
            "en la carpeta del programa."
        ),
    )
    return parser.parse_args()


def resolver_ruta_csv(nombre_o_ruta_opcional):
    """
    Decide qué archivo CSV abrir.

    - Sin argumento: usa transacciones.csv que está junto a main.py (como antes).
    - Con argumento: la ruta es relativa a la carpeta desde la que ejecutaste
      python (la "carpeta actual"), salvo que pongas una ruta absoluta (C:\\...).
    """
    if nombre_o_ruta_opcional is None:
        return CARPETA / NOMBRE_CSV_POR_DEFECTO

    p = Path(nombre_o_ruta_opcional).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (Path.cwd() / p).resolve()


# ---------------------------------------------------------------------------
# CARGA Y FECHA/HORA (datetime)
# ---------------------------------------------------------------------------


def parsear_fecha_hora(fecha_str, hora_str):
    """
    Une las columnas 'fecha' y 'hora' del CSV en un solo datetime.

    - Fecha esperada: YYYY-MM-DD (como en el CSV de ejemplo).
    - Hora: HH, HH:MM o HH:MM:SS.
    """
    fecha_str = fecha_str.strip()
    hora_str = hora_str.strip()
    # Partimos la hora en horas, minutos y (opcional) segundos
    partes_h = hora_str.split(":")
    h = int(partes_h[0])
    mi = int(partes_h[1]) if len(partes_h) > 1 else 0
    s = int(partes_h[2]) if len(partes_h) > 2 else 0
    solo_fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    return datetime.combine(solo_fecha, time(h, mi, s))


def cargar_transacciones(ruta):
    """
    Lee el CSV y devuelve una lista de diccionarios (una fila = un diccionario).
    Convierte 'importe' a float y junta fecha + hora en 'fecha_hora' (datetime).
    Las columnas fecha y hora del CSV ya no se guardan sueltas: solo el datetime.
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


def esta_dentro_de_horario_permitido(fecha_hora):
    """
    True si la hora del datetime está entre 08:00 y 22:00 inclusive
    (se mira hora y minuto del reloj, igual que antes con la columna hora).
    """
    minutos_desde_medianoche = fecha_hora.hour * 60 + fecha_hora.minute
    inicio = HORA_INICIO * 60
    fin = HORA_FIN * 60
    return inicio <= minutos_desde_medianoche <= fin


def mapa_grupos_fraccionamiento(transacciones):
    """
    Detecta patrones de posible fraccionamiento (estructuring):

    Agrupamos por fecha del calendario y miramos solo transacciones con importe
    estrictamente menor a UMBRAL_IMPORTE_PEQUEÑO. Si en un mismo día hay
    MIN_PEQUEÑAS_MISMO_DIA o más de esas operaciones, todas las "pequeñas"
    de ese día quedan relacionadas entre sí.

    Devuelve un diccionario: id de transacción (texto) -> identificador del grupo.
    El identificador incluye la fecha para que en el informe se vea qué movimientos van juntos.
    Ejemplo de grupo: "FRAC-2026-04-05" (todas las del mismo día en ese patrón comparten ID).
    """
    # fecha -> lista de ids de filas pequeñas ese día (una entrada por transacción)
    pequeñas_por_dia = {}
    for t in transacciones:
        if t["importe"] < UMBRAL_IMPORTE_PEQUEÑO:
            # Día calendario a partir del datetime (YYYY-MM-DD, estable para agrupar)
            dia = t["fecha_hora"].date().isoformat()
            if dia not in pequeñas_por_dia:
                pequeñas_por_dia[dia] = []
            pequeñas_por_dia[dia].append(str(t["id"]))

    id_a_grupo = {}
    for fecha, lista_ids in pequeñas_por_dia.items():
        if len(lista_ids) >= MIN_PEQUEÑAS_MISMO_DIA:
            # Un solo código de grupo por fecha: todas las pequeñas de ese día comparten relación
            etiqueta = f"FRAC-{fecha}"
            for tid in lista_ids:
                id_a_grupo[tid] = etiqueta
    return id_a_grupo


def normalizar_descripcion(texto):
    """Texto en minúsculas y sin espacios de sobra (conceptos y destinatarios)."""
    if not texto:
        return ""
    return " ".join(texto.strip().lower().split())


def palabras_clave_del_concepto(concepto):
    """
    Trocea el concepto en palabras, ignora las muy comunes y devuelve el resto.
    Así “Cuota gimnasio mensual” y “Cuota gimnasio abril” comparten “gimnasio”.
    """
    texto = normalizar_descripcion(concepto)
    if not texto:
        return set()
    return {
        p
        for p in texto.split()
        if len(p) >= 2 and p not in PALABRAS_IGNORADAS_EN_CONCEPTO
    }


def conceptos_relacionados(concepto_a, concepto_b):
    """True si, tras quitar palabras triviales, queda al menos una palabra en común."""
    clave_a = palabras_clave_del_concepto(concepto_a)
    clave_b = palabras_clave_del_concepto(concepto_b)
    if not clave_a or not clave_b:
        return False
    return bool(clave_a & clave_b)


def importes_parecidos(importe_a, importe_b):
    """
    Dos importes son “similares” si la diferencia relativa respecto al mayor
    es estrictamente menor al 20 % (ej. 800 € y 950 € → |800-950|/950 ≈ 15,8 %).
    """
    if importe_a <= 0 and importe_b <= 0:
        return importe_a == importe_b
    if importe_a <= 0 or importe_b <= 0:
        return False
    mayor = max(importe_a, importe_b)
    return abs(importe_a - importe_b) / mayor < UMBRAL_DIFERENCIA_IMPORTE_RELATIVA


def transacciones_mismo_patron(t_a, t_b):
    """
    Dos movimientos van al mismo patrón si:
      - mismo destinatario (mismo texto normalizado),
      - importes similares (< 20 % de diferencia),
      - conceptos relacionados (comparten alguna palabra clave tras filtrar tópicos).
    """
    dest_a = normalizar_descripcion(t_a.get("destinatario", ""))
    dest_b = normalizar_descripcion(t_b.get("destinatario", ""))
    if not dest_a or dest_a != dest_b:
        return False
    if not importes_parecidos(t_a["importe"], t_b["importe"]):
        return False
    return conceptos_relacionados(t_a.get("concepto", ""), t_b.get("concepto", ""))


def mapa_patrones_repetitivos(transacciones):
    """
    Busca grupos de pagos repetidos en el tiempo: mismo destinatario, importe parecido
    y concepto que comparte palabra principal (sin exigir texto idéntico).

    Unimos filas que cumplen eso entre sí (conjuntos disjuntos). Si el grupo tiene
    al menos MIN_OCURRENCIAS_PATRON movimientos y en MIN_DIAS_DISTINTOS_PATRON
    fechas distintas, asignamos PATRON-001, PATRON-002, ...
    """
    n = len(transacciones)
    if n < MIN_OCURRENCIAS_PATRON:
        return {}

    # Cada posición es un índice en la lista transacciones; padre[i] apunta al “representante”
    padre = list(range(n))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]  # achatamos caminos para ir más rápido
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

    # Agrupar índices por la raíz del conjunto
    componentes = {}
    for i in range(n):
        r = raiz(i)
        if r not in componentes:
            componentes[r] = []
        componentes[r].append(i)

    grupos_sospechosos = []
    for indices in componentes.values():
        if len(indices) < MIN_OCURRENCIAS_PATRON:
            continue
        fechas_distintas = {
            transacciones[k]["fecha_hora"].date().isoformat() for k in indices
        }
        if len(fechas_distintas) < MIN_DIAS_DISTINTOS_PATRON:
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

    # Regla 2: fuera de franja 08:00–22:00 → +1 punto (se usa el reloj del datetime)
    if not esta_dentro_de_horario_permitido(transaccion["fecha_hora"]):
        score += PUNTOS_FUERA_DE_HORARIO
        alertas.append(MENSAJE_HORARIO)

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
    """
    Convierte el score en una etiqueta legible.

    - 0 puntos     → riesgo bajo
    - 1 o 2 puntos → riesgo medio
    - 3 o más      → riesgo alto

    El score puede subir más si varias reglas coinciden (p. ej. importe alto,
    fuera de horario y fraccionamiento el mismo día).
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

    Las reglas de fraccionamiento y de patrón temporal miran todo el listado junto,
    por eso primero calculamos mapas id→etiqueta y luego ajustamos cada fila.
    """
    grupos_fraccionamiento = mapa_grupos_fraccionamiento(lista_transacciones)
    patrones_repetitivos = mapa_patrones_repetitivos(lista_transacciones)

    resultados = []
    for t in lista_transacciones:
        r = evaluar_transaccion(t)
        tid = str(t["id"])

        # Regla 3: varias transacciones pequeñas el mismo día (grupo relacionado)
        if tid in grupos_fraccionamiento:
            r["alertas"].append(MENSAJE_FRACCIONAMIENTO)
            r["grupo_fraccionamiento"] = grupos_fraccionamiento[tid]
            # Piso de riesgo: entrar en un grupo así implica al menos riesgo alto
            r["score"] = max(r["score"], SCORE_MINIMO_FRACCIONAMIENTO)

        # Regla 4: el mismo tipo de operación en varios días con importes parecidos
        if tid in patrones_repetitivos:
            r["alertas"].append(MENSAJE_PATRON_REPETITIVO)
            r["patron_repetitivo"] = patrones_repetitivos[tid]
            r["score"] += PUNTOS_PATRON_REPETITIVO

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
    # Solo aparece si esta fila forma parte de un grupo de fraccionamiento
    grupo = r.get("grupo_fraccionamiento")
    if grupo:
        emitir_linea(
            f"  Grupo relacionado:  {grupo}  (misma fecha, patrón conjunto)",
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
    args = parsear_argumentos()
    archivo_csv = resolver_ruta_csv(args.archivo_csv)

    imprimir_separador("=")
    print("INFORME DE ANÁLISIS DE TRANSACCIONES")
    imprimir_separador("=")
    print()

    if not archivo_csv.is_file():
        print(f"ERROR: No se encuentra el archivo CSV:")
        print(f"       {archivo_csv}")
        print()
        print("Comprueba la ruta o usa: python main.py --file tu_archivo.csv")
        return

    transacciones = cargar_transacciones(archivo_csv)
    resultados = analizar_todas_las_transacciones(transacciones)

    print(f"Archivo: {archivo_csv}")
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