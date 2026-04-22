# Propuesta de Trabajo Final de Máster

## Título provisional

**Desarrollo de un sistema de traducción automática Inga-Español mediante adaptación de modelos de lenguaje con recuperación aumentada de información para la preservación digital de la lengua Inga del Putumayo, Colombia**

---

## Descripción y justificación

La lengua Inga, perteneciente a la familia lingüística quechua, es hablada por aproximadamente 18.000 personas del pueblo Inga, asentado principalmente en el departamento del Putumayo, en el suroccidente de Colombia. A pesar de ser una lengua viva y de uso cotidiano en comunidades como las de Mocoa, Santiago, Colón y San Andrés, el Inga enfrenta un proceso progresivo de desplazamiento lingüístico provocado por la presión del español como lengua dominante en los ámbitos educativo, institucional y digital. Este fenómeno pone en riesgo no solo un sistema de comunicación, sino toda una cosmovisión, un sistema de conocimiento ancestral y una identidad cultural que se transmite a través de la palabra.

Actualmente no existen herramientas tecnológicas de traducción automática que contemplen la lengua Inga. Los grandes traductores comerciales como Google Translate o DeepL no la incluyen en su catálogo. Google Translate incorporó Quechua sureño en mayo de 2022, pero la variante Inga del Putumayo permanece excluida. Los escasos recursos digitales disponibles se limitan al Diccionario Inga del Valle de Sibundoy (Levinsohn, Maffla y Tandioy, 1978/1997), materiales pedagógicos del SIL International y los recursos del programa Inga Rimangapa Samuichi de la Universidad de Indiana, todos con difusión restringida y sin integración computacional. Esta ausencia tecnológica profundiza la brecha entre las lenguas hegemónicas y las lenguas indígenas, negándole al Inga un espacio en el ecosistema digital contemporáneo.

El presente trabajo propone el desarrollo de un sistema de traducción automática Inga-Español que combina dos aproximaciones complementarias: por un lado, la adaptación de un modelo de traducción automática de código abierto especializado (NLLB-200 de Meta, que ya incluye Quechua Ayacucho en sus 200 lenguas) mediante ajuste fino eficiente con LoRA; por otro lado, el uso de un modelo de lenguaje de frontera (Claude Opus 4.5 de Anthropic) potenciado con generación aumentada por recuperación (RAG) que inyecta conocimiento lingüístico específico del Inga en el proceso de traducción.

La propuesta se sustenta en tres antecedentes recientes. Primero, el proyecto QueEn (Llerena et al., 2024) demostró que la combinación de RAG y LoRA permite adaptar modelos de gran escala para la traducción Quechua-Inglés, alcanzando mejoras de BLEU de 1.5 a 17.6 puntos. Segundo, el trabajo de Prieto et al. (2024) de la Universidad de Los Andes creó los primeros corpus paralelos para lenguas indígenas colombianas incluyendo el Inga, aplicando transfer learning desde NLLB-200 con resultados prometedores. Tercero, la investigación de Enis y Hopkins (2024) demostró que Claude exhibe una "eficiencia de recursos" única entre los LLMs: su calidad de traducción se degrada menos que otros modelos al pasar de lenguas de altos recursos a lenguas de bajos recursos, lo que lo convierte en un candidato particularmente adecuado para este tipo de tarea.

Dado que el Inga es una variante de la familia quechua, existe una base lingüística compartida con el Quechua sureño que hace viable la transferencia de conocimiento desde modelos que ya incorporan esa lengua, adaptándolos a las particularidades fonológicas, morfológicas y sintácticas propias del Inga del Putumayo.

Este trabajo nace desde dentro de la comunidad. Uno de los integrantes del equipo es indígena Inga, hablante de la lengua y residente en Mocoa, Putumayo, lo que garantiza no solo el acceso directo a hablantes nativos para la construcción y validación del corpus, sino también una comprensión profunda del contexto cultural en el que la lengua opera. La traducción automática de una lengua indígena no puede construirse únicamente desde la ingeniería; requiere sensibilidad cultural, conocimiento situado y participación comunitaria. Este proyecto reúne esas condiciones.

---

## Objetivos e impacto esperado

### Objetivo general

Desarrollar y evaluar un sistema de traducción automática Inga-Español que combine la adaptación de modelos de traducción de código abierto con el uso de modelos de lenguaje de frontera potenciados por recuperación de información lingüística, contribuyendo a la preservación digital y la visibilización de la lengua Inga del Putumayo.

