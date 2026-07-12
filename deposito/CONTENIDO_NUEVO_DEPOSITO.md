# Contenido nuevo para el deposito (expansion del Capitulo 4)

Cada cifra de este documento sale de un fichero del repositorio. La procedencia se anota
entre corchetes al final de cada bloque para el sweep humano; esas anotaciones NO se
insertan en el docx.

---

## BLOQUE 1 -- Nueva subseccion 4.3.1 (va detras de 4.3, antes de 4.4)

### 4.3.1. Validacion cualitativa de la recuperacion

Antes de medir la calidad de las traducciones conviene comprobar que el componente de
recuperacion hace lo que se espera de el. Un sistema RAG puede fallar en dos lugares
distintos y el error se ve igual desde fuera: puede que el generador traduzca mal, o puede
que el recuperador le entregue un contexto inutil y el generador simplemente lo ignore. Por
eso el Notebook 08 cierra con una bateria de tres consultas de sondeo, una por cada nivel de
dificultad, cuyas salidas quedaron guardadas en el propio notebook.

La primera consulta es una palabra aislada, wasi (casa). El indice lexico devuelve como
primeras tres entradas casa (s): wasi, wasi (s): casa y wasi kancha (s): patio de la casa. El
indice gramatical recupera fragmentos de la gramatica de Levinsohn que utilizan huasi como
ejemplo para explicar los posposicionales cancha (fuera de) y ucu (dentro de). La
recuperacion lexica y la gramatical funcionan aqui como se esperaba: la primera devuelve el
lema exacto en ambas direcciones de consulta y la segunda devuelve reglas donde la palabra
aparece en uso.

La segunda consulta es una locucion, imasa parlangapa (como decir). El interes de este caso
esta en el indice gramatical, que devuelve tres pasajes de Levinsohn dedicados precisamente
al comportamiento de imasa: su uso para expresar semejanza con una accion, su frecuencia en
interrogativas y su coocurrencia con el infinitivo en -sca. Es el tipo de conocimiento que un
modelo de lenguaje de frontera no puede tener memorizado para el Inga y que solo puede
llegarle por el contexto.

La tercera consulta es una oracion completa, Taita Diuska runakunata kuianmi (Dios ama a las
personas). El indice de ejemplos devuelve Efesios 2:4, 1 Juan 5:2 y 1 Juan 4:20, los tres
versiculos sobre el amor de Dios, lo que confirma que la busqueda semantica sobre
embeddings opera a nivel de significado y no de coincidencia de superficie.

La misma bateria expone dos debilidades que conviene registrar. En la tercera consulta, el
indice lexico devuelve entre sus tres primeras entradas panela (s): dusi, miski, que no
guarda relacion con la oracion consultada: cuando la consulta es una oracion entera y no un
lema, el indice lexico pierde precision porque el embedding de la oracion no se parece al
embedding de ninguna entrada de diccionario en particular. En la primera consulta ocurre algo
distinto y mas incomodo. Entre los ejemplos recuperados para wasi aparece Marcos 6:38, cuyo
texto Inga menciona efectivamente wasi pero cuyo texto espanol alineado habla de panes y
peces, sin mencionar ninguna casa. El par recuperado es correcto respecto al indice y erroneo
respecto al contenido: es ruido de alineacion del corpus, heredado de la correspondencia
canonica versiculo a versiculo, que la recuperacion no puede corregir y que se traslada
intacto al prompt. Este punto se retoma en el apartado 4.6.5.

[Fuente: outputs ejecutados de notebooks/08_indexacion_vectorial.ipynb; conteos de indices en
lance_indexes/]

---

## BLOQUE 2 -- Nueva subseccion 4.4.1 (va al final de 4.4, tras la Figura 10)

### 4.4.1. Lectura de la curva de entrenamiento

Los hiperparametros del adaptador quedaron fijados en adapter_config.json: rango r igual a
16, factor de escala alpha igual a 32, dropout de 0,1 y aplicacion restringida a las matrices
de proyeccion de consulta y de valor de los bloques de atencion, q_proj y v_proj. El
entrenamiento corrio tres epocas completas sobre los 9.024 ejemplos bidireccionales, lo que
da 3.384 pasos de optimizacion con tamano de lote 8, tasa de aprendizaje pico de 3e-4 y
calentamiento lineal durante los primeros 100 pasos. El proceso tardo 1.606 segundos, es
decir 26,8 minutos, sobre la GPU integrada del equipo mediante el backend MPS, a un ritmo de
16,86 ejemplos por segundo. El adaptador resultante ocupa 9,46 MB frente a los 2,46 GB del
modelo base, que es el argumento economico de LoRA y la razon por la que este experimento
cabe en un portatil.

