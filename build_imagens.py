# Baixa retratos da Wikipédia (só licença livre), recorta o rosto e embute como data URI.
# Uso:  python build_imagens.py relatorio     -> só resolve nomes e imprime o relatório
#       python build_imagens.py embutir       -> baixa, processa e injeta em index.html
import re, sys, json, io, base64, urllib.parse, urllib.request, os

AQUI = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(AQUI, "index.html")
CACHE = os.path.join(AQUI, ".cache-retratos")
UA = "CemAnosDeGoverno/1.0 (projeto pessoal de estudo)"

# nomes do roster que não batem com o título da Wikipédia em português
OVERRIDES = {
    "Carlos V": "Carlos V do Sacro Império Romano-Germânico",
    "Dom Pedro I": "Pedro I do Brasil",
    "Dom Pedro II": "Pedro II do Brasil",
    "Princesa Isabel": "Isabel, Princesa Imperial do Brasil",
    "Sula": "Lúcio Cornélio Sula",
    "Catão, o Velho": "Catão, o Velho",
    "Tibério Graco": "Tibério Semprônio Graco (tribuno da plebe)",
    "César Augusto": "Augusto",
    "Cipião Africano": "Cipião Africano",
    "Imperador Kangxi": "Kangxi",
    "Leônidas I": "Leônidas I",
    "Filipe II da Macedônia": "Filipe II da Macedônia",
    "William Pitt, o Jovem": "William Pitt, o Jovem",
    "Duque de Wellington": "Arthur Wellesley, 1.º Duque de Wellington",
    "Rainha Vitória": "Vitória do Reino Unido",
    "Lord Palmerston": "Henry John Temple, 3.º Visconde Palmerston",
    "Ivã, o Terrível": "Ivan, o Terrível",
    "Pedro, o Grande": "Pedro, o Grande",
    "Catarina, a Grande": "Catarina II da Rússia",
    "Nikita Khrushchov": "Nikita Khrushchov",
    "Leon Trótski": "Leon Trótski",
    "Karl vom Stein": "Heinrich Friedrich Karl vom Stein",
    "Mehmed Köprülü": "Köprülü Mehmed Paxá",
    "Umar ibn al-Khattab": "Omar ibn al-Khattab",
    "Abderramão III": "Abderramão III",
    "Nur ad-Din": "Nur ad-Din Zengi",
    "Gengis Khan": "Gengis Khan",
    "Qin Shi Huang": "Qin Shi Huang",
    "Mao Tsé-Tung": "Mao Tsé-Tung",
    "Talleyrand": "Charles Maurice de Talleyrand-Périgord",
    "Cardeal Richelieu": "Cardeal de Richelieu",
    "Barão do Rio Branco": "José Maria da Silva Paranhos Júnior",
    "Duque de Caxias": "Luís Alves de Lima e Silva",
    "José Bonifácio": "José Bonifácio de Andrada e Silva",
    "Luís IX": "Luís IX de França",
    "Buda": "Sidarta Gautama",
    "Lao-Tsé": "Lao Zi",
    "Arcanjo Miguel": "Miguel (arcanjo)",
    "Arcanjo Rafael": "Rafael (arcanjo)",
    "Casimiro": "Casimiro (streamer)",
}

# quem não tem foto livre na Wikipédia: arquivo com o nome exato do roster
# (ex.: "Raiam Santos.jpg") nesta pasta. Tem prioridade sobre a Wikipédia.
MANUAIS = os.path.join(AQUI, "retratos-manuais")

def manual(n):
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = os.path.join(MANUAIS, n + ext)
        if os.path.exists(p): return p
    return None

def nomes():
    txt = open(HTML, encoding="utf-8").read()
    return re.findall(r'^f\("([^"]+)"', txt, re.M)

# segunda tentativa na Wikipédia em inglês, para quem a versão em português não tem foto livre
EN = {
    "Ievgueni Primakov": "Yevgeny Primakov",
    "Serguei Lavrov": "Sergey Lavrov",
    "Bhimrao Ambedkar": "B. R. Ambedkar",
    "Nzinga de Matamba": "Nzinga of Ndongo and Matamba",
    "Sundiata Keita": "Sundiata Keita",
    "Duque de Caxias": "Luís Alves de Lima e Silva, Duke of Caxias",
    "Tibério Graco": "Tiberius Gracchus",
    "Henrique IV": "Henry IV of France",
    "Lord Palmerston": "Lord Palmerston",
    "Guilherme II": "Wilhelm II, German Emperor",
    "Karl vom Stein": "Heinrich Friedrich Karl vom Stein",
    "Mehmed Köprülü": "Köprülü Mehmed Pasha",
    "Luís IX": "Louis IX of France",
    "Pachacútec": "Pachacuti",
}

# quando a página em português tem imagem, mas a em inglês tem uma melhor para retrato
FORCAR_EN = {
    "Jesus Cristo": "Jesus",
    "Krishna": "Krishna",
    "Arcanjo Gabriel": "Gabriel",
    "Xangô": "Shango",
    "Lúcifer": "Lucifer",
    "Belzebu": "Beelzebub",
    "Mamon": "Mammon",
    "Ogum": "Ogun",
}