### Objetivos específicos

1. Construir un corpus paralelo Inga-Español a partir de fuentes orales, textuales y comunitarias del pueblo Inga del Putumayo, complementado con recursos existentes de lenguas quechuas emparentadas, garantizando la representatividad dialectal y el consentimiento informado de los hablantes participantes.

2. Diseñar e implementar una base de conocimiento lingüístico del Inga (diccionario bilingüe estructurado, reglas gramaticales y pares de traducción ejemplares) indexada mediante técnicas de recuperación híbrida (búsqueda exacta + similitud semántica por embeddings) con índices separados por tipo de conocimiento para su uso como componente RAG del sistema.

3. Adaptar el modelo de traducción NLLB-200 de Meta mediante ajuste fino con LoRA, aprovechando el conocimiento de Quechua Ayacucho (`quy_Latn`) ya presente en el modelo como base para la transferencia al par lingüístico Inga-Español. Explorar adicionalmente MADLAD-400 y TranslateGemma como modelos alternativos.

4. Implementar un pipeline de traducción basado en Claude Opus 4.5 (Anthropic) con RAG, diseñando estrategias de prompt estructurado que inyecten conocimiento lingüístico del Inga sin saturar el contexto del modelo, y evaluar su rendimiento comparativo frente al modelo local ajustado.

5. Evaluar el rendimiento de ambas aproximaciones mediante métricas automáticas (BLEU, chrF++, BERTScore) y validación cualitativa con hablantes nativos de la lengua Inga, incluyendo criterios de adecuación semántica, fluidez gramatical y naturalidad cultural.

6. Documentar el proceso completo como un marco metodológico replicable para otras lenguas indígenas de Colombia y América Latina en situación de vulnerabilidad, y liberar los recursos construidos (corpus, diccionario digital, base de conocimiento) como bienes comunes para la comunidad Inga y la comunidad académica.

### Impacto esperado

**En lo social y cultural**, este trabajo busca devolver a la lengua Inga una presencia en el mundo digital que históricamente le ha sido negada. Un traductor funcional permitiría a hablantes Inga comunicarse con instituciones, acceder a información en español y producir contenido en su propia lengua con apoyo tecnológico. Además, generaría una herramienta concreta para maestros bilingües, gestores culturales y organizaciones indígenas como el Colectivo Runapacha que trabajan en la revitalización lingüística en el Putumayo. En un contexto donde la educación intercultural bilingüe es un derecho reconocido por la Constitución Colombiana de 1991 pero carente de herramientas digitales, este proyecto contribuye a cerrar esa brecha.

**En lo académico**, el proyecto aporta evidencia sobre la viabilidad de adaptar modelos de lenguaje a lenguas de muy bajos recursos que no cuentan con presencia en los datos de entrenamiento. La comparación directa entre un modelo de traducción especializado con fine-tuning (NLLB-200 + LoRA) y un modelo de frontera con RAG (Claude Opus 4.5) constituye un aporte original al campo, pues permite entender cuál aproximación es más efectiva cuando los datos son extremadamente escasos. Este diseño experimental dual va más allá del trabajo de Prieto et al. (2024) y del proyecto QueEn, que evaluaron cada estrategia por separado.

**En lo comunitario**, el corpus construido, el diccionario digital estructurado y la base de conocimiento gramatical quedarán como recursos abiertos para la comunidad Inga y para investigadores interesados en la lengua. El proyecto no extrae conocimiento de la comunidad: lo sistematiza y lo devuelve en forma de herramienta útil. Toda la participación comunitaria se realizará bajo protocolos de consentimiento informado y respeto a la consulta previa, principios irrenunciables del pueblo Inga.

---

## Metodología, tecnologías y técnicas

### Enfoque metodológico

El proyecto sigue una metodología de investigación aplicada con enfoque experimental comparativo, organizada en cinco fases. La estrategia central consiste en desarrollar dos sistemas de traducción en paralelo — uno basado en fine-tuning de un modelo de código abierto y otro basado en un LLM de frontera con RAG — y evaluar rigurosamente cuál produce mejores traducciones para una lengua de recursos extremadamente limitados.

### Fase 1: Construcción del corpus paralelo Inga-Español

Se recopilará un corpus de oraciones alineadas Inga-Español mediante las siguientes fuentes:

