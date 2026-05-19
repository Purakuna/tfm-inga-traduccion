"""Genera entrega2/figuras/fig10_arquitectura_rag.png.

Diagrama de la arquitectura RAG multi-indice implementada en Entrega 2:
- 4 indices LanceDB (lexico, gramatical, ejemplos, ejemplos_es)
- Embeddings Gemini text-embedding-001 (768 dims)
- Retriever uniforme
- Conmutador por direccion (inga2es / es2inga)
- Prompt builder
- LLM Claude Sonnet 4.6
"""
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "entrega2" / "figuras" / "fig10_arquitectura_rag.png"

fig, ax = plt.subplots(figsize=(13, 7.5))
ax.set_xlim(0, 14)
ax.set_ylim(0, 9)
ax.axis("off")


def caja(x, y, w, h, label, color="#dbeafe", border="#1e40af", fontsize=9, weight="bold"):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.15",
        linewidth=1.3,
        edgecolor=border,
        facecolor=color,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, weight=weight, color="#0f172a")


def flecha(x1, y1, x2, y2, color="#475569"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="->", mutation_scale=14, linewidth=1.2, color=color,
    ))


# Capa 1: Fuentes (verde claro)
caja(0.3, 7.3, 2.5, 1.0, "Diccionario\nInga\n(4.900 entradas)", color="#dcfce7", border="#15803d", fontsize=8)
caja(3.1, 7.3, 2.5, 1.0, "Gramatica +\nRosetta\n(605 chunks)", color="#dcfce7", border="#15803d", fontsize=8)
caja(5.9, 7.3, 2.5, 1.0, "Train pairs\n(Inga side)\n(4.471 pares)", color="#dcfce7", border="#15803d", fontsize=8)
caja(8.7, 7.3, 2.5, 1.0, "Train pairs\n(Spanish side)\n(4.471 pares)", color="#dcfce7", border="#15803d", fontsize=8)

# Capa 2: Embedder
caja(4.5, 5.7, 5.0, 0.9, "gemini-embedding-001\n(output_dimensionality = 768)",
     color="#fef3c7", border="#b45309", fontsize=9)

for x in [1.55, 4.35, 7.15, 9.95]:
    flecha(x, 7.3, x, 6.6)
flecha(1.55, 5.7, 4.5, 5.7, color="#94a3b8")
flecha(9.95, 5.7, 9.5, 5.7, color="#94a3b8")

# Capa 3: Indices LanceDB
caja(0.3, 4.0, 2.5, 1.0, "INDICE\nlexico\n(LanceDB)", color="#dbeafe", border="#1e40af", fontsize=8)
caja(3.1, 4.0, 2.5, 1.0, "INDICE\ngramatical\n(LanceDB)", color="#dbeafe", border="#1e40af", fontsize=8)
caja(5.9, 4.0, 2.5, 1.0, "INDICE\nejemplos\n(LanceDB)", color="#dbeafe", border="#1e40af", fontsize=8)
caja(8.7, 4.0, 2.5, 1.0, "INDICE\nejemplos_es\n(LanceDB)", color="#dbeafe", border="#1e40af", fontsize=8)

for x in [1.55, 4.35, 7.15, 9.95]:
    flecha(x, 5.7, x, 5.0)

# Capa 4: Retriever uniforme
caja(2.0, 2.5, 7.5, 0.9, "Retriever multi-indice (top-k=5 por indice)\nconmutador por direccion: inga2es -> ejemplos | es2inga -> ejemplos_es",
     color="#fce7f3", border="#9d174d", fontsize=9)

flecha(1.55, 4.0, 2.5, 3.4)
flecha(4.35, 4.0, 4.0, 3.4)
flecha(7.15, 4.0, 6.5, 3.4)
flecha(9.95, 4.0, 8.5, 3.4)

# Capa 5: Prompt builder
caja(3.5, 1.2, 4.5, 0.7, "Prompt builder estructurado\n(system + lexico + gramatical + ejemplos few-shot)",
     color="#e0e7ff", border="#4338ca", fontsize=8.5)

flecha(5.75, 2.5, 5.75, 1.9)

# Capa 6: LLM
caja(3.5, 0.05, 4.5, 0.8, "Claude Sonnet 4.6 (Anthropic API)",
     color="#fee2e2", border="#991b1b", fontsize=10, weight="bold")

flecha(5.75, 1.2, 5.75, 0.85)

# Query box (derecha)
caja(11.5, 5.7, 2.3, 1.5, "Oracion\na traducir\n(Inga o Espanol)",
     color="#f1f5f9", border="#0f172a", fontsize=8)
flecha(11.5, 6.45, 9.5, 6.15, color="#0ea5e9")  # to embedder
flecha(11.5, 5.95, 9.5, 2.95, color="#0ea5e9")  # to retriever

# Output box (abajo derecha)
caja(11.0, 0.2, 2.8, 0.6, "Traduccion al\nidioma destino",
     color="#fae8ff", border="#86198f", fontsize=8.5)
flecha(8.0, 0.45, 11.0, 0.45, color="#86198f")

# Leyendas
ax.text(7, 8.7, "Arquitectura del sistema RAG multi-indice (Entrega 2)",
        ha="center", va="center", fontsize=12, weight="bold", color="#0f172a")
ax.text(7, 8.4, "fuentes primarias -> embeddings -> indices vectoriales -> retriever -> prompt -> LLM",
        ha="center", va="center", fontsize=9, style="italic", color="#475569")

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Figura escrita: {OUT}")
