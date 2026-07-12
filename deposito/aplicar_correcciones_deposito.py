#!/usr/bin/env python3
"""
Aplica las correcciones del revisor (Comentarios Entrega 3 G16) sobre el docx
del deposito, operando sobre el XML interno. Cada transformacion valida sus
precondiciones y aborta en voz alta si la estructura del documento cambio.

Bloques de correccion:
  A. Numeracion de titulos: los capitulos 1-3 pasan de numeracion automatica
     del estilo a numero literal en el texto con numId=0 (mismo esquema que ya
     usan los capitulos 4-5). Formato homogeneo "N. ", "N.N. ", "N.N.N. ".
     De paso: Cronograma deja de duplicar el 3.3.2 (pasa a 3.3.3) y corren
     Infraestructura (3.3.4) y Configuraciones (3.3.5).
  B. Titulos literales del cap 4-5 sin punto final: "4.1 " -> "4.1. ", etc.
  C. Titulo del capitulo 4 estaba como Heading3: pasa a Heading1.
  D. Anexo A: el estilo Anexo trae numeracion propia "Anexo A." y el texto ya
     dice "Anexo A. ..." (por eso el TOC mostraba "Anexo A.Anexo A."). Se
     desactiva la numeracion del parrafo (numId=0) y queda solo el literal.
  E. "para Quechua" -> "para quechua" (RAE) en el titulo 2.2.3 y el TOC cacheado.
  F. Captions en dos lineas (APA/UNIR): cada pie "Tabla N Titulo" se parte en
     un parrafo identificador "Tabla N" (estilo Caption, negrita) y un parrafo
     de titulo en cursiva (estilo nuevo TituloFiguraTabla). Se inserta un campo
     TC oculto con "Etiqueta N. Titulo" para que los indices de figuras/tablas
     conserven numero + titulo + pagina al regenerarse.
  G. Los dos indices (figuras/tablas) pasan de TOC \\c a TOC \\f (F figuras,
     T tablas) para leer los campos TC.
  H. Notas con todo el texto en cursiva: solo "Nota." queda en cursiva.
  I. Invitaciones en el texto para Figura 8, Tabla 6, Figura 9 y Figura 11; y
     se corrige la referencia cruzada del cronograma (decia Figura 8, es la 7).

Tras ejecutar: abrir en Word y actualizar todos los campos (Cmd+A, F9) para
regenerar los tres indices.
"""
import re, shutil, sys, zipfile
from pathlib import Path

DEPOSITO = Path(__file__).parent
DOCX = DEPOSITO / "TFM_Deposito_EslavaSantos.docx"
BASE = DEPOSITO / "_base_vFINAL_original.docx"
WORK = Path("/private/tmp/claude-501/-Users-william-santos-Documents-UNIR-tfm-entrega3/f06ae7c6-dd02-4339-b690-529f0b580aa7/scratchpad/build_dep")

NUMPR_OFF = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'

def die(msg):
    sys.exit(f"ABORT: {msg}")

def ptext(p):
    return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p))

def pstyle(p):
    m = re.search(r'<w:pStyle w:val="([^"]+)"', p)
    return m.group(1) if m else ''

class Doc:
    def __init__(self, xml):
        self.xml = xml

    def paras(self):
        return re.findall(r'<w:p [^>]*>.*?</w:p>|<w:p>.*?</w:p>', self.xml, re.S)

    def find_para(self, text, style=None, startswith=False):
        hits = []
        for p in self.paras():
            t = ptext(p)
            ok = t.startswith(text) if startswith else (t == text)
            if ok and (style is None or pstyle(p) == style):
                hits.append(p)
        if len(hits) != 1:
            die(f"esperaba 1 parrafo text={text!r} style={style}, hay {len(hits)}")
        return hits[0]

    def replace_para(self, old, new, label):
        if self.xml.count(old) != 1:
            die(f"[{label}] el parrafo objetivo no es unico en el XML")
        self.xml = self.xml.replace(old, new, 1)
        print(f"  ok [{label}]")

# ---------------------------------------------------------------- transformaciones

def literalizar_heading(doc, texto, estilo, numero):
    """Numeracion automatica -> literal: agrega numPr numId=0 y antepone el numero."""
    p = doc.find_para(texto, estilo)
    m = re.search(r'(<w:pPr><w:pStyle w:val="%s"/>)' % estilo, p)
    if not m:
        die(f"pPr inesperado en {texto!r}")
    new = p.replace(m.group(1), m.group(1) + NUMPR_OFF, 1)
    tm = re.search(r'<w:t(?: xml:space="preserve")?>', new)
    if not tm:
        die(f"sin w:t en {texto!r}")
    new = new.replace(tm.group(0), f'<w:t xml:space="preserve">{numero} ', 1)
    doc.replace_para(p, new, f"literal {numero} {texto[:35]}")