La curva de perdida de la Figura 10 admite una lectura que conviene hacer explicita, porque
condiciona la interpretacion de los resultados del apartado 4.6. La perdida de entrenamiento
arranca en 10,71 en el paso 20 y cae a 6,01 en el paso 3.380, con un minimo de 5,92. La caida
no esta repartida de manera uniforme: casi toda ocurre en la primera epoca. La perdida de
validacion lo confirma con claridad, porque baja de 6,05 al terminar la primera epoca a 5,97
en la segunda y a 5,94 en la tercera. Las dos ultimas epocas, que consumen dos tercios del
computo, aportan una mejora de 0,11 en la perdida de validacion.

Lo que muestra esa curva es un adaptador que satura. El modelo aprende deprisa lo que puede
aprender con 4.512 pares y despues deja de aprender, y no porque empiece a sobreajustar (la
perdida de validacion sigue bajando, aunque sea poco) sino porque agota la senal disponible en
el corpus. La consecuencia practica es que ampliar el numero de epocas no era el camino: el
techo no lo pone el presupuesto de entrenamiento sino el tamano y la homogeneidad del corpus,
que procede casi por completo de un unico registro textual. Esta observacion explica por que
la configuracion B mejora de forma clara sobre la A pero se queda muy por debajo de la D, y
es la razon de fondo por la que el trabajo futuro apunta primero a ampliar el corpus y solo
despues a escalar el modelo.

[Fuente: models/nllb-inga-lora-v1/adapter_config.json, checkpoint-3384/trainer_state.json,
training_history.json]

---

## BLOQUE 3 -- Nueva subseccion 4.5.3 (va al final de 4.5, tras 4.5.2)

### 4.5.3. Presupuesto de contexto del prompt

El contexto que se inyecta en cada llamada esta acotado de forma deliberada y ese limite tiene
consecuencias. Por cada oracion a traducir, el modulo claude_rag.py compone un prompt de
usuario con tres secciones: las cinco entradas lexicas mas cercanas, en formato lema
(categoria): glosa; los tres fragmentos gramaticales mas cercanos, cada uno truncado a 400
caracteres; y los cinco ejemplos paralelos mas cercanos, ordenados segun la direccion de
traduccion. La respuesta se limita a 256 tokens.

El truncamiento de los fragmentos gramaticales a 400 caracteres es la decision mas discutible
del diseno. Se tomo para acotar el coste por llamada y mantener el prompt en un tamano
predecible, pero corta pasajes de Levinsohn a mitad de explicacion. En la consulta de sondeo
sobre imasa que se describe en el apartado 4.3.1 se ve el efecto: el fragmento recuperado
introduce la regla y se interrumpe antes de los ejemplos que la ilustran. Un modelo de
frontera puede completar la regla por analogia con el quechua sureno, y eso es exactamente lo
que no se quiere, porque el objetivo es que produzca Inga y no una lengua emparentada. La
alternativa habria sido segmentar la gramatica en unidades semanticamente completas en lugar
de trocear por longitud, y queda anotada como mejora del indice gramatical.

La direccion de traduccion determina de que indice se recuperan los ejemplos. Para inga2es se
consulta el indice ejemplos, construido sobre el texto Inga; para es2inga se consulta
ejemplos_es, construido sobre el texto espanol. La consulta se hace siempre en la lengua de
origen, de modo que la busqueda semantica opere sobre embeddings de la misma lengua que la
oracion de entrada. Los dos indices contienen los mismos 4.512 pares del conjunto de
entrenamiento y se diferencian solo en el campo que se vectoriza.

Conviene precisar un punto que el resumen del trabajo podia dejar ambiguo. Los indices de
ejemplos suman 9.024 registros entre los dos, pero corresponden a 4.512 pares distintos
indexados por sus dos caras. El numero de ejemplos paralelos unicos disponibles para la
recuperacion es 4.512, no 9.024.

[Fuente: src/models/claude_rag.py (build_prompt, translate), src/rag/retriever.py, outputs de
notebooks/08_indexacion_vectorial.ipynb]

---

## BLOQUE 4 -- Nueva subseccion 4.6.1 (entra ANTES del actual "Analisis cualitativo", que pasa a 4.6.2)

### 4.6.1. Protocolo de evaluacion y validez de las metricas

Las tres metricas se calculan con el modulo src/eval/metrics.py, que envuelve
implementaciones estandar: BLEU a nivel de corpus con sacrebleu, chrF++ con sacrebleu y
word_order igual a 2, y BERTScore F1 sobre XLM-RoBERTa multilingue sin reescalado de linea
base. Fijar estas decisiones por escrito importa mas de lo que parece, porque BLEU admite
variantes de tokenizacion y de suavizado que cambian el resultado varios puntos y hacen
incomparables cifras que se presentan como equivalentes.