- **Corpus existente de la Universidad de Los Andes** (Prieto et al., 2024): Primer corpus paralelo documentado que incluye Inga, construido a partir de la Biblia, la Constitución Colombiana, cuentos y diccionarios. Se buscará acceso directo a este recurso contactando al equipo investigador.
- **Diccionario Inga del Valle de Sibundoy** (Levinsohn, Maffla y Tandioy, 1978/1997, SIL International): Digitalización y estructuración de entradas léxicas con sus variantes morfológicas.
- **Materiales educativos bilingües** del pueblo Inga: Cartillas, materiales del Ministerio de Cultura y de programas de educación intercultural bilingüe en Putumayo.
- **Sesiones de elicitación lingüística** con hablantes nativos en Mocoa y comunidades aledañas, realizadas con consentimiento informado y respetando los protocolos de consulta previa del pueblo Inga.
- **Textos narrativos orales** transcritos y traducidos al español por hablantes bilingües.
- **Corpus quechuas emparentados** para transferencia: JW300 (variantes quy, quz, que), el corpus somosnlp spanish-to-quechua (128K pares Español-Quechua Ayacucho de HuggingFace) y el corpus monolingüe Llamacha/monolingual-quechua-iic (175K oraciones).
- **Datos sintéticos**: Generación de pares paralelos adicionales mediante back-translation y augmentación con modelos LLM, siguiendo la metodología documentada en trabajos recientes de AmericasNLP 2025.

Se establece como meta mínima la construcción de un corpus de 5.000 pares de oraciones alineadas Inga-Español, con una meta deseable de 10.000 pares. El corpus será limpiado, normalizado ortográficamente y segmentado en conjuntos de entrenamiento (80%), validación (10%) y prueba (10%).

### Fase 2: Construcción de la base de conocimiento para RAG

Se estructurará una base de conocimiento lingüístico compuesta por tres índices independientes:

- **Índice léxico (Diccionario bilingüe Inga-Español)**: Entradas léxicas con sus variantes morfológicas, organizadas como fragmentos atómicos indexables. Se consultará mediante las palabras individuales de la oración a traducir.
- **Índice gramatical (Guía gramatical del Inga)**: Reglas de sufijación (el Inga es aglutinante), orden sintáctico SOV, marcadores de tiempo, persona y número, fragmentadas en unidades independientes. Se consultará mediante patrones morfológicos detectados en la oración fuente.
- **Índice de ejemplos (Pares de traducción)**: Oraciones traducidas que sirvan como ejemplos few-shot, indexadas por similitud semántica con la oración completa a traducir.

La separación en índices evita contaminación cruzada: una búsqueda de un término del diccionario no traerá reglas gramaticales irrelevantes y viceversa.

**Estrategia de control de contexto** (para evitar saturación del prompt):
- Top-k bajo (3-5 fragmentos máximo) con umbral de similitud coseno mínimo de 0.75.
- Presupuesto fijo de tokens para material RAG (máximo 500 tokens).
- Prompt estructurado con separación explícita entre material de referencia y tarea de traducción.
- Instrucción explícita al modelo de ignorar material no relevante.
- Reranking post-retrieval con cross-encoder para filtrar los fragmentos más pertinentes antes de inyectar.

**Tecnologías previstas:**
- FAISS o ChromaDB como base de datos vectorial.
- Modelo de embeddings multilingüe `paraphrase-multilingual-MiniLM-L12-v2` para indexación semántica.
- LlamaIndex como framework de orquestación RAG.

### Fase 3: Adaptación del modelo de traducción local (Fine-tuning)

Se trabajará con hardware local (Apple M4 Max, 128 GB de memoria unificada), lo que permite ejecutar modelos de hasta 40B de parámetros en precisión completa o hasta 70B cuantizados, eliminando la dependencia de plataformas cloud.

**Modelo base principal: `facebook/nllb-200-3.3B`** (No Language Left Behind)
- Modelo encoder-decoder diseñado específicamente para traducción de 200 idiomas.
- Incluye Quechua Ayacucho (`quy_Latn`) en sus datos de entrenamiento, proporcionando la base de transferencia más directa hacia el Inga.
- Arquitectura dominante en las competiciones AmericasNLP (2021-2025) para traducción de lenguas indígenas americanas.
- Con 128 GB de RAM, se puede ejecutar y ajustar sin restricciones de memoria.

