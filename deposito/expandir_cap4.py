#!/usr/bin/env python3
"""Expande el Capitulo 4 del deposito y reconcilia sus cifras con los ficheros del repo.

Parte del docx ya corregido (bloque de formato del revisor, aplicado por
aplicar_correcciones_deposito.py) y le anade el contenido nuevo redactado en
CONTENIDO_NUEVO_DEPOSITO.md. Es idempotente: guarda una base intocable la primera vez y
siempre reconstruye desde ella, de modo que se puede ejecutar cuantas veces haga falta.

Cada insercion clona un parrafo del propio documento para heredar su formato (estilo,
numeracion, fuente), tecnica ya empleada en entrega3/insertar_contenido_en_docx.py. Toda
precondicion se valida y el script aborta en voz alta si el documento cambio de estructura.

Bloques:
  1. Cifras: splits reales (4.512 / 564 / 565 / 5.641) en la Tabla 6 y en la prosa;
     parametros entrenables reales del adaptador LoRA (2,36 M, 0,38 %); corpus de 5.641
     pares en la primera conclusion del Capitulo 5.
  2. Contenido nuevo: 4.2.7 (perfil del corpus + Tabla 12), ampliacion de 4.3, 4.3.1
     (validacion del retriever), 4.4.1 (curva de entrenamiento y codigo de lengua), 4.5.3
     (presupuesto de contexto), 4.6.1 (protocolo de evaluacion), ampliacion del analisis
     cualitativo, 4.6.3 (taxonomia reproducible + Tabla 11 nueva), 4.6.4 (comparacion
     intra-Claude + Tabla 10 con ambos modelos) y 4.6.5 (amenazas a la validez).
  3. Renumeracion: los actuales 4.6.1 y 4.6.2 pasan a 4.6.2 y 4.6.3.

Tras ejecutar: abrir en Word y regenerar los tres indices (los campos TOC quedan marcados
como dirty; el procedimiento fiable en Word para Mac es el bucle AppleScript de
'update field' sobre los campos TOC).
"""
from __future__ import annotations

import copy
import re
import shutil
import sys
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DEPOSITO = Path(__file__).parent
DOCX = DEPOSITO / "TFM_Deposito_EslavaSantos.docx"
BASE = DEPOSITO / "_base_correcciones.docx"   # estado tras las correcciones de formato


def die(msg: str):
    sys.exit(f"ABORT: {msg}")


def w(tag: str) -> str:
    return qn("w:" + tag)


# ------------------------------------------------------------------ clonado de parrafos

def _strip(el, tag):
    for e in el.findall(w(tag)):
        el.remove(e)


def _first_run_rpr(p_el):
    r = p_el.find(w("r"))
    if r is None:
        return None
    rpr = r.find(w("rPr"))
    return copy.deepcopy(rpr) if rpr is not None else None


def _mk_runs(text: str, rpr):
    """Genera runs interpretando **negrita**, cada uno con copia del rPr de la plantilla."""
    runs = []
    for k, seg in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if seg == "":
            continue
        r = OxmlElement("w:r")
        rp = copy.deepcopy(rpr) if rpr is not None else None
        if k % 2 == 1:
            if rp is None:
                rp = OxmlElement("w:rPr")
            if rp.find(w("b")) is None:
                rp.append(OxmlElement("w:b"))
        if rp is not None:
            r.append(rp)
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = seg
        r.append(t)
        runs.append(r)
    return runs


def clone_para(template_p, text: str):
    """Clona un parrafo (heading o cuerpo): conserva pPr, reemplaza el texto."""
    new = copy.deepcopy(template_p._p)
    for tag in ("bookmarkStart", "bookmarkEnd", "proofErr"):
        _strip(new, tag)
    rpr = _first_run_rpr(new)
    for el in list(new):
        if el.tag in (w("r"), w("proofErr"), w("hyperlink")):
            new.remove(el)
    for r in _mk_runs(text, rpr):
        new.append(r)
    return new


def clone_caption(template_cap, titulo: str):
    """Clona un pie de tabla ya corregido: 'Tabla ' + campo SEQ + salto + titulo cursiva.

    Conserva el campo SEQ (que Word renumera solo) y el salto de linea manual, y sustituye
    los runs del titulo por uno nuevo con el mismo formato (sin negrita, en cursiva).
    """
    new = copy.deepcopy(template_cap._p)
    for tag in ("bookmarkStart", "bookmarkEnd", "proofErr"):
        _strip(new, tag)

    hijos = list(new)
    idx_br = None
    for i, el in enumerate(hijos):
        if el.tag == w("r") and el.find(w("br")) is not None:
            idx_br = i
            break
    if idx_br is None:
        die("la plantilla de pie de tabla no tiene el salto de linea esperado")

    rpr_titulo = None
    for el in hijos[idx_br + 1:]:
        if el.tag == w("r") and el.find(w("rPr")) is not None:
            rpr_titulo = copy.deepcopy(el.find(w("rPr")))
            break
    if rpr_titulo is None:
        die("la plantilla de pie de tabla no tiene runs de titulo con formato")

    for el in hijos[idx_br + 1:]:
        new.remove(el)

    r = OxmlElement("w:r")
    r.append(rpr_titulo)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = titulo
    r.append(t)
    new.append(r)
    return new


def borrar_columna(tabla, indice: int):
    """Elimina una columna de la tabla: su celda en cada fila y su ancho en el tblGrid."""
    grid = tabla._tbl.find(w("tblGrid"))
    cols = grid.findall(w("gridCol"))
    grid.remove(cols[indice])
    for fila in tabla._tbl.findall(w("tr")):
        celdas = fila.findall(w("tc"))
        fila.remove(celdas[indice])