Hay una limitacion en la configuracion de BERTScore que debe declararse porque afecta a la
lectura de la Tabla 8. El scorer se instancia con lang igual a "es" para las dos direcciones
de traduccion. En la direccion Inga-espanol esto es correcto, porque la referencia esta en
espanol. En la direccion espanol-Inga no lo es: la referencia esta en Inga, una lengua que
XLM-RoBERTa no vio durante su preentrenamiento, y el modelo la procesa como si fuera espanol.
El resultado es que en esa direccion BERTScore no mide adecuacion semantica sino, mas bien,
plausibilidad de las subunidades ortograficas, y por eso sus valores se comprimen en un rango
estrecho y varian poco entre configuraciones. La lectura correcta es que BERTScore aporta
informacion util en Inga-espanol y debe tomarse con reservas en espanol-Inga, direccion en la
que chrF++, que opera sobre caracteres y no depende de ningun modelo preentrenado, es la
metrica mas fiable de las tres. Ninguna conclusion del trabajo se sostiene unicamente sobre
el BERTScore de la direccion espanol-Inga.

La muestra de evaluacion son 100 ejemplos extraidos del conjunto de validacion con
random_state igual a 42. Su composicion no es homogenea: 99 versiculos del Nuevo Testamento y
un unico articulo de la Constitucion, el articulo 10. Esa proporcion refleja la del corpus,
pero implica que las cifras de la Tabla 8 describen el rendimiento del sistema sobre registro
biblico y no autorizan a extrapolarlo al registro juridico ni al conversacional. El unico
ejemplo constitucional de la muestra se comenta por separado en el apartado 4.6.2 justamente
porque es el unico.

Las configuraciones A y B se generan localmente con busqueda en haz de cuatro caminos y un
maximo de 128 tokens nuevos; las configuraciones C, D y E se generan por API con un maximo de
256 tokens. Las diez corridas comparten los mismos 100 ejemplos, condicion necesaria para que
las diferencias entre columnas sean atribuibles a la configuracion y no a la muestra.

Queda por decir lo que el protocolo no cubre. No se midio sobre el conjunto de prueba, que
permanece intacto con sus 565 ejemplos: todas las cifras de este capitulo son de validacion,
lo que en rigor las convierte en estimaciones de desarrollo y no en una evaluacion final
independiente. Tampoco se calcularon intervalos de confianza ni pruebas de significancia por
remuestreo, de modo que las diferencias pequenas entre configuraciones, y en particular la
distancia de 1,13 puntos BLEU entre D y E en la direccion espanol-Inga, no pueden declararse
estadisticamente significativas. Las diferencias grandes, como los 13,5 puntos que separan a C
de D, son de una magnitud que ningun intervalo razonable haria desaparecer.

[Fuente: src/eval/metrics.py, notebooks/10_medicion_nllb_configs.ipynb,
notebooks/11_medicion_llm_rag.ipynb, datos/splits/test.jsonl]

---

## BLOQUE 5 -- Parrafos que se ANADEN al final del actual "Analisis cualitativo" (ya 4.6.2), antes de la Tabla 10

La inspeccion caso a caso se puede respaldar con una medida agregada que no depende del
criterio del lector: la longitud de las salidas. La referencia Inga del conjunto de
evaluacion tiene 21,3 palabras de media y la referencia espanola 20,3. En la direccion
espanol-Inga, las configuraciones con recuperacion se mantienen cerca de ese orden de
magnitud, con 16,5 palabras la D y 17,6 la E, mientras que la configuracion B se dispara
hasta 27,3 palabras. Ese exceso no es riqueza expresiva: es el bucle de repeticion que se
cuantifica en el apartado siguiente, inflando artificialmente el recuento. La configuracion A,
en el extremo opuesto, se queda en 14,5 palabras, por debajo de la referencia, lo que encaja
con salidas cortas en una lengua que el modelo domina mal.

En la direccion Inga-espanol el patron se invierte. Todas las configuraciones producen
salidas mas largas que la referencia, entre 24,3 y 33,4 palabras frente a las 20,3 del gold.
Aqui la explicacion no es la degeneracion sino la naturaleza del texto fuente: los versiculos
de la Reina-Valera de 1909 son sintacticamente comprimidos y arcaizantes, y tanto NLLB como
Claude tienden a desplegarlos en castellano contemporaneo, mas explicito y mas largo. Es un
sesgo de estilo que las metricas de n-gramas penalizan aunque la traduccion sea correcta, y
conviene tenerlo presente al comparar las cifras de esta direccion con las de la literatura,
donde las referencias rara vez son biblicas.

---

## BLOQUE 6 -- REEMPLAZA integramente el texto del actual 4.6.2 "Taxonomia de errores" (pasa a 4.6.3) y su Tabla 11

### 4.6.3. Taxonomia de errores

El analisis cualitativo se apoya en casos concretos. Para respaldarlo con una mirada de
conjunto, las salidas de las cinco configuraciones sobre los 100 ejemplos de la muestra se
clasificaron por tipo de fallo mediante criterios automaticos y deterministas, implementados
en el modulo src/eval/error_analysis.py. La tabla que sigue puede regenerarse desde el fichero
de predicciones sin intervencion manual, que es la condicion para que un recuento de errores
sea algo mas que una impresion. Los criterios se enuncian antes de mostrar los resultados,
porque de ellos depende como han de leerse.