**Modelos alternativos para comparación:**
- **`google/madlad400-10b-mt`** (10.7B parámetros): Modelo de traducción basado en T5 con cobertura de 450+ lenguas incluyendo Quechua (`qu`), con cobertura dialectal más amplia que NLLB. Licencia Apache 2.0.
- **`google/translategemma-12b-it`** (12B parámetros): Modelo de traducción basado en Gemma 3, publicado en enero de 2026, diseñado explícitamente como base fine-tuneable para investigadores que deseen extenderlo a nuevas lenguas de bajos recursos.

**Técnica de ajuste fino:** LoRA (Low-Rank Adaptation) a través de la librería PEFT de HuggingFace, que permite ajustar un subconjunto reducido de parámetros del modelo (matrices de proyección query y value en las capas de atención del Transformer). Con 128 GB de memoria unificada en la M4 Max, es viable incluso el fine-tuning completo del modelo NLLB-200-3.3B, aunque LoRA se utilizará para experimentación rápida y ablation studies.

**Augmentación de datos:** Se aplicarán técnicas de back-translation y generación sintética de pares paralelos, siguiendo la metodología de Ortega et al. (2025) que demostró mejoras consistentes en chrF++ para Quechua, Aymara y Guaraní mediante datos sintéticos generados por NLLB.

**Tecnologías previstas:**
- HuggingFace Transformers + PEFT (LoRA/QLoRA).
- PyTorch con soporte Metal Performance Shaders (MPS) para Apple Silicon.
- MLX (framework de Apple) como alternativa nativa para M4 Max.
- Weights & Biases para tracking de experimentos.

### Fase 4: Pipeline de traducción con Claude Opus 4.5 + RAG

Como segunda línea experimental, se implementará un sistema de traducción basado en Claude Opus 4.5 de Anthropic, el modelo de lenguaje de frontera más potente disponible por API.

**Justificación de la elección de Claude:**
- Investigación publicada (Enis y Hopkins, 2024, arXiv:2404.13813) demostró que Claude exhibe "resource efficiency" en traducción: su calidad se degrada significativamente menos que otros LLMs y que sistemas NMT especializados al pasar de lenguas de altos a bajos recursos.
- Claude opera al 98.2% del nivel de inglés en tareas en español, la lengua meta del sistema.
- Ventana de contexto de 200K tokens, suficiente para inyectar diccionario, gramática y ejemplos sin comprometer la generación.
- Ganador en 9 de 11 pares de idiomas en la competencia de traducción WMT24.

**Diseño del pipeline:**
1. Recepción de oración en Inga.
2. Consulta a los tres índices RAG (léxico, gramatical, ejemplos) con la estrategia de control de contexto descrita en la Fase 2.
3. Construcción de prompt estructurado con secciones explícitas: instrucción del sistema, material de referencia (separado por tipo), ejemplos few-shot, y tarea de traducción.
4. Llamada a la API de Claude Opus 4.5 con el prompt enriquecido.
5. Post-procesamiento y registro de la traducción.

**Optimización de costos:** Se utilizará la API Batch de Anthropic (50% de descuento) para evaluaciones masivas, y prompt caching para el material RAG estable (90% de ahorro en contexto repetido).

**Tecnologías previstas:**
- SDK de Anthropic para Python.
- LlamaIndex para la orquestación RAG (mismo pipeline que el modelo local).
- Presupuesto estimado de API para experimentación y evaluación completa.

### Fase 5: Evaluación comparativa

La evaluación se realizará en dos dimensiones, comparando al menos seis configuraciones:

| Configuración | Modelo | Técnica |
|---------------|--------|---------|
| A | NLLB-200-3.3B | Sin adaptación (zero-shot con código `quy_Latn`) |
| B | NLLB-200-3.3B | Fine-tuning con LoRA sobre corpus Inga-Español |
| C | MADLAD-400-10B o TranslateGemma-12B | Fine-tuning con LoRA |
| D | Claude Opus 4.5 | Sin RAG (zero-shot) |
| E | Claude Opus 4.5 | Con RAG (diccionario + gramática + ejemplos) |
| F | NLLB-200-3.3B + LoRA | Con RAG en inferencia |

**Evaluación automática:**
- **BLEU** (Bilingual Evaluation Understudy): Precisión de n-gramas respecto a la traducción de referencia.
- **chrF++**: Métrica basada en caracteres, recomendada por AmericasNLP como más adecuada para lenguas aglutinantes como el Inga.
- **BERTScore**: Similitud semántica basada en embeddings contextuales.

