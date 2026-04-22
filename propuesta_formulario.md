# Propuesta TFM - Campos del formulario

---

## Título provisional

Traducción automática Inga-Español mediante adaptación de modelos de lenguaje con RAG para la preservación digital de una lengua indígena colombiana

---

## Descripción y justificación del trabajo a desarrollar

La lengua Inga, de la familia quechua, es hablada por 18.000 personas en el Putumayo, Colombia. Actualmente no existe ningún traductor automático que la contemple: Google Translate y DeepL la excluyen, y los recursos digitales disponibles son escasos y sin integración computacional. Esta ausencia tecnológica profundiza la brecha digital de las lenguas indígenas.

Este trabajo propone desarrollar un sistema de traducción Inga-Español combinando dos enfoques: (1) adaptación del modelo NLLB-200 de Meta mediante fine-tuning con LoRA, aprovechando que ya incluye Quechua Ayacucho como base de transferencia; y (2) uso de Claude Opus 4.5 con RAG (Retrieval-Augmented Generation) para inyectar conocimiento lingüístico del Inga en el proceso de traducción.

El proyecto nace desde dentro de la comunidad: uno de los integrantes es indígena Inga, hablante nativo y residente en Mocoa, lo que garantiza acceso directo a hablantes para construcción y validación del corpus, además de comprensión del contexto cultural.

---

## Objetivos e impacto que se espera conseguir con el desarrollo del trabajo

**Objetivo general:** Desarrollar y evaluar un sistema de traducción Inga-Español que combine modelos de código abierto con fine-tuning y modelos de frontera con RAG, contribuyendo a la preservación digital de la lengua Inga.

**Objetivos específicos:**
1. Construir un corpus paralelo Inga-Español (meta: 5.000-10.000 pares) con participación comunitaria.
2. Implementar una base de conocimiento lingüístico (diccionario, gramática, ejemplos) indexada para RAG.
3. Adaptar NLLB-200 mediante LoRA y comparar con MADLAD-400 y TranslateGemma.
4. Implementar pipeline de traducción con Claude Opus 4.5 + RAG.
5. Evaluar con métricas automáticas (BLEU, chrF++, BERTScore) y validación con hablantes nativos.

**Impacto esperado:**
- Social: Herramienta para maestros bilingües, gestores culturales y organizaciones indígenas del Putumayo.
- Académico: Evidencia comparativa sobre fine-tuning vs. RAG para lenguas de muy bajos recursos.
- Comunitario: Corpus y recursos digitales liberados como bienes comunes para la comunidad Inga.

---

## Metodología, tecnologías o técnicas previstas para abordar el desarrollo del trabajo

**Metodología:** Investigación aplicada con enfoque experimental comparativo en cinco fases: (1) construcción del corpus paralelo, (2) base de conocimiento para RAG, (3) fine-tuning de modelos locales, (4) pipeline Claude + RAG, (5) evaluación comparativa.

**Modelos:**
- Local principal: NLLB-200-3.3B (Meta) — ya contiene Quechua, dominante en AmericasNLP 2021-2025.
- Alternativos: MADLAD-400-10B, TranslateGemma-12B.
- API: Claude Opus 4.5 (Anthropic) — demostrada eficiencia en lenguas de bajos recursos.

**Técnicas:**
- Fine-tuning con LoRA/QLoRA (PEFT de HuggingFace).
- RAG con índices separados (léxico, gramatical, ejemplos) usando FAISS/ChromaDB y LlamaIndex.
- Augmentación de datos con back-translation y generación sintética.

**Infraestructura:**
- Hardware local: Apple M4 Max, 128 GB RAM (modelos hasta 40B en precisión completa).
- API: Anthropic Claude Opus 4.5.

**Equipo:** Tres integrantes (Mocoa: corpus y validación comunitaria; Cali: RAG y orquestación; Cúcuta: fine-tuning y evaluación).