Una salida se marca como degenerada cuando contiene un n-grama de hasta cuatro palabras
repetido tres o mas veces de forma consecutiva. Se marca como desbordada cuando supera en mas
de dos veces y media la longitud de la referencia. Y para la direccion espanol-Inga, que es
donde se juega la cuestion de la variante, se emplean dos indicadores ortograficos y lexicos
en lugar de un juicio subjetivo sobre a que lengua se parece la salida.

El primero aprovecha un rasgo de la escritura del Inga del Putumayo que resulta
inusualmente discriminante. Sobre los 823.744 caracteres de texto Inga del conjunto de
entrenamiento, la letra y no aparece ni una sola vez y la letra q aparece seis veces, un
0,001 por ciento. El Inga escribe iuiai donde el quechua sureno escribe yuyay, y kan donde
aquel escribe qan. Ambos grafemas, en cambio, son centrales en la ortografia del quechua
sureno y del kichwa ecuatoriano. La presencia de una q o una y en una salida es por tanto
evidencia objetiva de que el sistema no esta escribiendo en la variante del corpus. El segundo
indicador mide la fraccion de palabras de la salida que pertenecen al vocabulario Inga del
entrenamiento, formado por 13.575 tipos, y considera la salida anclada al Inga cuando esa
fraccion alcanza la mitad.

Los resultados de la Tabla 11 son mas nitidos de lo que las metricas agregadas dejaban
entrever. El modelo multilingue sin adaptar (configuracion A) produce grafias ajenas al Inga
en 98 de los 100 ejemplos y solo una de sus salidas alcanza el umbral de anclaje lexico. No
esta traduciendo mal al Inga: no esta traduciendo al Inga en absoluto, sino al quechua que
conoce, que es el sureno del par quy_Latn con el que se le fuerza a decodificar. Ninguna
metrica de la Tabla 8 dice esto, y sin embargo es lo primero que habria que saber del sistema.

El ajuste fino corrige el idioma y rompe el decodificador. La configuracion B invierte por
completo los dos indicadores, con 98 salidas ancladas al vocabulario Inga y solo una con
grafia ajena, lo que confirma que 4.512 pares bastan para ensenarle a NLLB en que lengua debe
escribir. Pero al mismo tiempo degenera en 51 de los 100 ejemplos, mas de la mitad, y esa es
la explicacion completa de por que su BLEU en espanol-Inga se queda en 1,79 pese a haber
aprendido la variante correcta. El adaptador aprende el lexico y pierde la capacidad de
detenerse.

La recuperacion aumentada consigue las dos cosas a la vez. La configuracion D reduce la
grafia ajena a 5 ejemplos, ancla 98 salidas al vocabulario Inga y no degenera en ninguno,
mientras que la configuracion C, el mismo modelo sin contexto recuperado, se queda a medio
camino con 60 salidas de grafia ajena y solo 38 ancladas. La diferencia entre C y D no esta en
el modelo, que es el mismo, sino unicamente en lo que se le entrega en el prompt. Es la
evidencia mas directa de que, para este par de lenguas, el conocimiento que hace falta no esta
en los pesos sino en el contexto.

Un cuarto tipo de error no admite recuento automatico y aparece con regularidad en la
inspeccion: los fallos de referencia y concordancia. En oraciones con varias clausulas
subordinadas, incluso la configuracion D confunde a veces quien hace que, o desplaza un sujeto
de una clausula a otra. Son errores sutiles, que no degradan la fluidez de la salida y que por
eso pueden pasar inadvertidos a una metrica de superficie, pero que alteran el sentido. Su
persistencia en la mejor configuracion marca uno de los limites actuales del sistema.

Conviene cerrar con un dato en positivo: ninguna de las cinco configuraciones produjo salidas
vacias o truncadas. Todas devuelven siempre una traduccion completa, aunque sea defectuosa. El
problema, cuando lo hay, no es de cobertura sino de calidad o de variante.

TABLA 11 (nueva, reemplaza la actual):

Tabla 11
Recuento de errores por tipo y configuracion sobre los 100 ejemplos del conjunto de validacion

| Indicador | Direccion | A | B | C | D | E |
| Degeneracion por repeticion | Inga-es | 6 | 8 | 1 | 1 | 1 |
| Degeneracion por repeticion | es-Inga | 6 | 51 | 0 | 0 | 0 |
| Desbordamiento de longitud (>2,5x ref) | Inga-es | 17 | 7 | 13 | 12 | 13 |
| Grafia ajena al Inga (letras q o y) | es-Inga | 98 | 1 | 60 | 5 | 6 |
| Salida anclada al vocabulario Inga | es-Inga | 1 | 98 | 38 | 98 | 97 |
| Salidas vacias o truncadas | ambas | 0 | 0 | 0 | 0 | 0 |

Nota. Elaboracion propia a partir de datos/predicciones_val_completo.jsonl mediante el modulo
src/eval/error_analysis.py, sobre la corrida principal con Claude Opus 4.7. Todos los
indicadores son deterministas y reproducibles; los criterios se definen en el texto. Las
filas de grafia y anclaje no son excluyentes entre si.