def set_cell(cell, texto: str, negrita: bool = False):
    """Reescribe una celda conservando el formato del primer run que ya tenia.

    Alinea a la izquierda: las celdas heredan la justificacion del cuerpo y, en columnas
    estrechas con texto largo, eso abre huecos entre palabras que dificultan la lectura.
    """
    p = cell.paragraphs[0]
    ppr = p._p.get_or_add_pPr()
    if ppr.find(w("jc")) is None:
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), "left")
        ppr.append(jc)
    rpr = _first_run_rpr(p._p)
    for el in list(p._p):
        if el.tag in (w("r"), w("proofErr")):
            p._p.remove(el)
    for extra in cell.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    r = OxmlElement("w:r")
    if rpr is not None:
        if negrita and rpr.find(w("b")) is None:
            rpr.append(OxmlElement("w:b"))
        if not negrita:
            for b in rpr.findall(w("b")):
                rpr.remove(b)
        r.append(rpr)
    elif negrita:
        rpr = OxmlElement("w:rPr")
        rpr.append(OxmlElement("w:b"))
        r.append(rpr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = texto
    r.append(t)
    p._p.append(r)


# ------------------------------------------------------------------ contenido nuevo

H_427 = "4.2.7. Perfil estadístico del corpus"

TXT_427 = [
    "El corpus final reúne 5.641 pares, de los cuales 5.589 provienen del Nuevo Testamento y 52 de la Constitución de 1991. Conviene mirar su composición interna, porque de ella se derivan varias decisiones técnicas del resto del capítulo y también varias de sus limitaciones.",
    "La distribución por libro es marcadamente desigual, como muestra la Tabla 7. Los cuatro evangelios y los Hechos de los Apóstoles concentran 3.338 pares, casi el sesenta por ciento del total, mientras que en el otro extremo hay libros que apenas contribuyen: 2 Juan y 3 Juan aportan cinco pares cada uno. Esta asimetría tiene una consecuencia inmediata sobre el diseño experimental. La partición estratificada por libro, que habría sido la opción natural para garantizar que las tres particiones cubrieran el mismo reparto temático, resulta inviable cuando existen clases con cinco elementos, porque una estratificación 80/10/10 sobre cinco pares no reparte nada. Por eso el Notebook 07 recurre a una partición aleatoria simple con semilla 42, decisión que se documenta aquí con su motivo y no como una preferencia arbitraria.",
    "Las longitudes de las dos caras del corpus son más parecidas de lo que cabría esperar entre una lengua aglutinante y una lengua flexiva. El texto Inga suma 119.174 palabras y el español 116.584, con medias de 21,13 y 20,67 palabras por par. La razón de longitud entre ambas caras tiene mediana 0,93, es decir, la versión Inga de un versículo típico es ligeramente más corta que la española, lo que concuerda con una morfología que empaqueta en sufijos lo que el español despliega en preposiciones y artículos. La media de esa misma razón, en cambio, es 1,07, y esa discrepancia entre media y mediana delata la existencia de una cola de pares donde el Inga se alarga desproporcionadamente. El par más extremo tiene 131 palabras en Inga frente a un máximo de 63 en español. Esos casos suelen corresponder a versículos donde la traducción Inga es más parafrástica que literal, y son candidatos naturales a introducir ruido en el entrenamiento.",
    "El corpus es homogéneo en un sentido que conviene no perder de vista: los 5.641 pares pertenecen al dialecto Alto Putumayo y proceden, salvo 52 excepciones, de un único texto religioso traducido por un único equipo. Esa homogeneidad facilita el aprendizaje, porque el registro y la ortografía son consistentes, y al mismo tiempo limita la generalización, porque el sistema aprende a traducir el Inga de la Biblia de Wycliffe antes que el Inga que se habla en el Putumayo.",
]

TABLA_12 = [
    ["Libro o fuente", "Pares", "Porcentaje del corpus"],
    ["Lucas", "794", "14,1"],
    ["Hechos", "704", "12,5"],
    ["Mateo", "697", "12,4"],
    ["Juan", "635", "11,3"],
    ["Marcos", "508", "9,0"],
    ["Romanos", "346", "6,1"],
    ["1 Corintios", "304", "5,4"],
    ["Apocalipsis", "249", "4,4"],
    ["Hebreos", "226", "4,0"],
    ["2 Corintios", "180", "3,2"],
    ["Resto del Nuevo Testamento (17 libros)", "946", "16,8"],
    ["Constitución de 1991", "52", "0,9"],
    ["Total", "5.641", "100,0"],
]

CAP_12 = "Distribución del corpus paralelo por libro (diez primeros) y fuente"
NOTA_12 = "Nota. Elaboración propia a partir de datos/corpus_paralelo.jsonl. El corpus abarca 28 libros del Nuevo Testamento. Los dos menos representados, 2 Juan y 3 Juan, aportan cinco pares cada uno."

TXT_43_EXTRA = [
    "Dos decisiones de la indexación merecen justificarse porque condicionan lo que el recuperador puede encontrar. La primera es la dimensionalidad de los vectores. El modelo gemini-embedding-001 produce por defecto embeddings de 3.072 dimensiones, y en este trabajo se reducen a 768 mediante el parámetro output_dimensionality. La reducción responde a una razón práctica: cuatro índices que suman 14.529 registros ocupan en disco 127 MB con vectores de 768 dimensiones, y multiplicar por cuatro ese tamaño no aportaría precisión apreciable en una búsqueda sobre colecciones de este orden, donde el cuello de botella no es la capacidad de representación sino la calidad de lo indexado.",
    "La segunda es la segmentación de la gramática. Los dos recursos gramaticales se trocean en 605 fragmentos, 560 procedentes de la gramática pedagógica de Levinsohn y Mongui y 45 del apéndice morfosintáctico. Ese troceo se hace por longitud y no por unidad de sentido, que es la vía rápida y también la más imperfecta: una regla gramatical puede quedar separada de los ejemplos que la ilustran, y el recuperador entregar entonces la mitad útil de una explicación. El efecto de esta decisión, agravado por el truncamiento posterior a 400 caracteres que se describe en el apartado 4.5.3, se observa en las consultas de sondeo del apartado 4.3.1.",
    "El acceso a la API de embeddings se realiza por lotes de 50 textos con una espera de 1,2 segundos entre lotes y hasta cinco reintentos con retroceso exponencial. Estos parámetros no tienen interés teórico, pero son los que hacen que la indexación de 14.529 registros termine sin errores de límite de tasa, y se consignan porque forman parte de lo que hay que reproducir para obtener los mismos índices.",
]

H_431 = "4.3.1. Validación cualitativa de la recuperación"

TXT_431 = [
    "Antes de medir la calidad de las traducciones conviene comprobar que el componente de recuperación hace lo que se espera de él. Un sistema RAG puede fallar en dos lugares distintos y el error se ve igual desde fuera: puede que el generador traduzca mal, o puede que el recuperador le entregue un contexto inútil y el generador simplemente lo ignore. Por eso el Notebook 08 cierra con una batería de tres consultas de sondeo, una por cada nivel de dificultad, cuyas salidas quedaron guardadas en el propio notebook.",
    "La primera consulta es una palabra aislada, wasi (casa). El índice léxico devuelve como primeras tres entradas casa (s): wasi, wasi (s): casa y wasi kancha (s): patio de la casa. El índice gramatical recupera fragmentos de la gramática de Levinsohn que utilizan huasi como ejemplo para explicar los posposicionales cancha (fuera de) y ucu (dentro de). La recuperación léxica y la gramatical funcionan aquí como se esperaba: la primera devuelve el lema exacto en ambas direcciones de consulta y la segunda devuelve reglas donde la palabra aparece en uso.",
    "La segunda consulta es una locución, imasa parlangapa (cómo decir). El interés de este caso está en el índice gramatical, que devuelve tres pasajes de Levinsohn dedicados precisamente al comportamiento de imasa: su uso para expresar semejanza con una acción, su frecuencia en interrogativas y su coocurrencia con el infinitivo en -sca. Es el tipo de conocimiento que un modelo de lenguaje de frontera no puede tener memorizado para el Inga y que solo puede llegarle por el contexto.",
    "La tercera consulta es una oración completa, Taita Diuska runakunata kuianmi (Dios ama a las personas). El índice de ejemplos devuelve Efesios 2:4, 1 Juan 5:2 y 1 Juan 4:20, los tres versículos sobre el amor de Dios, lo que confirma que la búsqueda semántica sobre embeddings opera a nivel de significado y no de coincidencia de superficie.",
    "La misma batería expone dos debilidades que conviene registrar. En la tercera consulta, el índice léxico devuelve entre sus tres primeras entradas panela (s): dusi, miski, que no guarda relación con la oración consultada: cuando la consulta es una oración entera y no un lema, el índice léxico pierde precisión porque el embedding de la oración no se parece al embedding de ninguna entrada de diccionario en particular. En la primera consulta ocurre algo distinto y más incómodo. Entre los ejemplos recuperados para wasi aparece Marcos 6:38, cuyo texto Inga menciona efectivamente wasi pero cuyo texto español alineado habla de panes y peces, sin mencionar ninguna casa. El par recuperado es correcto respecto al índice y erróneo respecto al contenido: es ruido de alineación del corpus, heredado de la correspondencia canónica versículo a versículo, que la recuperación no puede corregir y que se traslada intacto al prompt. Este punto se retoma en el apartado 4.6.5.",
]

H_441 = "4.4.1. Lectura de la curva de entrenamiento"

TXT_441 = [
    "Los hiperparámetros del adaptador quedaron fijados en adapter_config.json: rango r igual a 16, factor de escala alpha igual a 32, dropout de 0,1 y aplicación restringida a las matrices de proyección de consulta y de valor de los bloques de atención, q_proj y v_proj. El entrenamiento corrió tres épocas completas sobre los 9.024 ejemplos bidireccionales, lo que da 3.384 pasos de optimización con tamaño de lote 8, tasa de aprendizaje pico de 3e-4 y calentamiento lineal durante los primeros 100 pasos. El proceso tardó 1.606 segundos, es decir 26,8 minutos, sobre la GPU integrada del equipo mediante el backend MPS, a un ritmo de 16,86 ejemplos por segundo. El adaptador resultante ocupa 9,4 megabytes frente a los 2,46 gigabytes del modelo base, que es el argumento económico de LoRA y la razón por la que este experimento cabe en un portátil.",
    "La curva de pérdida de la Figura 10 admite una lectura que conviene hacer explícita, porque condiciona la interpretación de los resultados del apartado 4.6. La pérdida de entrenamiento arranca en 10,71 en el paso 20 y cae a 6,01 en el paso 3.380, con un mínimo de 5,92. La caída no está repartida de manera uniforme: casi toda ocurre en la primera época. La pérdida de validación lo confirma con claridad, porque baja de 6,05 al terminar la primera época a 5,97 en la segunda y a 5,94 en la tercera. Las dos últimas épocas, que consumen dos tercios del cómputo, aportan una mejora de 0,11 en la pérdida de validación.",
    "Lo que muestra esa curva es un adaptador que satura. El modelo aprende deprisa lo que puede aprender con 4.512 pares y después deja de aprender, y no porque empiece a sobreajustar (la pérdida de validación sigue bajando, aunque sea poco) sino porque agota la señal disponible en el corpus. La consecuencia práctica es que ampliar el número de épocas no era el camino: el techo no lo pone el presupuesto de entrenamiento sino el tamaño y la homogeneidad del corpus, que procede casi por completo de un único registro textual. Esta observación explica por qué la configuración B mejora de forma clara sobre la A pero se queda muy por debajo de la D, y es la razón de fondo por la que el trabajo futuro apunta primero a ampliar el corpus y solo después a escalar el modelo.",
    "Queda por justificar una decisión que atraviesa todo el capítulo y que hasta aquí se ha dado por supuesta: el uso del código de lengua quy_Latn, correspondiente al quechua de Ayacucho, para representar al Inga dentro de NLLB-200. El Inga no figura entre las doscientas lenguas del modelo, de modo que hay que asignarle alguna etiqueta existente, y quy_Latn es la más próxima tipológicamente entre las disponibles. La alternativa habría sido añadir un token de lengua nuevo y entrenar su embedding desde cero, lo que con 4.512 pares no ofrece garantías.",
    "La elección tiene una consecuencia que el apartado 4.6.3 cuantifica y que conviene anticipar aquí. Al forzar la decodificación en quy_Latn, el modelo sin adaptar no produce Inga defectuoso: produce quechua de Ayacucho competente, con su ortografía y su morfología propias, en 98 de los 100 ejemplos evaluados. El código de lengua actúa como un ancla fuerte, y esa ancla apunta a la lengua equivocada. El ajuste fino LoRA es precisamente lo que reorienta esa ancla hacia el Inga, y la Tabla 12 muestra que lo consigue: la configuración B ancla 98 de sus 100 salidas al vocabulario Inga del entrenamiento. Visto así, el valor del adaptador no está tanto en la mejora de BLEU, que es modesta, como en el cambio de lengua de salida, un efecto que ninguna de las tres métricas del capítulo sabe registrar.",
]

H_453 = "4.5.3. Presupuesto de contexto del prompt"

TXT_453 = [
    "El contexto que se inyecta en cada llamada está acotado de forma deliberada y ese límite tiene consecuencias. Por cada oración a traducir, el módulo claude_rag.py compone un prompt de usuario con tres secciones: las cinco entradas léxicas más cercanas, en formato lema (categoría): glosa; los tres fragmentos gramaticales más cercanos, cada uno truncado a 400 caracteres; y los cinco ejemplos paralelos más cercanos, ordenados según la dirección de traducción. La respuesta se limita a 256 tokens.",
    "El truncamiento de los fragmentos gramaticales a 400 caracteres es la decisión más discutible del diseño. Se tomó para acotar el coste por llamada y mantener el prompt en un tamaño predecible, pero corta pasajes de Levinsohn a mitad de explicación. En la consulta de sondeo sobre imasa que se describe en el apartado 4.3.1 se ve el efecto: el fragmento recuperado introduce la regla y se interrumpe antes de los ejemplos que la ilustran. Un modelo de frontera puede completar la regla por analogía con el quechua sureño, y eso es exactamente lo que no se quiere, porque el objetivo es que produzca Inga y no una lengua emparentada. La alternativa habría sido segmentar la gramática en unidades semánticamente completas en lugar de trocear por longitud, y queda anotada como mejora del índice gramatical.",
    "La dirección de traducción determina de qué índice se recuperan los ejemplos. Para inga2es se consulta el índice ejemplos, construido sobre el texto Inga; para es2inga se consulta ejemplos_es, construido sobre el texto español. La consulta se hace siempre en la lengua de origen, de modo que la búsqueda semántica opere sobre embeddings de la misma lengua que la oración de entrada. Los dos índices contienen los mismos 4.512 pares del conjunto de entrenamiento y se diferencian solo en el campo que se vectoriza.",
    "Conviene precisar un punto que el resumen del trabajo podía dejar ambiguo. Los índices de ejemplos suman 9.024 registros entre los dos, pero corresponden a 4.512 pares distintos indexados por sus dos caras. El número de ejemplos paralelos únicos disponibles para la recuperación es 4.512, no 9.024.",
]

H_461 = "4.6.1. Protocolo de evaluación y validez de las métricas"

TXT_461 = [
    "Las tres métricas se calculan con el módulo src/eval/metrics.py, que envuelve implementaciones estándar: BLEU a nivel de corpus con sacrebleu, chrF++ con sacrebleu y word_order igual a 2, y BERTScore F1 sobre XLM-RoBERTa multilingüe sin reescalado de línea base. Fijar estas decisiones por escrito importa más de lo que parece, porque BLEU admite variantes de tokenización y de suavizado que cambian el resultado varios puntos y hacen incomparables cifras que se presentan como equivalentes.",
    "Hay una limitación en la configuración de BERTScore que debe declararse porque afecta a la lectura de la Tabla 9. El scorer se instancia con lang igual a es para las dos direcciones de traducción. En la dirección Inga-español esto es correcto, porque la referencia está en español. En la dirección español-Inga no lo es: la referencia está en Inga, una lengua que XLM-RoBERTa no vio durante su preentrenamiento, y el modelo la procesa como si fuera español. El resultado es que en esa dirección BERTScore no mide adecuación semántica sino, más bien, plausibilidad de las subunidades ortográficas, y por eso sus valores se comprimen en un rango estrecho y varían poco entre configuraciones. La lectura correcta es que BERTScore aporta información útil en Inga-español y debe tomarse con reservas en español-Inga, dirección en la que chrF++, que opera sobre caracteres y no depende de ningún modelo preentrenado, es la métrica más fiable de las tres. Ninguna conclusión del trabajo se sostiene únicamente sobre el BERTScore de la dirección español-Inga.",
    "La muestra de evaluación son 100 ejemplos extraídos del conjunto de validación con random_state igual a 42. Su composición no es homogénea: 99 versículos del Nuevo Testamento y un único artículo de la Constitución, el artículo 10. Esa proporción refleja la del corpus, pero implica que las cifras de la Tabla 9 describen el rendimiento del sistema sobre registro bíblico y no autorizan a extrapolarlo al registro jurídico ni al conversacional. El único ejemplo constitucional de la muestra se comenta por separado en el apartado 4.6.2 justamente porque es el único.",
    "Las configuraciones A y B se generan localmente con búsqueda en haz de cuatro caminos y un máximo de 128 tokens nuevos; las configuraciones C, D y E se generan por API con un máximo de 256 tokens. Las diez corridas comparten los mismos 100 ejemplos, condición necesaria para que las diferencias entre columnas sean atribuibles a la configuración y no a la muestra.",
    "Queda por decir lo que el protocolo no cubre. No se midió sobre el conjunto de prueba, que permanece intacto con sus 565 ejemplos: todas las cifras de este capítulo son de validación, lo que en rigor las convierte en estimaciones de desarrollo y no en una evaluación final independiente. Tampoco se calcularon intervalos de confianza ni pruebas de significancia por remuestreo, de modo que las diferencias pequeñas entre configuraciones, y en particular la distancia de 1,13 puntos BLEU entre D y E en la dirección español-Inga, no pueden declararse estadísticamente significativas. Las diferencias grandes, como los 13,5 puntos que separan a C de D, son de una magnitud que ningún intervalo razonable haría desaparecer.",
]

TXT_CUALI_EXTRA = [
    "La inspección caso a caso se puede respaldar con una medida agregada que no depende del criterio del lector: la longitud de las salidas. La referencia Inga del conjunto de evaluación tiene 21,3 palabras de media y la referencia española 20,3. En la dirección español-Inga, las configuraciones con recuperación se mantienen cerca de ese orden de magnitud, con 16,5 palabras la D y 17,6 la E, mientras que la configuración B se dispara hasta 27,3 palabras. Ese exceso no es riqueza expresiva: es el bucle de repetición que se cuantifica en el apartado siguiente, inflando artificialmente el recuento. La configuración A, en el extremo opuesto, se queda en 14,5 palabras, por debajo de la referencia, lo que encaja con salidas cortas en una lengua que el modelo domina mal.",
    "En la dirección Inga-español el patrón se invierte. Todas las configuraciones producen salidas más largas que la referencia, entre 24,3 y 33,4 palabras frente a las 20,3 del gold. Aquí la explicación no es la degeneración sino la naturaleza del texto fuente: los versículos de la Reina-Valera de 1909 son sintácticamente comprimidos y arcaizantes, y tanto NLLB como Claude tienden a desplegarlos en castellano contemporáneo, más explícito y más largo. Es un sesgo de estilo que las métricas de n-gramas penalizan aunque la traducción sea correcta, y conviene tenerlo presente al comparar las cifras de esta dirección con las de la literatura, donde las referencias rara vez son bíblicas.",
]

TXT_TAXO = [
    "El análisis cualitativo se apoya en casos concretos. Para respaldarlo con una mirada de conjunto, las salidas de las cinco configuraciones sobre los 100 ejemplos de la muestra se clasificaron por tipo de fallo mediante criterios automáticos y deterministas, implementados en el módulo src/eval/error_analysis.py. La tabla que sigue puede regenerarse desde el fichero de predicciones sin intervención manual, que es la condición para que un recuento de errores sea algo más que una impresión. Los criterios se enuncian antes de mostrar los resultados, porque de ellos depende cómo han de leerse.",
    "Una salida se marca como degenerada cuando contiene un n-grama de hasta cuatro palabras repetido tres o más veces de forma consecutiva. Se marca como desbordada cuando supera en más de dos veces y media la longitud de la referencia. Y para la dirección español-Inga, que es donde se juega la cuestión de la variante, se emplean dos indicadores ortográficos y léxicos en lugar de un juicio subjetivo sobre a qué lengua se parece la salida.",
    "El primero aprovecha un rasgo de la escritura del Inga del Putumayo que resulta inusualmente discriminante. Sobre los 823.744 caracteres de texto Inga del conjunto de entrenamiento, la letra y no aparece ni una sola vez y la letra q aparece seis veces, un 0,001 por ciento. El Inga escribe iuiai donde el quechua sureño escribe yuyay, y kan donde aquel escribe qan. Ambos grafemas, en cambio, son centrales en la ortografía del quechua sureño y del kichwa ecuatoriano. La presencia de una q o una y en una salida es por tanto evidencia objetiva de que el sistema no está escribiendo en la variante del corpus. El segundo indicador mide la fracción de palabras de la salida que pertenecen al vocabulario Inga del entrenamiento, formado por 13.575 tipos, y considera la salida anclada al Inga cuando esa fracción alcanza la mitad.",
    "Los resultados de la Tabla 12 son más nítidos de lo que las métricas agregadas dejaban entrever. El modelo multilingüe sin adaptar (configuración A) produce grafías ajenas al Inga en 98 de los 100 ejemplos y solo una de sus salidas alcanza el umbral de anclaje léxico. No está traduciendo mal al Inga: no está traduciendo al Inga en absoluto, sino al quechua que conoce, que es el sureño del par quy_Latn con el que se le fuerza a decodificar. Ninguna métrica de la Tabla 9 dice esto, y sin embargo es lo primero que habría que saber del sistema.",
    "El ajuste fino corrige el idioma y rompe el decodificador. La configuración B invierte por completo los dos indicadores, con 98 salidas ancladas al vocabulario Inga y solo una con grafía ajena, lo que confirma que 4.512 pares bastan para enseñarle a NLLB en qué lengua debe escribir. Pero al mismo tiempo degenera en 51 de los 100 ejemplos, más de la mitad, y esa es la explicación completa de por qué su BLEU en español-Inga se queda en 1,79 pese a haber aprendido la variante correcta. El adaptador aprende el léxico y pierde la capacidad de detenerse.",
    "La recuperación aumentada consigue las dos cosas a la vez. La configuración D reduce la grafía ajena a 5 ejemplos, ancla 98 salidas al vocabulario Inga y no degenera en ninguno, mientras que la configuración C, el mismo modelo sin contexto recuperado, se queda a medio camino con 60 salidas de grafía ajena y solo 38 ancladas. La diferencia entre C y D no está en el modelo, que es el mismo, sino únicamente en lo que se le entrega en el prompt. Es la evidencia más directa de que, para este par de lenguas, el conocimiento que hace falta no está en los pesos sino en el contexto.",
    "Un cuarto tipo de error no admite recuento automático y aparece con regularidad en la inspección: los fallos de referencia y concordancia. En oraciones con varias cláusulas subordinadas, incluso la configuración D confunde a veces quién hace qué, o desplaza un sujeto de una cláusula a otra. Son errores sutiles, que no degradan la fluidez de la salida y que por eso pueden pasar inadvertidos a una métrica de superficie, pero que alteran el sentido. Su persistencia en la mejor configuración marca uno de los límites actuales del sistema.",
    "Conviene cerrar con un dato en positivo: ninguna de las cinco configuraciones produjo salidas vacías o truncadas. Todas devuelven siempre una traducción completa, aunque sea defectuosa. El problema, cuando lo hay, no es de cobertura sino de calidad o de variante.",
]

TABLA_11 = [
    ["Indicador", "Dirección", "A", "B", "C", "D", "E"],
    ["Degeneración por repetición", "Inga-es", "6", "8", "1", "1", "1"],
    ["Degeneración por repetición", "es-Inga", "6", "51", "0", "0", "0"],
    ["Desbordamiento de longitud (>2,5x ref)", "Inga-es", "17", "7", "13", "12", "13"],
    ["Grafía ajena al Inga (letras q o y)", "es-Inga", "98", "1", "60", "5", "6"],
    ["Salida anclada al vocabulario Inga", "es-Inga", "1", "98", "38", "98", "97"],
    ["Salidas vacías o truncadas", "ambas", "0", "0", "0", "0", "0"],
]

NOTA_11 = "Nota. Elaboración propia a partir de datos/predicciones_val_completo.jsonl mediante el módulo src/eval/error_analysis.py, sobre la corrida principal con Claude Opus 4.7. Todos los indicadores son deterministas y reproducibles; los criterios se definen en el texto. Las filas de grafía y anclaje no son excluyentes entre sí."

H_464 = "4.6.4. Comparación intra-Claude: por qué el modelo mayor aprovecha mejor el contexto"

TXT_464 = [
    "La Tabla 10 registra que Opus 4.7 aventaja a Sonnet 4.6 en 5,92 puntos BLEU en la configuración D, pero no explica de dónde sale esa ventaja. Los indicadores del apartado anterior, aplicados a las dos corridas por separado, permiten responderlo.",
    "En la configuración C, sin contexto recuperado, los dos modelos se comportan prácticamente igual, y ambos mal: Sonnet produce grafía ajena al Inga en 83 de los 100 ejemplos y Opus en 60, con anclajes léxicos de 5 y 38 respectivamente. Ninguno de los dos sabe escribir Inga por su cuenta, lo que era esperable. La diferencia aparece cuando se les entrega el mismo contexto recuperado. En la configuración D, Opus deja solo 5 salidas con grafía ajena, frente a las 19 de Sonnet. Es decir, ante ejemplos y vocabulario idénticos, el modelo de mayor capacidad se adhiere con más rigor a la ortografía y al léxico que se le muestran, mientras que el menor se desliza con más frecuencia hacia la variante quechua que ya traía aprendida.",
    "La ventaja de Opus, por tanto, no es una mayor competencia previa en Inga, lengua que ninguno de los dos conoce, sino una mayor fidelidad al contexto que se le entrega. Es un matiz con consecuencias prácticas: en un sistema RAG sobre una lengua de recursos escasos, lo que diferencia a los modelos no es tanto lo que saben como cuánto se dejan corregir por lo que se les muestra. Explica además la anomalía de la configuración E, donde Sonnet obtiene mejor BLEU en la dirección Inga-español: cuando el contexto incluye una semilla defectuosa producida por el LoRA, la mayor docilidad de Opus hacia el contexto deja de ser una virtud, porque lo que respeta con fidelidad es un error.",
    "La Tabla 11 del apartado anterior permite inspeccionar esa diferencia directamente: recoge tres ejemplos de la muestra con las salidas de ambos modelos junto a las del modelo multilingüe sin adaptar.",
]

TABLA_10 = [
    ["Referencia", "Texto fuente (español)", "A (NLLB zero-shot)", "D con Opus 4.7", "D con Sonnet 4.6"],
    ["Juan 4:32", "Yo tengo una comida que comer, que vosotros no sabéis.",
     "Jesustaq paykunata nirqan: Qankuna mana reqsiq kanaykichispaq mikhuq kani, nispa. (quechua sureño)",
     "Paika nirkakunata: Nukaka kankuna mana iachaska sug mikuita charini mikungapa. (Inga)",
     "Paika painakunata nirka: Nukaka mikungapa mikuika tian, kamkunaka mana yachangichu. (Inga con grafía y)"],
    ["Lucas 24:38", "Mas él les dice: ¿Por qué estáis turbados, y suben pensamientos á vuestros corazones?",
     "Jesustaq paykunata nirqan: ¿Imanasqataq llakikunkichis? ¿Imanasqataq sonqoykichispi yuyashankichis? (quechua sureño)",
     "Pai nirkakunata: ¿Imapatak chasa manchaspa kangichi, i imapatak chasa sungullapi iuianakungichi? (Inga)",
     "Paika nirkakunata: ¿Imapatak manchanakungichi, iuiaikunatak sungullapi wicharimungichi? (Inga)"],
    ["Constitución art. 10", "El castellano es el idioma oficial de Colombia.",
     "Kastillanuqa Colombia suyupi rimaymi. (quechua sureño)",
     "Lanku simi rimaimi ká Kulumbia Llagtapa idioma. (Inga)",
     "Kastilla simi kami Kulumbia llagtapi kawsag tukui runakunapata rimai. (Inga)"],
]

NOTA_10 = "Nota. Elaboración propia a partir de los Notebooks 10 y 11. Los tres ejemplos corresponden a la dirección español-Inga, que es donde se juega la cuestión de la variante. Las salidas se transcriben literalmente; los guiones de diálogo se normalizaron. La configuración A es idéntica en ambas corridas porque no interviene el modelo de lenguaje de frontera. La variante detectada se indica entre paréntesis. En Juan 4:32, la salida de Sonnet contiene la letra y (yachangichu), grafema ausente del Inga del corpus."

H_465 = "4.6.5. Amenazas a la validez de la evaluación"

TXT_465 = [
    "Cuatro factores acotan hasta dónde pueden llevarse las conclusiones de este capítulo.",
    "El primero es el ruido de alineación del propio corpus, que contamina las referencias contra las que se mide. La alineación canónica versículo a versículo descrita en el apartado 4.2.3 supone que la numeración de la edición Inga de Wycliffe y la de la Reina-Valera de 1909 coinciden, y no siempre lo hacen. En la muestra de evaluación hay al menos un caso claro: en Juan 4:32, el texto español de referencia dice que hay una comida que comer que los discípulos no conocen, mientras que el texto Inga emparejado corresponde en realidad al contenido de Juan 3:32, sobre el testimonio de lo que se ha visto y oído. En ese ejemplo, cualquier sistema que traduzca correctamente el español será penalizado por las tres métricas, porque la referencia no es la traducción de la oración fuente. El efecto empuja todas las cifras hacia abajo por igual, de modo que no invalida la comparación entre configuraciones, que es el objeto del experimento, pero sí obliga a leer los valores absolutos de BLEU como un límite inferior del rendimiento real.",
    "El segundo es el tamaño y la composición de la muestra. Cien ejemplos, de los cuales 99 son versículos bíblicos, no permiten estimar el rendimiento fuera del registro religioso ni calcular intervalos de confianza estrechos. El conjunto de prueba, con 565 ejemplos, sigue sin utilizarse.",
    "El tercero es la referencia única. BLEU y chrF++ comparan contra una sola traducción válida, cuando en traducción existen muchas. Este problema afecta a toda la traducción automática, pero se agrava en lenguas sin norma ortográfica estabilizada, donde una misma palabra admite varias escrituras legítimas y el sistema es penalizado por elegir una distinta de la del corpus.",
    "El cuarto es la ausencia de juicio humano. Ninguna de las salidas fue evaluada por hablantes de Inga. Los indicadores automáticos de variante que se introducen en el apartado 4.6.3 mitigan parcialmente esta carencia, porque detectan de forma objetiva cuándo el sistema escribe en otra lengua, pero no pueden pronunciarse sobre si una traducción anclada al léxico correcto es además aceptable, respetuosa con el registro y comprensible para un hablante. Esa validación queda como la pieza pendiente del trabajo y se recoge en las líneas futuras del Capítulo 5.",
]

TXT_41_EXTRA = [
    "El entorno se declara por completo en pyproject.toml y queda congelado en uv.lock, de modo que la reconstrucción no depende de qué versiones estuvieran instaladas el día del experimento. Las piezas que determinan los resultados son cuatro: PyTorch con el backend MPS para el entrenamiento local, la biblioteca peft en su versión 0.19.1 para los adaptadores LoRA, sacrebleu y bert-score para las métricas, y lancedb como motor de los índices vectoriales. Las dos dependencias de servicios externos, anthropic y google-genai, son las únicas que exigen credenciales y por tanto las únicas que impiden reproducir el trabajo de forma completamente offline.",
    "La elección de trabajar sobre una estación local, y no sobre GPU alquilada en la nube, no es solo una cuestión de coste. Los 128 GB de memoria unificada del Apple M4 Max permiten cargar el modelo base de 600 millones de parámetros y entrenar el adaptador sin cuantización ni acumulación de gradientes, y el entrenamiento completo cabe en menos de media hora. Esto tiene una consecuencia que interesa al propósito del proyecto: el pipeline de ajuste fino de este trabajo puede ejecutarse en un portátil de gama alta, sin infraestructura especializada, lo que lo pone al alcance de una comunidad o de una universidad regional sin presupuesto de cómputo. La línea basada en el modelo de frontera, en cambio, sí depende de una API de pago y esa asimetría se discute en el Capítulo 5.",
]

TXT_423_EXTRA = [
    "El proceso parte de 6.779 registros extraídos del Nuevo Testamento Inga, que se reducen a 6.091 tras eliminar duplicados de la tupla (libro, capítulo, versículo) producidos por el parser, y de 7.955 versículos de la Reina-Valera de 1909. El join exacto sobre esa tupla devuelve 5.680 pares, lo que equivale al 93,3 por ciento de los versículos Inga disponibles y al 71,4 por ciento de los españoles. La diferencia entre ambas tasas se explica sola: la edición Inga no cubre el Nuevo Testamento completo con la misma granularidad de versículo, de modo que el español aporta más material del que puede emparejarse.",
    "Sobre esos 5.680 pares se aplican tres filtros de calidad, todos ellos deliberadamente conservadores. Se descarta el par cuyo texto, en cualquiera de las dos lenguas, tenga menos de cinco palabras, porque los fragmentos muy cortos suelen ser restos de encabezado y no oraciones. Se descarta también el par en el que más de la mitad de las palabras sean dígitos, que es la firma de una referencia cruzada mal segmentada. Y se descarta el par cuya razón de longitud entre las dos lenguas supere el factor cinco, indicio de que la correspondencia canónica emparejó un versículo con otro que no le corresponde. Los dos primeros filtros eliminan 37 pares y el tercero 74, con cierto solapamiento entre ambos conjuntos, y el corpus queda en 5.589 pares.",
    "Conviene ser explícito sobre lo que estos filtros no pueden hacer. Detectan desajustes groseros de longitud, pero no detectan un emparejamiento incorrecto entre dos versículos de longitud parecida. Si la numeración de la edición Inga se desplaza respecto a la española en un versículo, el par resultante pasa los tres filtros sin problema y entra al corpus con una traducción que no corresponde. En el apartado 4.6.5 se documenta un caso de este tipo detectado en la muestra de evaluación, y es la razón por la que la tasa de alineación del 93,3 por ciento debe leerse como una cota superior de la calidad real del emparejamiento.",
]

TXT_47_EXTRA = [
    "La reproducción completa del trabajo sigue el orden numérico de los notebooks y no requiere decisiones manuales. Los notebooks 00 a 07 reconstruyen el corpus desde las fuentes OCR y producen las particiones; el 08 levanta los cuatro índices vectoriales, único paso que consume la API de embeddings de Google; el 09 entrena el adaptador LoRA; y el 10 y el 11 ejecutan las diez corridas de evaluación, de las cuales las cinco del modelo de frontera consumen la API de Anthropic. Todos los pasos con componente aleatorio (la partición del corpus, el muestreo de los 100 ejemplos de evaluación y el barajado del entrenamiento) están fijados con semilla 42, de modo que una reejecución produce exactamente los mismos conjuntos.",
    "Los dos artefactos que no se regeneran solos son los índices vectoriales y el adaptador, y ambos se versionan en el repositorio: el adaptador ocupa 9,4 megabytes y los índices 127 megabytes, tamaños que caben en un repositorio Git sin recurrir a almacenamiento externo. Quien quiera reproducir únicamente la evaluación puede por tanto saltarse los notebooks 00 a 09 y ejecutar directamente el 10 y el 11 sobre los artefactos publicados, lo que reduce el coste de verificación a las llamadas a la API del modelo de frontera.",
    "El módulo src/eval/error_analysis.py, introducido en el apartado 4.6.3, se ejecuta sin credenciales de ningún tipo, porque opera únicamente sobre el fichero de predicciones ya generado. Cualquier lector puede regenerar la Tabla 11 completa y verificar los criterios de degeneración y de variante lingüística sin coste alguno, que era precisamente el objetivo de convertir el recuento de errores en código.",
]

P_LENGUA_INCORRECTA ="El problema de la lengua incorrecta en la dirección español-Inga. Este es el hallazgo cualitativo más relevante del trabajo, y no se aprecia bien solo con las métricas. Cuando se pide traducir del español al Inga, los sistemas que carecen de anclaje al Inga del Putumayo no devuelven una traducción mala: devuelven una traducción a otra lengua quechua. La Tabla 11 lo ilustra con Juan 4:32. La configuración A produce \"Jesustaq paykunata nirqan: Qankuna mana reqsiq kanaykichispaq mikhuq kani, nispa\", que es quechua sureño: las marcas -qa y -taq, el sufijo -nispa y las consonantes glotalizadas de mikhuq delatan la variante de mayor presencia en los datos de preentrenamiento de NLLB. La configuración C, el mismo Opus 4.7 pero sin contexto recuperado, produce \"Y pai nirka: Nuka charini mikui mikungapa, mana kankuna yachankichi\", una forma híbrida que ya se acerca al Inga en el léxico pero conserva la grafía con y de yachankichi, ajena al corpus. Solo con la recuperación aumentada, en la configuración D, la salida se ancla del todo: \"Paika nirkakunata: Nukaka kankuna mana iachaska sug mikuita charini mikungapa\", con la grafía iachaska en lugar de yachaska y la morfología que aparece en el corpus paralelo. El contexto recuperado no solo mejora el contenido: reorienta la salida hacia la variante correcta de una familia lingüística con docenas de variantes mutuamente ininteligibles."

P_ARTICULO_10 = "El mismo efecto aparece en el artículo 10 de la Constitución, \"El castellano es el idioma oficial de Colombia\". La configuración A devuelve \"Kastillanuqa Colombia suyupi rimaymi\", de nuevo quechua sureño (suyu por territorio, el enclítico -qa). Las configuraciones con recuperación producen en cambio formas ancladas al material Inga indexado: Opus 4.7 devuelve \"Lanku simi rimaimi ká Kulumbia Llagtapa idioma\" y Sonnet 4.6 \"Kastilla simi kami Kulumbia llagtapi kawsag tukui runakunapata rimai\", ambas con llagta y la grafía Kulumbia propias del corpus, aunque la primera recurre al préstamo idioma en lugar de traducirlo. Que el ejemplo provenga del corpus jurídico, y no del Nuevo Testamento, sugiere que el anclaje por recuperación funciona también fuera del dominio bíblico que domina el corpus."

P_ARTICULO_10B = "Conviene advertir, no obstante, que este ejemplo concreto arrastra un problema de la propia referencia. El texto Inga emparejado con el artículo 10 en el corpus no traduce la frase sobre el castellano, sino la que reconoce las lenguas de los pueblos indígenas, y varias configuraciones interpretaron la raíz iura como árbol y produjeron traducciones sobre el idioma de los árboles. El caso ilustra a la vez un límite del sistema y un límite del corpus; esto último se retoma en el apartado 4.6.5."


# ------------------------------------------------------------------ main

def main():
    if not BASE.exists():
        shutil.copy2(DOCX, BASE)
        print(f"base intocable guardada -> {BASE.name}")
    shutil.copy2(BASE, DOCX)
    doc = docx.Document(DOCX)

    def find_p(pred, que):
        hits = [p for p in doc.paragraphs if pred(p)]
        if len(hits) != 1:
            die(f"esperaba 1 parrafo para {que}, encontre {len(hits)}")
        return hits[0]

    def is_h(p, txt):
        return p.style.name.startswith("Heading") and p.text.strip() == txt

    def starts(p, txt):
        return p.text.strip().startswith(txt)

    # Referencias a las tablas que se reescriben, tomadas ANTES de insertar la Tabla 12:
    # al insertarla, los indices de doc.tables se desplazan.
    t10 = doc.tables[10]
    t11 = doc.tables[11]
    t6 = doc.tables[6]

    # --- plantillas ---
    TPL_H3 = find_p(lambda p: is_h(p, "4.2.5. Particiones del corpus"), "plantilla H3")
    TPL_BODY = find_p(lambda p: starts(p, "El Notebook 07 unifica las salidas"), "plantilla cuerpo")
    TPL_CAP = find_p(lambda p: p.style.name == "Caption" and "Distribución del corpus paralelo train" in p.text, "plantilla pie de tabla")
    TPL_NOTA = find_p(lambda p: starts(p, "Nota. Elaboración propia. La columna MP"), "plantilla nota")

    # ============================================ 1. CIFRAS
    print("== 1. reconciliacion de cifras ==")
    if t6.rows[0].cells[0].text.strip() != "Partición":
        die("la tabla 6 no es la de particiones")
    reemplazos_t6 = {"4.471": "4.512", "558": "564", "560": "565", "5.589": "5.641"}
    n = 0
    for row in t6.rows:
        for cell in row.cells:
            txt = cell.text.strip()
            if txt in reemplazos_t6:
                set_cell(cell, reemplazos_t6[txt], negrita=(txt == "5.589"))
                n += 1
    if n != 8:
        die(f"esperaba 8 celdas a corregir en la Tabla 6, corregi {n}")
    print(f"  ok [Tabla 6: {n} celdas -> 4.512 / 564 / 565 / 5.641]")

    def sustituir(p, viejo, nuevo, etiqueta):
        hecho = False
        for r in p.runs:
            if viejo in r.text:
                r.text = r.text.replace(viejo, nuevo, 1)
                hecho = True
                break
        if not hecho:
            die(f"[{etiqueta}] no encontre {viejo!r} en un run del parrafo")
        print(f"  ok [{etiqueta}]")

    p = find_p(lambda q: starts(q, "El índice de ejemplos indexa los 4.471"), "indice de ejemplos")
    sustituir(p, "4.471", "4.512", "4.3: indice de ejemplos = 4.512 pares")

    p = find_p(lambda q: starts(q, "La configuración de LoRA introdujo"), "params LoRA")
    sustituir(p, "aproximadamente 1,18 millones", "2,36 millones", "4.4: 2,36 M parametros")
    sustituir(p, "0,19 %", "0,38 %", "4.4: 0,38 % del modelo base")

    p = find_p(lambda q: starts(q, "Primero, el corpus paralelo Inga-Español alcanzó 5.589"), "conclusion 1 cap5")
    sustituir(p, "5.589 pares verificados", "5.641 pares verificados", "5.1: corpus = 5.641 pares")

    # ============================================ 1a. ALINEACION DE LOS PIES DE TABLA
    # Los pies llevan el identificador y el titulo en dos lineas separadas por un salto manual.
    # Word justifica las lineas que terminan en salto manual, de modo que "Tabla" y su numero
    # acaban separados de extremo a extremo del renglon. Alinear el pie a la izquierda lo evita
    # y es ademas lo que pide la norma APA para el identificador. Los pies de figura van
    # centrados y no sufren el problema.
    print("== 1a. alineacion izquierda de los pies de tabla ==")
    alineados = 0
    for p in doc.paragraphs:
        if p.style.name != "Caption" or not p.text.strip().startswith("Tabla"):
            continue
        ppr = p._p.get_or_add_pPr()
        if ppr.find(w("jc")) is None:
            jc = OxmlElement("w:jc")
            jc.set(qn("w:val"), "left")
            ppr.append(jc)
            alineados += 1
    if alineados != 11:
        die(f"esperaba alinear 11 pies de tabla, alinee {alineados}")
    print(f"  ok [{alineados} pies de tabla a la izquierda]")

    # ============================================ 1b. RENUMERACION DE TABLAS
    # La tabla nueva del apartado 4.2.7 se inserta antes que las actuales 7 a 11, y el campo
    # SEQ de Word numera por orden de aparicion: la nueva pasa a ser la Tabla 7 y las demas
    # corren una posicion. Las referencias del texto hay que moverlas con ellas. Se hace ANTES
    # de insertar el contenido nuevo, que ya viene escrito con la numeracion final.
    print("== 1b. renumeracion de las referencias a tablas (N -> N+1 para N>=7) ==")
    movidas = 0
    for p in doc.paragraphs:
        if p.style.name in ("Caption",) or "table of figures" in p.style.name.lower():
            continue
        for r in p.runs:
            nuevo = re.sub(r"Tabla (\d+)",
                           lambda m: f"Tabla {int(m.group(1)) + 1}" if int(m.group(1)) >= 7 else m.group(0),
                           r.text)
            if nuevo != r.text:
                movidas += len(re.findall(r"Tabla \d+", r.text))
                r.text = nuevo
    if movidas != 11:
        die(f"esperaba renumerar 11 referencias a tablas en prosa, renumere {movidas}")
    print(f"  ok [{movidas} referencias movidas: metricas 8->9, intra-Claude 9->10, ejemplos 10->11, errores 11->12]")

    # ============================================ 2. RENUMERACION 4.6.x
    print("== 2. renumeracion de 4.6.1 y 4.6.2 ==")
    h_cuali = find_p(lambda q: is_h(q, "4.6.1. Análisis cualitativo de las traducciones"), "H 4.6.1")
    sustituir(h_cuali, "4.6.1.", "4.6.2.", "4.6.1 -> 4.6.2 (analisis cualitativo)")
    h_taxo = find_p(lambda q: is_h(q, "4.6.2. Taxonomía de errores"), "H 4.6.2")
    sustituir(h_taxo, "4.6.2.", "4.6.3.", "4.6.2 -> 4.6.3 (taxonomia)")

    # ============================================ 3. INSERCIONES
    print("== 3. contenido nuevo ==")
    log = []

    def ins_antes(ancla_p, elementos):
        for el in elementos:
            ancla_p._p.addprevious(el)

    def cuerpo(textos):
        return [clone_para(TPL_BODY, t) for t in textos]

    def heading(txt):
        return clone_para(TPL_H3, txt)

    def tabla_nueva(filas):
        t = doc.add_table(rows=len(filas), cols=len(filas[0]))
        t.style = doc.tables[6].style
        for ri, fila in enumerate(filas):
            for ci, val in enumerate(fila):
                celda = t.rows[ri].cells[ci]
                celda.paragraphs[0].add_run(val)
                if ri == 0:
                    celda.paragraphs[0].runs[0].bold = True
        return t

    # -- ampliacion de 4.1 (antes de 4.2)
    a42 = find_p(lambda q: is_h(q, "4.2. Construcción del corpus paralelo"), "H 4.2")
    ins_antes(a42, cuerpo(TXT_41_EXTRA))
    log.append("4.1 ampliado")

    # -- ampliacion de 4.2.3 (antes de 4.2.4)
    a424 = find_p(lambda q: is_h(q, "4.2.4. Antihua Pacay como recurso exploratorio"), "H 4.2.4")
    ins_antes(a424, cuerpo(TXT_423_EXTRA))
    log.append("4.2.3 ampliado")

    # -- 4.2.7 + Tabla 12 (antes de 4.3)
    a43 = find_p(lambda q: is_h(q, "4.3. Base de conocimiento e indexación vectorial"), "H 4.3")
    ins_antes(a43, [heading(H_427)] + cuerpo(TXT_427))
    ins_antes(a43, [clone_caption(TPL_CAP, CAP_12)])
    t12 = tabla_nueva(TABLA_12)
    a43._p.addprevious(t12._tbl)
    ins_antes(a43, [clone_para(TPL_NOTA, NOTA_12)])
    log.append("4.2.7 + Tabla 12")

    # -- ampliacion de 4.3 y nueva 4.3.1 (antes de 4.4)
    a44 = find_p(lambda q: is_h(q, "4.4. Adaptación de NLLB-200 mediante LoRA bidireccional"), "H 4.4")
    ins_antes(a44, cuerpo(TXT_43_EXTRA) + [heading(H_431)] + cuerpo(TXT_431))
    log.append("4.3 ampliado + 4.3.1")

    # -- 4.4.1 (antes de 4.5)
    a45 = find_p(lambda q: is_h(q, "4.5. Pipeline LLM + RAG con Claude"), "H 4.5")
    ins_antes(a45, [heading(H_441)] + cuerpo(TXT_441))
    log.append("4.4.1")

    # -- 4.5.3 (antes de 4.6)
    a46 = find_p(lambda q: is_h(q, "4.6. Evaluación comparativa"), "H 4.6")
    ins_antes(a46, [heading(H_453)] + cuerpo(TXT_453))
    log.append("4.5.3")

    # -- 4.6.1 protocolo: justo antes del (renumerado) 4.6.2 analisis cualitativo
    ins_antes(h_cuali, [heading(H_461)] + cuerpo(TXT_461))
    log.append("4.6.1 protocolo")

    # -- ampliacion cualitativa: antes del pie de la Tabla 10
    cap10 = find_p(lambda q: q.style.name == "Caption" and "Ejemplos de traducción por configuración" in q.text, "pie Tabla 10")
    ins_antes(cap10, cuerpo(TXT_CUALI_EXTRA))
    log.append("analisis cualitativo ampliado")

    # -- taxonomia: reemplazar el cuerpo actual entre el heading 4.6.3 y el pie de la Tabla 11
    cap11 = find_p(lambda q: q.style.name == "Caption" and "Recuento de errores por tipo" in q.text, "pie Tabla 11")
    viejos = []
    el = h_taxo._p.getnext()
    while el is not None and el is not cap11._p:
        if el.tag == w("p"):
            viejos.append(el)
        el = el.getnext()
    if len(viejos) != 6:
        die(f"esperaba 6 parrafos de la taxonomia vieja, hay {len(viejos)}")
    for v in viejos:
        v.getparent().remove(v)
    for nuevo in cuerpo(TXT_TAXO):
        cap11._p.addprevious(nuevo)
    log.append(f"taxonomia reescrita ({len(viejos)} parrafos viejos fuera, {len(TXT_TAXO)} nuevos)")

    # -- 4.6.4 y 4.6.5 cierran el 4.6, en ese orden, justo antes de 4.7
    a47 = find_p(lambda q: is_h(q, "4.7. Repositorio de código y datos"), "H 4.7")
    ins_antes(a47, [heading(H_464)] + cuerpo(TXT_464) + [heading(H_465)] + cuerpo(TXT_465))
    log.append("4.6.4 + 4.6.5")

    # -- ampliacion de 4.7 (antes del Capitulo 5)
    a5 = find_p(lambda q: is_h(q, "5. Conclusiones y trabajo futuro"), "H 5")
    ins_antes(a5, cuerpo(TXT_47_EXTRA))
    log.append("4.7 ampliado")

    # ============================================ 4. TABLAS 10 y 11 y notas
    print("== 4. tablas 10 y 11 ==")
    if len(t10.rows) != 4 or len(t10.columns) != 6:
        die(f"la tabla de ejemplos no es 4x6, es {len(t10.rows)}x{len(t10.columns)}")
    # la columna "Dirección" valia es-Inga en las tres filas: se elimina y se dice en la nota,
    # lo que deja respirar a las columnas de texto, que son las que cuestan de leer
    borrar_columna(t10, 1)
    for ri, fila in enumerate(TABLA_10):
        for ci, val in enumerate(fila):
            set_cell(t10.rows[ri].cells[ci], val, negrita=(ri == 0))
    print("  ok [Tabla 10 con Opus y Sonnet lado a lado]")

    if len(t11.rows) != 7 or len(t11.columns) != 7:
        die(f"la tabla 11 no es 7x7, es {len(t11.rows)}x{len(t11.columns)}")
    for ri, fila in enumerate(TABLA_11):
        for ci, val in enumerate(fila):
            set_cell(t11.rows[ri].cells[ci], val, negrita=(ri == 0))
    print("  ok [Tabla 11 con indicadores reproducibles]")

    for texto_ini, nuevo, etiqueta in [
        ("Nota. Elaboración propia a partir del Notebook 11. Las salidas se transcriben", NOTA_10, "nota Tabla 10"),
        ("Nota. Elaboración propia a partir del Notebook 11. Los conteos de repetición", NOTA_11, "nota Tabla 11"),
    ]:
        p = find_p(lambda q, t=texto_ini: starts(q, t), etiqueta)
        nueva = clone_para(TPL_NOTA, nuevo)
        p._p.addprevious(nueva)
        p._p.getparent().remove(p._p)
        print(f"  ok [{etiqueta}]")

    # ============================================ 5. parrafos mal atribuidos
    print("== 5. parrafos que citaban salidas de Sonnet como si fueran de Opus ==")
    p = find_p(lambda q: starts(q, "El problema de la lengua incorrecta"), "parrafo lengua incorrecta")
    p._p.addprevious(clone_para(TPL_BODY, P_LENGUA_INCORRECTA))
    p._p.getparent().remove(p._p)
    print("  ok [parrafo de la lengua incorrecta reescrito con la corrida principal]")

    p = find_p(lambda q: starts(q, "El mismo efecto aparece en el artículo 10"), "parrafo articulo 10")
    for nuevo in (P_ARTICULO_10, P_ARTICULO_10B):
        p._p.addprevious(clone_para(TPL_BODY, nuevo))
    p._p.getparent().remove(p._p)
    print("  ok [parrafo del articulo 10 reescrito + nota sobre el ruido de alineacion]")

    # ============================================ 6. TOC dirty
    doc.save(DOCX)

    for linea in log:
        print(f"  + {linea}")
    print(f"\nDocx expandido: {DOCX}")
    print("Paso siguiente: marcar los TOC como dirty y regenerar los indices en Word.")


if __name__ == "__main__":
    main()