def punto_tras_numero(doc, prefijo, estilo):
    """'4.1 Titulo' -> '4.1. Titulo' en el primer w:t del parrafo."""
    p = doc.find_para(prefijo + " ", estilo, startswith=True)
    old_frag = re.search(r'<w:t[^>]*>' + re.escape(prefijo) + r' ', p)
    if not old_frag:
        die(f"no encuentro el prefijo {prefijo!r} en su primer w:t")
    new = p.replace(old_frag.group(0), old_frag.group(0).replace(prefijo + " ", prefijo + ". "), 1)
    doc.replace_para(p, new, f"punto {prefijo}.")

def caption_dos_lineas(doc, p):
    """Caption inline -> identificador (negrita, del estilo Caption) + salto de
    linea manual + titulo en cursiva sin negrita. Word convierte el salto en un
    espacio al regenerar los indices \\c, conservando numero + titulo + pagina
    (comportamiento verificado empiricamente con Word 16 en un docx minimo)."""
    m = re.match(r'(<w:p(?: [^>]*)?>)(<w:pPr>.*?</w:pPr>)(.*)(</w:p>)$', p, re.S)
    if not m:
        die("caption sin estructura esperada")
    popen, ppr, body, pclose = m.groups()
    seq = re.search(r'^(.*?</w:fldSimple>)(.*)$', body, re.S)
    if not seq:
        die(f"caption sin fldSimple SEQ: {ptext(p)[:50]!r}")
    ident_part, resto = seq.groups()
    # quitar separadores (runs de solo espacios o tab) al inicio del resto
    while True:
        ws = re.match(r'^<w:r(?: [^>]*)?>(?:<w:rPr>.*?</w:rPr>)?(?:<w:t xml:space="preserve">\s*</w:t>|<w:tab/>)</w:r>', resto, re.S)
        if not ws:
            break
        resto = resto[ws.end():]
    resto = re.sub(r'<w:proofErr [^>]*/>', '', resto)
    if not ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', resto)).strip():
        die(f"caption sin titulo tras el SEQ: {ptext(p)[:50]!r}")
    num_m = re.search(r'<w:fldSimple[^>]*>.*?<w:t[^>]*>(\d+)</w:t>.*?</w:fldSimple>', ident_part, re.S)
    etiqueta = 'Figura' if 'SEQ Ilustración' in ident_part else 'Tabla'
    # titulo: cursiva y sin negrita (la negrita viene del estilo Caption)
    def marcar_run(rm):
        rtag, rpr, restor = rm.group(1), rm.group(2), rm.group(3)
        if rpr and re.search(r'<w:(rStyle|rFonts)', rpr):
            die(f"run de titulo con rPr complejo en {etiqueta} {num_m.group(1)}")
        inner = re.sub(r'^<w:rPr>|</w:rPr>$', '', rpr) if rpr else ''
        return f'{rtag}<w:rPr><w:b w:val="0"/><w:bCs w:val="0"/><w:i/><w:iCs/>{inner}</w:rPr>{restor}'
    resto = re.sub(r'(<w:r(?: [^>]*)?>)(<w:rPr>.*?</w:rPr>)?((?:(?!</w:r>).)*</w:r>)', marcar_run, resto, flags=re.S)
    nuevo = popen + ppr + ident_part + '<w:r><w:br/></w:r>' + resto + pclose
    doc.replace_para(p, nuevo, f"caption {etiqueta} {num_m.group(1)}")

def arreglar_nota(doc, p):
    """Nota de un solo run todo en cursiva -> 'Nota.' cursiva + resto normal."""
    runs = re.findall(r'<w:r(?: [^>]*)?>.*?</w:r>', p, re.S)
    if len(runs) != 1:
        die(f"nota con {len(runs)} runs, esperaba 1: {ptext(p)[:50]!r}")
    run = runs[0]
    m = re.match(r'(<w:r(?: [^>]*)?>)(<w:rPr>.*?</w:rPr>)?(<w:t[^>]*>)Nota\.\s(.*)(</w:t></w:r>)$', run, re.S)
    if not m:
        die(f"estructura de nota inesperada: {ptext(p)[:50]!r}")
    ropen, rpr, topen, resto_txt, rclose = m.groups()
    rpr = rpr or '<w:rPr></w:rPr>'
    if '<w:i/>' not in rpr:
        die(f"la nota no estaba en cursiva: {ptext(p)[:50]!r}")
    rpr_plain = rpr.replace('<w:i/>', '').replace('<w:iCs/>', '')
    run1 = f'{ropen}{rpr}<w:t>Nota.</w:t></w:r>'
    run2 = f'{ropen}{rpr_plain}<w:t xml:space="preserve"> {resto_txt}{rclose}'
    doc.replace_para(p, p.replace(run, run1 + run2, 1), f"nota {ptext(p)[6:40]!r}")