[Fuente: src/eval/error_analysis.py sobre las predicciones de Opus recuperadas del commit
189833b]

---

## BLOQUE 7 -- Nueva subseccion 4.6.4 (tras la taxonomia) + Tabla 10 ampliada

### 4.6.4. Comparacion intra-Claude: por que el modelo mayor aprovecha mejor el contexto

La Tabla 9 registra que Opus 4.7 aventaja a Sonnet 4.6 en 5,92 puntos BLEU en la
configuracion D, pero no explica de donde sale esa ventaja. Los indicadores del apartado
anterior, aplicados a las dos corridas por separado, permiten responderlo.

En la configuracion C, sin contexto recuperado, los dos modelos se comportan practicamente
igual, y ambos mal: Sonnet produce grafia ajena al Inga en 83 de los 100 ejemplos y Opus en
60, con anclajes lexicos de 5 y 38 respectivamente. Ninguno de los dos sabe escribir Inga por
su cuenta, lo que era esperable. La diferencia aparece cuando se les entrega el mismo contexto
recuperado. En la configuracion D, Opus deja solo 5 salidas con grafia ajena, frente a las 19
de Sonnet. Es decir, ante ejemplos y vocabulario identicos, el modelo de mayor capacidad se
adhiere con mas rigor a la ortografia y al lexico que se le muestran, mientras que el menor se
desliza con mas frecuencia hacia la variante quechua que ya traia aprendida.

La ventaja de Opus, por tanto, no es una mayor competencia previa en Inga, lengua que ninguno
de los dos conoce, sino una mayor fidelidad al contexto que se le entrega. Es un matiz con
consecuencias practicas: en un sistema RAG sobre una lengua de recursos escasos, lo que
diferencia a los modelos no es tanto lo que saben como cuanto se dejan corregir por lo que se
les muestra. Explica ademas la anomalia de la configuracion E, donde Sonnet obtiene mejor BLEU
en la direccion Inga-espanol: cuando el contexto incluye una semilla defectuosa producida por
el LoRA, la mayor docilidad de Opus hacia el contexto deja de ser una virtud, porque lo que
respeta con fidelidad es un error.

La Tabla 10 recoge tres ejemplos de la muestra con las salidas de ambos modelos, de modo que
la diferencia pueda inspeccionarse directamente.

TABLA 10 (reemplaza la actual; 6 columnas):

Tabla 10
Ejemplos de traduccion por configuracion, direccion y modelo sobre el conjunto de validacion

| Referencia | Direccion | Texto fuente | A (NLLB zero-shot) | D con Opus 4.7 | D con Sonnet 4.6 |
| Juan 4:32 | es-Inga | Yo tengo una comida que comer, que vosotros no sabeis. | Jesustaq paykunata nirqan: Qankuna mana reqsiq kanaykichispaq mikhuq kani, nispa. (quechua sureno) | Paika nirkakunata: Nukaka kankuna mana iachaska sug mikuita charini mikungapa. (Inga) | Paika painakunata nirka: Nukaka mikungapa mikuika tian, kamkunaka mana yachangichu. (Inga con grafia y) |
| Lucas 24:38 | es-Inga | Mas el les dice: ¿Por que estais turbados, y suben pensamientos a vuestros corazones? | Jesustaq paykunata nirqan: ¿Imanasqataq llakikunkichis? ¿Imanasqataq sonqoykichispi yuyashankichis? (quechua sureno) | Pai nirkakunata: ¿Imapatak chasa manchaspa kangichi, i imapatak chasa sungullapi iuianakungichi? (Inga) | Paika nirkakunata: ¿Imapatak manchanakungichi, iuiaikunatak sungullapi wicharimungichi? (Inga) |
| Constitucion art. 10 | es-Inga | El castellano es el idioma oficial de Colombia. | Kastillanuqa Colombia suyupi rimaymi. (quechua sureno) | Lanku simi rimaimi ka Kulumbia Llagtapa idioma. (Inga) | Kastilla simi kami Kulumbia llagtapi kawsag tukui runakunapata rimai. (Inga) |

Nota. Elaboracion propia a partir de los Notebooks 10 y 11. Las salidas se transcriben
literalmente; los guiones de dialogo se normalizaron. La configuracion A es identica en ambas
corridas porque no interviene el modelo de lenguaje de frontera. La variante detectada se
indica entre parentesis. En Juan 4:32, la salida de Sonnet contiene la letra y (yachangichu),
grafema ausente del Inga del corpus.

[Fuente: predicciones de Opus (commit 189833b) y de Sonnet (HEAD),
datos/metricas_entrega2.json y datos/metricas_entrega2_sonnet.json]

---

## BLOQUE 8 -- Nueva subseccion 4.6.5 (cierra el 4.6)

### 4.6.5. Amenazas a la validez de la evaluacion

Cuatro factores acotan hasta donde pueden llevarse las conclusiones de este capitulo.