**Evaluación humana:**
Se realizarán sesiones de validación con hablantes nativos Inga que evaluarán una muestra representativa de traducciones en tres dimensiones: adecuación semántica (¿la traducción dice lo mismo?), fluidez gramatical (¿suena natural?) y naturalidad cultural (¿respeta el modo de expresión Inga?). Esta evaluación es fundamental porque las métricas automáticas fueron diseñadas para lenguas con abundantes recursos y pueden no capturar las particularidades del Inga, especialmente en lo relativo a expresiones culturales que no tienen equivalente directo en español.

**Evaluación contra trabajos previos:**
Se compararán los resultados con los reportados por Prieto et al. (2024) para Inga en su estudio con NLLB y con los benchmarks de FLORES-200 para Quechua Ayacucho, estableciendo una línea base de referencia que permita medir el aporte real del proyecto.

### Distribución del equipo

El equipo de trabajo está conformado por tres personas con perfiles complementarios:

- **Integrante en Mocoa (Putumayo)**: Hablante nativo Inga, responsable de la construcción del corpus, el contacto comunitario, la validación lingüística con hablantes nativos y la evaluación humana de las traducciones.
- **Integrante en Cali**: Responsable del diseño e implementación del pipeline de RAG, la base de conocimiento vectorial, la integración con la API de Claude y la orquestación del sistema completo.
- **Integrante en Cúcuta**: Responsable del ajuste fino de los modelos locales con LoRA, la experimentación con modelos alternativos, la augmentación de datos y la evaluación cuantitativa.

La coordinación se realizará de forma remota con herramientas colaborativas, y el código y datos del proyecto se gestionarán en un repositorio compartido con control de versiones.

### Infraestructura de cómputo

| Recurso | Especificación | Uso |
|---------|---------------|-----|
| Apple M4 Max, 128 GB RAM | Ejecución local | Fine-tuning NLLB-200-3.3B, MADLAD-400-10B, TranslateGemma-12B. Inferencia de todos los modelos locales. |
| API Anthropic (Claude Opus 4.5) | Acceso por API | Pipeline RAG + traducción. Evaluación comparativa. |
| FAISS / ChromaDB | Local | Indexación y recuperación de la base de conocimiento lingüístico. |

---

### Referencias

- Llerena, N. et al. (2024). *QueEn: Translation Model for Low-Resource Quechua-English*. arXiv:2412.05184v1.
- Prieto, J.C. et al. (2024). *Translation systems for low-resource Colombian Indigenous languages, a first step towards cultural preservation*. AmericasNLP 2024, NAACL. ACL Anthology.
- Prieto, J.C. et al. (2025). *Machine Translation Strategies for Low-Resource Colombian Indigenous Languages*. Springer.
- Enis, M. y Hopkins, M. (2024). *From LLM to NMT: Advancing Low-Resource Machine Translation with Claude*. arXiv:2404.13813.
- Costa-jussà, M. et al. (2022). *No Language Left Behind: Scaling Human-Centered Machine Translation*. Meta AI. Nature, 2024.
- Hu, E. et al. (2021). *LoRA: Low-Rank Adaptation of Large Language Models*. arXiv:2106.09685.
- Lewis, P. et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*. NeurIPS 2020.
- Ortega, J. et al. (2025). *Improving Indigenous Language Machine Translation with Synthetic Data*. arXiv:2601.03135.
- Ebrahimi, A. et al. (2024). *Findings of the AmericasNLP 2024 Shared Task on Machine Translation*. NAACL 2024. ACL Anthology.
- Tonja, A. et al. (2024). *NLP Progress in Indigenous Latin American Languages*. arXiv:2404.05365. NAACL 2024.
- Jara-Roa, D. et al. (2026). *TranslateGemma: Technical Report*. arXiv:2601.09012. Google.
- Kudugunta, S. et al. (2023). *MADLAD-400: A Multilingual And Document-Level Large Audited Dataset*. Google.
- Levinsohn, S.H., Maffla, A. y Tandioy, D. (1978/1997). *Diccionario Inga del Valle de Sibundoy*. SIL International.
- Tandioy Jansasoy, F. *Inga Rimangapa Samuichi: Speaking the Quechua of Colombia*. Indiana University.
- Diagne, A. et al. (2025). *The Serendipity of Claude AI: Case of the 13 Low-Resource National Languages of Mali*. arXiv:2503.03380.