def parrafo_nuevo(texto):
    return f'<w:p><w:r><w:t xml:space="preserve">{texto}</w:t></w:r></w:p>'

# ---------------------------------------------------------------- main

def main():
    if not BASE.exists():
        shutil.copy2(DOCX, BASE)
        print(f"backup original -> {BASE.name}")
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    with zipfile.ZipFile(BASE) as z:
        names = z.namelist()
        z.extractall(WORK)

    doc = Doc((WORK / "word/document.xml").read_text(encoding="utf-8"))

    print("== A. literalizar numeracion caps 1-3 ==")
    plan = [
        ("Introducción", "Heading1", "1."),
        ("Motivación", "Heading2", "1.1."),
        ("Planteamiento del trabajo", "Heading2", "1.2."),
        ("Estructura del trabajo", "Heading2", "1.3."),
        ("Contexto y estado del arte", "Heading1", "2."),
        ("Contexto del problema", "Heading2", "2.1."),
        ("La lengua Inga y su situación en el Putumayo", "Heading3", "2.1.1."),
        ("Marco legal-político en Colombia y contexto internacional", "Heading3", "2.1.2."),
        ("Traducción automática de bajos recursos: fundamentos", "Heading3", "2.1.3."),
        ("Transfer learning y recuperación aumentada: definiciones", "Heading3", "2.1.4."),
        ("Estado del arte", "Heading2", "2.2."),
        ("Procesamiento del lenguaje natural para lenguas indígenas de América Latina", "Heading3", "2.2.1."),
        ("Traducción automática de lenguas indígenas colombianas", "Heading3", "2.2.2."),
        ("Traducción automática para Quechua: el caso cercano al Inga", "Heading3", "2.2.3."),
        ("Modelos de lenguaje de frontera para traducción", "Heading3", "2.2.4."),
        ("Recuperación aumentada aplicada a traducción", "Heading3", "2.2.5."),
        ("Técnicas de ajuste fino eficiente en parámetros", "Heading3", "2.2.6."),
        ("Modelos base candidatos: análisis comparativo", "Heading3", "2.2.7."),
        ("Conclusiones del capítulo", "Heading2", "2.3."),
        ("Objetivos concretos y metodología de trabajo", "Heading1", "3."),
        ("Objetivo general", "Heading2", "3.1."),
        ("Objetivos específicos", "Heading2", "3.2."),
        ("Metodología del trabajo", "Heading2", "3.3."),
        ("Enfoque metodológico", "Heading3", "3.3.1."),
        ("Cronograma", "Heading3", "3.3.3."),
        ("Infraestructura de cómputo", "Heading3", "3.3.4."),
        ("Configuraciones experimentales a evaluar", "Heading3", "3.3.5."),
    ]
    for texto, estilo, numero in plan:
        literalizar_heading(doc, texto, estilo, numero)

    print("== B. punto final en numeros literales caps 3-5 ==")
    punto_tras_numero(doc, "3.3.2", "Heading3")
    for pref in ("4.1", "4.2", "4.2.1", "4.2.2", "4.2.3", "4.2.4", "4.2.5", "4.2.6",
                 "4.3", "4.4", "4.5", "4.5.1", "4.5.2", "4.6", "4.6.1", "4.6.2",
                 "4.7"):
        punto_tras_numero(doc, pref, "Heading2" if pref.count('.') == 1 else "Heading3")
    for pref in ("5.1", "5.2", "5.3"):
        punto_tras_numero(doc, pref, "Heading2")

    print("== C. titulo del capitulo 4: Heading3 -> Heading1 ==")
    p = doc.find_para("4. Desarrollo específico de la contribución", "Heading3")
    doc.replace_para(p, p.replace('<w:pStyle w:val="Heading3"/>', '<w:pStyle w:val="Heading1"/>', 1), "cap4 Heading1")

    print("== D. Anexo A: desactivar numeracion del estilo ==")
    p = doc.find_para("Anexo A. Código fuente y datos analizados", "Anexo")
    if '<w:numPr>' in p:
        die("el parrafo del Anexo ya tiene numPr")
    doc.replace_para(p, p.replace('<w:pageBreakBefore/>', '<w:pageBreakBefore/>' + NUMPR_OFF, 1), "anexo numId=0")

    print("== E. Quechua -> quechua ==")
    # en el titulo del cuerpo "Quechua" va en un run propio (marcas de corrector)
    p = doc.find_para("2.2.3. Traducción automática para Quechua: el caso cercano al Inga", "Heading3")
    if p.count("<w:t>Quechua</w:t>") != 1:
        die("no encuentro el run 'Quechua' dentro del titulo 2.2.3")
    doc.replace_para(p, p.replace("<w:t>Quechua</w:t>", "<w:t>quechua</w:t>", 1), "quechua titulo 2.2.3")
    # entrada cacheada del TOC (F9 la regenerara igual, pero que el preview quede bien)
    if doc.xml.count("para Quechua") != 1:
        die(f"esperaba 1 'para Quechua' restante en el TOC cacheado, hay {doc.xml.count('para Quechua')}")
    doc.xml = doc.xml.replace("para Quechua", "para quechua", 1)
    print("  ok [quechua TOC cacheado]")

    print("== F. captions en dos lineas (salto de linea manual) ==")
    captions = [q for q in doc.paras() if pstyle(q) == 'Caption' and 'SEQ' in q]
    if len(captions) != 22:
        die(f"esperaba 22 captions con SEQ, hay {len(captions)}")
    for q in captions:
        caption_dos_lineas(doc, q)

    print("== G2. marcar los 3 campos TOC como dirty (Word los regenera al abrir) ==")
    marcados = 0
    for m in list(re.finditer(r'<w:instrText[^>]*> TOC [^<]*</w:instrText>', doc.xml)):
        ini = doc.xml.rfind('<w:fldChar w:fldCharType="begin"/>', 0, m.start())
        if ini == -1:
            die("campo TOC sin fldChar begin precedente")
        doc.xml = (doc.xml[:ini]
                   + '<w:fldChar w:fldCharType="begin" w:dirty="true"/>'
                   + doc.xml[ini + len('<w:fldChar w:fldCharType="begin"/>'):])
        marcados += 1
    if marcados != 3:
        die(f"esperaba marcar 3 TOC dirty, marque {marcados}")
    print("  ok [3 TOC dirty]")

    print("== H. notas: solo 'Nota.' en cursiva ==")
    notas = [q for q in doc.paras()
             if ptext(q).startswith('Nota. ')
             and len(re.findall(r'<w:r(?: [^>]*)?>.*?</w:r>', q, re.S)) == 1]
    if len(notas) != 6:
        die(f"esperaba 6 notas de un solo run, hay {len(notas)}")
    for q in notas:
        arreglar_nota(doc, q)

    print("== I. invitaciones y referencia del cronograma ==")
    old = "cronograma global del proyecto se muestra en la Figura 8"
    if doc.xml.count(old) != 1:
        die("referencia del cronograma no encontrada")
    doc.xml = doc.xml.replace(old, old.replace("Figura 8", "Figura 7"), 1)
    print("  ok [cronograma -> Figura 7]")

    p = doc.find_para("El Notebook 07 unifica las salidas", startswith=True)
    inv = '<w:r><w:t xml:space="preserve"> La distribución resultante por libro y partición se muestra en la Figura 8.</w:t></w:r>'
    doc.replace_para(p, p[:-len('</w:p>')] + inv + '</w:p>', "invitacion Figura 8")

    # las capturas ya estan partidas: el identificador es ahora un parrafo "Tabla 6" etc.
    objetivo = doc.find_para("El índice de ejemplos indexa los 4.471 pares", startswith=True)
    doc.replace_para(objetivo, objetivo + parrafo_nuevo("La arquitectura resultante del sistema de recuperación se muestra en la Figura 9."), "invitacion Figura 9")

    nota_fig8 = doc.find_para("Nota. Elaboración propia a partir del Notebook 07.", startswith=True)
    doc.replace_para(nota_fig8, nota_fig8 + parrafo_nuevo("El desglose por dialecto de las tres particiones se detalla en la Tabla 6."), "invitacion Tabla 6")

    quinto = doc.find_para("Quinto, BERTScore presenta menor variación", startswith=True)
    doc.replace_para(quinto, quinto + parrafo_nuevo("La comparación visual de las tres métricas por configuración y dirección se presenta en la Figura 11."), "invitacion Figura 11")

    (WORK / "word/document.xml").write_text(doc.xml, encoding="utf-8")
    print("== settings.xml: updateFields al abrir ==")
    stp = WORK / "word/settings.xml"
    st = stp.read_text(encoding="utf-8")
    if '<w:updateFields' in st:
        die("settings.xml ya tiene updateFields")
    if st.count('<w:compat>') != 1:
        die("no encuentro <w:compat> como ancla en settings.xml")
    st = st.replace('<w:compat>', '<w:updateFields w:val="true"/><w:compat>', 1)
    stp.write_text(st, encoding="utf-8")
    print("  ok [updateFields=true]")

    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            z.write(WORK / name, name)
    print(f"\nDocx corregido: {DOCX}")
    print("Paso siguiente: abrir en Word y actualizar todos los campos (Cmd+A, F9).")

if __name__ == "__main__":
    main()