El primero es el ruido de alineacion del propio corpus, que contamina las referencias contra
las que se mide. La alineacion canonica versiculo a versiculo descrita en el apartado 4.2.3
supone que la numeracion de la edicion Inga de Wycliffe y la de la Reina-Valera de 1909
coinciden, y no siempre lo hacen. En la muestra de evaluacion hay al menos un caso claro: en
Juan 4:32, el texto espanol de referencia dice "Yo tengo una comida que comer, que vosotros no
sabeis", mientras que el texto Inga emparejado corresponde en realidad al contenido de Juan
3:32, sobre el testimonio de lo que se ha visto y oido. En ese ejemplo, cualquier sistema que
traduzca correctamente el espanol sera penalizado por las tres metricas, porque la referencia
no es la traduccion de la oracion fuente. El efecto empuja todas las cifras hacia abajo por
igual, de modo que no invalida la comparacion entre configuraciones, que es el objeto del
experimento, pero si obliga a leer los valores absolutos de BLEU como un limite inferior del
rendimiento real.

El segundo es el tamano y la composicion de la muestra. Cien ejemplos, de los cuales 99 son
versiculos biblicos, no permiten estimar el rendimiento fuera del registro religioso ni
calcular intervalos de confianza estrechos. El conjunto de prueba, con 565 ejemplos, sigue sin
utilizarse.

El tercero es la referencia unica. BLEU y chrF++ comparan contra una sola traduccion valida,
cuando en traduccion existen muchas. Este problema afecta a toda la traduccion automatica,
pero se agrava en lenguas sin norma ortografica estabilizada, donde una misma palabra admite
varias escrituras legitimas y el sistema es penalizado por elegir una distinta de la del
corpus.

El cuarto es la ausencia de juicio humano. Ninguna de las salidas fue evaluada por hablantes
de Inga. Los indicadores automaticos de variante que se introducen en el apartado 4.6.3
mitigan parcialmente esta carencia, porque detectan de forma objetiva cuando el sistema
escribe en otra lengua, pero no pueden pronunciarse sobre si una traduccion anclada al lexico
correcto es ademas aceptable, respetuosa con el registro y comprensible para un hablante. Esa
validacion queda como la pieza pendiente del trabajo y se recoge en las lineas futuras del
Capitulo 5.

[Fuente: datos/predicciones_val_completo.jsonl (Juan 4:32), datos/splits/test.jsonl]

---

## BLOQUE 9 -- Nueva subseccion 4.2.7 (cierra 4.2, tras "Material descartado") + Tabla 12

### 4.2.7. Perfil estadistico del corpus

El corpus final reune 5.641 pares, de los cuales 5.589 provienen del Nuevo Testamento y 52
de la Constitucion de 1991. Conviene mirar su composicion interna, porque de ella se derivan
varias decisiones tecnicas del resto del capitulo y tambien varias de sus limitaciones.

La distribucion por libro es marcadamente desigual, como muestra la Tabla 12. Los cuatro
evangelios y los Hechos de los Apostoles concentran 3.338 pares, casi el sesenta por ciento
del total, mientras que en el otro extremo hay libros que apenas contribuyen: 2 Juan y 3 Juan
aportan cinco pares cada uno. Esta asimetria tiene una consecuencia inmediata sobre el diseno
experimental. La particion estratificada por libro, que habria sido la opcion natural para
garantizar que las tres particiones cubrieran el mismo reparto tematico, resulta inviable
cuando existen clases con cinco elementos, porque una estratificacion 80/10/10 sobre cinco
pares no reparte nada. Por eso el Notebook 07 recurre a una particion aleatoria simple con
semilla 42, decision que se documenta aqui con su motivo y no como una preferencia
arbitraria.

Las longitudes de las dos caras del corpus son mas parecidas de lo que cabria esperar entre
una lengua aglutinante y una lengua flexiva. El texto Inga suma 119.174 palabras y el espanol
116.584, con medias de 21,13 y 20,67 palabras por par. La razon de longitud entre ambas caras
tiene mediana 0,93, es decir, la version Inga de un versiculo tipico es ligeramente mas corta
que la espanola, lo que concuerda con una morfologia que empaqueta en sufijos lo que el
espanol despliega en preposiciones y articulos. La media de esa misma razon, en cambio, es
1,07, y esa discrepancia entre media y mediana delata la existencia de una cola de pares donde
el Inga se alarga desproporcionadamente. El par mas extremo tiene 131 palabras en Inga frente
a un maximo de 63 en espanol. Esos casos suelen corresponder a versiculos donde la traduccion
Inga es mas parafrastica que literal, y son candidatos naturales a introducir ruido en el
entrenamiento.

El corpus es homogeneo en un sentido que conviene no perder de vista: los 5.641 pares
pertenecen al dialecto Alto Putumayo y proceden, salvo 52 excepciones, de un unico texto
religioso traducido por un unico equipo. Esa homogeneidad facilita el aprendizaje, porque el
registro y la ortografia son consistentes, y al mismo tiempo limita la generalizacion, porque
el sistema aprende a traducir el Inga de la Biblia de Wycliffe antes que el Inga que se habla
en el Putumayo.