def api(titulos, lang="pt"):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2", "redirects": "1",
        "prop": "pageimages", "piprop": "thumbnail|name", "pithumbsize": "260",
        "pilicense": "free", "titles": "|".join(titulos),
    })
    req = urllib.request.Request(f"https://{lang}.wikipedia.org/w/api.php?" + q, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=60))

def buscar(alvo, lang):
    """alvo = {nome_roster: titulo}; devolve {nome_roster: pagina}"""
    porTitulo = {}
    titulos = sorted(set(alvo.values()))
    for i in range(0, len(titulos), 45):
        d = api(titulos[i:i+45], lang)
        norm = {x["from"]: x["to"] for x in d.get("query", {}).get("normalized", [])}
        redir = {x["from"]: x["to"] for x in d.get("query", {}).get("redirects", [])}
        for pg in d.get("query", {}).get("pages", []):
            porTitulo[pg["title"]] = pg
        for t in titulos[i:i+45]:
            t2 = redir.get(norm.get(t, t), norm.get(t, t))
            if t2 in porTitulo:
                porTitulo[t] = porTitulo[t2]
    return {n: porTitulo.get(t, {}) for n, t in alvo.items()}

def resolver(todos):
    """devolve {nome_roster: (titulo_resolvido, url_thumb|None, arquivo|None)}"""
    pags = buscar({n: OVERRIDES.get(n, n) for n in todos}, "pt")
    faltam = {n: EN[n] for n in todos if not pags.get(n, {}).get("thumbnail") and n in EN}
    faltam.update({n: FORCAR_EN[n] for n in todos if n in FORCAR_EN})
    if faltam:
        for n, pg in buscar(faltam, "en").items():
            if pg.get("thumbnail"): pags[n] = pg
    out = {}
    for n in todos:
        pg = pags.get(n, {})
        th = pg.get("thumbnail", {})
        out[n] = (pg.get("title", n), th.get("source"), pg.get("pageimage"))
    return out

def relatorio():
    todos = nomes()
    res = resolver(todos)
    faltam = []
    for n in todos:
        titulo, url, arq = res[n]
        marca = "man" if manual(n) else "ok " if url else "SEM"
        if not url and not manual(n): faltam.append(n)
        print(f"{marca} | {n[:26]:26} | {titulo[:34]:34} | {(arq or '-')[:52]}")
    print(f"\n{len(todos)-len(faltam)}/{len(todos)} com retrato livre.")
    if faltam:
        print("SEM RETRATO: " + ", ".join(faltam))
    json.dump({n: res[n][1] for n in todos}, open(os.path.join(AQUI, ".urls.json"), "w", encoding="utf-8"), ensure_ascii=False)

def recortar(dados):
    """quadrado no terço superior — retrato de corpo inteiro vira rosto"""
    from PIL import Image
    im = Image.open(io.BytesIO(dados)).convert("RGB")
    w, h = im.size
    lado = min(w, h)
    esq = (w - lado) // 2
    topo = 0 if h <= w else int(h * 0.06)          # painéis altos: começa perto do topo
    if topo + lado > h: topo = h - lado
    im = im.crop((esq, topo, esq + lado, topo + lado)).resize((96, 96), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72, optimize=True, progressive=False)
    return buf.getvalue()

def embutir():
    os.makedirs(CACHE, exist_ok=True)
    urls = json.load(open(os.path.join(AQUI, ".urls.json"), encoding="utf-8"))
    imgs, total, faltam = {}, 0, []
    for n in nomes():
        url = urls.get(n)
        m = manual(n)
        if m:
            jpg = recortar(open(m, "rb").read())
            imgs[n] = "data:image/jpeg;base64," + base64.b64encode(jpg).decode()
            total += len(jpg)
            continue
        if not url:
            faltam.append(n); continue
        cam = os.path.join(CACHE, re.sub(r"[^\w]", "_", n) + ".jpg")
        try:
            if os.path.exists(cam):
                jpg = open(cam, "rb").read()
            else:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                jpg = recortar(urllib.request.urlopen(req, timeout=60).read())
                open(cam, "wb").write(jpg)
            imgs[n] = "data:image/jpeg;base64," + base64.b64encode(jpg).decode()
            total += len(jpg)
        except Exception as e:
            print("falhou:", n, e); faltam.append(n)
    bloco = "const IMG=" + json.dumps(imgs, ensure_ascii=False, separators=(",", ":")) + ";"
    txt = open(HTML, encoding="utf-8").read()
    novo = re.sub(r"/\*IMG-INICIO\*/.*?/\*IMG-FIM\*/",
                  lambda m: "/*IMG-INICIO*/" + bloco + "/*IMG-FIM*/", txt, flags=re.S)
    if novo == txt:
        print("!! marcador /*IMG-INICIO*/.../*IMG-FIM*/ não encontrado em index.html"); return
    open(HTML, "w", encoding="utf-8").write(novo)
    print(f"{len(imgs)} retratos embutidos · {total/1024:.0f} KB de JPEG · {len(bloco)/1024:.0f} KB de base64")
    if faltam: print("sem retrato: " + ", ".join(faltam))

if __name__ == "__main__":
    (relatorio if sys.argv[1:] == ["relatorio"] else embutir)()