TABLA 12 (nueva):

Tabla 12
Distribucion del corpus paralelo por libro (diez primeros) y fuente

| Libro o fuente | Pares | Porcentaje del corpus |
| Lucas | 794 | 14,1 |
| Hechos | 704 | 12,5 |
| Mateo | 697 | 12,4 |
| Juan | 635 | 11,3 |
| Marcos | 508 | 9,0 |
| Romanos | 346 | 6,1 |
| 1 Corintios | 304 | 5,4 |
| Apocalipsis | 249 | 4,4 |
| Hebreos | 226 | 4,0 |
| 2 Corintios | 180 | 3,2 |
| Resto del Nuevo Testamento (17 libros) | 946 | 16,8 |
| Constitucion de 1991 | 52 | 0,9 |
| Total | 5.641 | 100,0 |

Nota. Elaboracion propia a partir de datos/corpus_paralelo.jsonl. El corpus abarca 28 libros
del Nuevo Testamento. Los dos menos representados, 2 Juan y 3 Juan, aportan cinco pares cada
uno.

[Fuente: datos/corpus_paralelo.jsonl, notebooks/07_corpus_particiones.ipynb]

---

## BLOQUE 10 -- Parrafos que se ANADEN al final de 4.3 (antes de la nueva 4.3.1)

Dos decisiones de la indexacion merecen justificarse porque condicionan lo que el
recuperador puede encontrar. La primera es la dimensionalidad de los vectores. El modelo
gemini-embedding-001 produce por defecto embeddings de 3.072 dimensiones, y en este trabajo se
reducen a 768 mediante el parametro output_dimensionality. La reduccion responde a una razon
practica: cuatro indices que suman 14.529 registros ocupan en disco 127 MB con vectores de 768
dimensiones, y multiplicar por cuatro ese tamano no aportaria precision apreciable en una
busqueda sobre colecciones de este orden, donde el cuello de botella no es la capacidad de
representacion sino la calidad de lo indexado.

La segunda es la segmentacion de la gramatica. Los dos recursos gramaticales se trocean en
605 fragmentos, 560 procedentes de la gramatica pedagogica de Levinsohn y Mongui y 45 del
apendice morfosintactico. Ese troceo se hace por longitud y no por unidad de sentido, que es
la via rapida y tambien la mas imperfecta: una regla gramatical puede quedar separada de los
ejemplos que la ilustran, y el recuperador entregar entonces la mitad util de una explicacion.
El efecto de esta decision, agravado por el truncamiento posterior a 400 caracteres que se
describe en el apartado 4.5.3, se observa en las consultas de sondeo del apartado 4.3.1.

El acceso a la API de embeddings se realiza por lotes de 50 textos con una espera de 1,2
segundos entre lotes y hasta cinco reintentos con retroceso exponencial. Estos parametros no
tienen interes teorico, pero son los que hacen que la indexacion de 14.529 registros termine
sin errores de limite de tasa, y se consignan porque forman parte de lo que hay que reproducir
para obtener los mismos indices.

[Fuente: src/rag/embeddings.py, src/rag/indexes.py, outputs de
notebooks/08_indexacion_vectorial.ipynb, tamanos de lance_indexes/]

---

## BLOQUE 11 -- Parrafos que se ANADEN al final de 4.4.1 (tras la lectura de la curva)

Queda por justificar una decision que atraviesa todo el capitulo y que hasta aqui se ha dado
por supuesta: el uso del codigo de lengua quy_Latn, correspondiente al quechua de Ayacucho,
para representar al Inga dentro de NLLB-200. El Inga no figura entre las doscientas lenguas
del modelo, de modo que hay que asignarle alguna etiqueta existente, y quy_Latn es la mas
proxima tipologicamente entre las disponibles. La alternativa habria sido anadir un token de
lengua nuevo y entrenar su embedding desde cero, lo que con 4.512 pares no ofrece garantias.

La eleccion tiene una consecuencia que el apartado 4.6.3 cuantifica y que conviene anticipar
aqui. Al forzar la decodificacion en quy_Latn, el modelo sin adaptar no produce Inga
defectuoso: produce quechua de Ayacucho competente, con su ortografia y su morfologia propias,
en 98 de los 100 ejemplos evaluados. El codigo de lengua actua como un ancla fuerte, y esa
ancla apunta a la lengua equivocada. El ajuste fino LoRA es precisamente lo que reorienta esa
ancla hacia el Inga, y la Tabla 11 muestra que lo consigue: la configuracion B ancla 98 de sus
100 salidas al vocabulario Inga del entrenamiento. Visto asi, el valor del adaptador no esta
tanto en la mejora de BLEU, que es modesta, como en el cambio de lengua de salida, un efecto
que ninguna de las tres metricas del capitulo sabe registrar.

[Fuente: notebooks/10_medicion_nllb_configs.ipynb (forced_bos_token_id), src/models/nllb_lora.py,
src/eval/error_analysis.py]

---

## BLOQUE 12 -- REEMPLAZA el parrafo "El problema de la lengua incorrecta..." del analisis cualitativo

Motivo: el parrafo actual ilustra con salidas de la corrida de Sonnet 4.6 mientras el
capitulo reporta las metricas de Opus 4.7. Se reescribe citando la corrida principal.

El problema de la lengua incorrecta en la direccion espanol-Inga. Este es el hallazgo
cualitativo mas relevante del trabajo, y no se aprecia bien solo con las metricas. Cuando se
pide traducir del espanol al Inga, los sistemas que carecen de anclaje al Inga del Putumayo no
devuelven una traduccion mala: devuelven una traduccion a otra lengua quechua. La Tabla 10 lo
ilustra con Juan 4:32. La configuracion A produce "Jesustaq paykunata nirqan: Qankuna mana
reqsiq kanaykichispaq mikhuq kani, nispa", que es quechua sureno: las marcas -qa y -taq, el
sufijo -nispa y las consonantes glotalizadas de mikhuq delatan la variante de mayor presencia
en los datos de preentrenamiento de NLLB. La configuracion C, el mismo Opus 4.7 pero sin
contexto recuperado, produce "Y pai nirka: Nuka charini mikui mikungapa, mana kankuna
yachankichi", una forma hibrida que ya se acerca al Inga en el lexico pero conserva la grafia
con y de yachankichi, ajena al corpus. Solo con la recuperacion aumentada, en la configuracion
D, la salida se ancla del todo: "Paika nirkakunata: Nukaka kankuna mana iachaska sug mikuita
charini mikungapa", con la grafia iachaska en lugar de yachaska y la morfologia que aparece en
el corpus paralelo. El contexto recuperado no solo mejora el contenido: reorienta la salida
hacia la variante correcta de una familia linguistica con docenas de variantes mutuamente
ininteligibles.

## BLOQUE 13 -- REEMPLAZA el parrafo "El mismo efecto aparece en el articulo 10..."

El mismo efecto aparece en el articulo 10 de la Constitucion, "El castellano es el idioma
oficial de Colombia". La configuracion A devuelve "Kastillanuqa Colombia suyupi rimaymi", de
nuevo quechua sureno (suyu por territorio, el enclitico -qa). Las configuraciones con
recuperacion producen en cambio formas ancladas al material Inga indexado: Opus 4.7 devuelve
"Lanku simi rimaimi ka Kulumbia Llagtapa idioma" y Sonnet 4.6 "Kastilla simi kami Kulumbia
llagtapi kawsag tukui runakunapata rimai", ambas con llagta y la grafia Kulumbia propias del
corpus, aunque la primera recurre al prestamo idioma en lugar de traducirlo. Que el ejemplo
provenga del corpus juridico, y no del Nuevo Testamento, sugiere que el anclaje por
recuperacion funciona tambien fuera del dominio biblico que domina el corpus.

Conviene advertir, no obstante, que este ejemplo concreto arrastra un problema de la propia
referencia. El texto Inga emparejado con el articulo 10 en el corpus no traduce la frase sobre
el castellano, sino la que reconoce las lenguas de los pueblos indigenas, y varias
configuraciones interpretaron la raiz iura como arbol y produjeron traducciones sobre el
idioma de los arboles. El caso ilustra a la vez un limite del sistema y un limite del corpus;
esto ultimo se retoma en el apartado 4.6.5.

## BLOQUE 14 -- CORRECCIONES DE CIFRAS (sustituciones puntuales)

1. Tabla 6 (splits por dialecto): Train 4.471 -> 4.512, Val 558 -> 564, Test 560 -> 565,
   Total 5.589 -> 5.641 (columnas AP y Total). Fuente: datos/splits/*.jsonl.
2. Seccion 4.3: "El indice de ejemplos indexa los 4.471 pares" -> "los 4.512 pares".
3. Seccion 4.4: "aproximadamente 1,18 millones de parametros entrenables, equivalentes al
   0,19 %" -> "2,36 millones de parametros entrenables, equivalentes al 0,38 %".
   Fuente: adapter_model.safetensors, 2.359.296 parametros contados (72 modulos LoRA de
   32.768 parametros cada uno: 24 en la autoatencion del codificador, 24 en la del
   descodificador y 24 en la atencion cruzada).
4. Capitulo 5, conclusion primera: "el corpus paralelo Inga-Espanol alcanzo 5.589 pares"
   -> "5.641 pares" (5.589 del Nuevo Testamento mas 52 de la Constitucion), para que
   concuerde con el resumen y con datos/corpus_paralelo.jsonl.

NOTA: la afirmacion de los "47 minutos" de entrenamiento que figuraba en versiones previas
NO esta presente en el docx del deposito. El dato real (26,8 minutos) se introduce por
primera vez en el Bloque 2.

