#!/usr/bin/env python3
"""
Coletor de imóveis da Imobiliária Daros.

Fonte: sitemap.xml do site (lista todas as páginas /imovel/...) + a página de
cada imóvel. Gera imoveis.json e imoveis.js na mesma pasta deste arquivo.

Uso:  python coletor.py
"""
import json
import os
import random
import re
import sys
import time
from datetime import date, datetime
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

# O servidor do site envia a cadeia de certificados incompleta; o Windows/Mac completam sozinhos,
# mas o "certifi" do requests não. Usar o repositório de certificados do sistema resolve,
# sem desligar a verificação de segurança.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

SITE = "https://imobiliariadaros.com.br"
SITEMAP = SITE + "/sitemap.xml"
PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_JSON = os.path.join(PASTA, "imoveis.json")
ARQ_JS = os.path.join(PASTA, "imoveis.js")
ARQ_LOG = os.path.join(PASTA, "coletor.log")

PAUSA = 1.0               # segundos de pausa entre requisições (+ um pouco de variação)
TENTATIVAS = 3
TIMEOUT = 30
DIAS_DESTAQUE = 7         # por quantos dias "novo"/"valor alterado"/"removido" continuam marcados
MAX_FALHAS = 0.30         # se mais de 30% das páginas falharem, a lista atual NÃO é alterada
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ColetorImoveisDaros/1.0; uso interno da imobiliaria)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

sessao = requests.Session()
sessao.headers.update(HEADERS)


def log(msg):
    linha = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(linha, flush=True)
    try:
        with open(ARQ_LOG, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except OSError:
        pass


class PaginaNaoExiste(Exception):
    pass


def baixar(url):
    """Baixa uma URL com novas tentativas. 404/410 => PaginaNaoExiste."""
    ultimo = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            r = sessao.get(url, timeout=TIMEOUT)
            if r.status_code in (404, 410):
                raise PaginaNaoExiste(url)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except PaginaNaoExiste:
            raise
        except requests.RequestException as e:
            ultimo = e
            time.sleep(3 * tentativa)
    raise RuntimeError(f"falha ao baixar {url}: {ultimo}")


def limpar(txt):
    return re.sub(r"\s+", " ", (txt or "").replace("\xa0", " ")).strip()


def numero_br(txt):
    """'1.234,56' -> 1234.56"""
    try:
        return float(txt.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def urls_do_sitemap():
    xml = baixar(SITEMAP)
    raiz = ElementTree.fromstring(xml.encode("utf-8"))
    urls = [e.text.strip() for e in raiz.iter() if e.tag.endswith("}loc") and e.text]
    return sorted({u for u in urls if re.search(r"/imovel/\d+/", u)})


def extrair_imovel(html, url):
    sopa = BeautifulSoup(html, "html.parser")
    codigo = re.search(r"/imovel/(\d+)/", url).group(1)

    h1 = sopa.find("h1")
    titulo = limpar(h1.get_text(" ")) if h1 else ""
    if not titulo:
        raise ValueError("página sem título (layout mudou?)")

    # "Casa à venda em Maringá - PR - Jardim Novo Oásis"
    tipo = limpar(re.split(r"\s+(?:à|a)\s+(?:venda|alugar)|\s+para\s+", titulo, flags=re.I)[0])
    cidade = uf = bairro = ""
    m = re.search(r"\bem\s+(.+?)\s+-\s+([A-Z]{2})(?:\s+-\s+(.+))?$", titulo)
    if m:
        cidade, uf, bairro = m.group(1), m.group(2), m.group(3) or ""

    # bloco "Localização": Endereço / Bairro / Cidade
    campos = {}
    for p in sopa.select(".location p"):
        rotulo = p.find("span", class_="label")
        if rotulo:
            nome = limpar(rotulo.get_text())
            rotulo.extract()
            campos[nome] = limpar(p.get_text(" "))
    bairro = bairro or campos.get("Bairro", "")
    if not cidade and campos.get("Cidade"):
        cid = campos["Cidade"].split(",")
        cidade = cid[0].strip().title()
        uf = cid[1].strip() if len(cid) > 1 else uf

    # endereço: linhas do cabeçalho (ex.: "Condomínio X" / "Rua Y, 292")
    box = sopa.select_one(".endereco")
    linhas = []
    if box:
        for pedaco in box.stripped_strings:
            pedaco = limpar(pedaco)
            if pedaco:
                linhas.append(pedaco)
    rua = linhas and ", ".join(linhas) or campos.get("Endereço", "")
    partes = [rua, bairro, f"{cidade} - {uf}" if cidade and uf else cidade]
    endereco = ", ".join(p for p in partes if p)

    # valor
    el = sopa.select_one(".valor-iptu-cond .valor") or sopa.select_one(".valor")
    valor_txt = limpar(el.get_text()) if el else ""
    mv = re.search(r"R\$\s*([\d.]+(?:,\d+)?)", valor_txt)
    valor = numero_br(mv.group(1)) if mv else None

    # quartos / suítes / banheiros / vagas / área (ícones do topo)
    quartos = suites = banheiros = vagas = None
    area_destaque = None
    for item in sopa.select(".detalhes-caracteristicas .detalhes-item"):
        txt = limpar(item.get_text(" "))
        for n, rotulo in re.findall(r"(\d+)\s*(su[ií]tes?|quartos?|dormit[óo]rios?|bwc|banheiros?|vagas?)", txt, re.I):
            r = rotulo.lower()
            n = int(n)
            if r.startswith("su"):
                suites = n
            elif r.startswith(("quarto", "dormit")):
                quartos = n
            elif r in ("bwc",) or r.startswith("banheiro"):
                banheiros = n
            elif r.startswith("vaga"):
                vagas = n
        ma = re.search(r"([\d.]+(?:,\d+)?)\s*m", txt)
        if ma and not re.search(r"quarto|su[ií]te|bwc|vaga", txt, re.I):
            area_destaque = numero_br(ma.group(1))
    quartos_total = None
    if quartos is not None or suites is not None:
        quartos_total = (quartos or 0) + (suites or 0)

    # áreas detalhadas
    areas = {}
    for rotulo, v in re.findall(r"(Área [\wçãéú ]+?):\s*([\d.]+(?:,\d+)?)\s*m", sopa.get_text(" ")):
        areas.setdefault(limpar(rotulo).lower(), numero_br(v))
    area = (areas.get("área construída") or areas.get("área útil") or areas.get("área privativa")
            or areas.get("área total") or areas.get("área do terreno") or area_destaque)

    og = sopa.find("meta", property="og:image")
    return {
        "codigo": codigo,
        "titulo": titulo,
        "tipo": tipo,
        "endereco": endereco,
        "bairro": bairro,
        "cidade": cidade,
        "uf": uf,
        "valor": valor,
        "valor_texto": valor_txt,
        "quartos": quartos_total,
        "suites": suites,
        "banheiros": banheiros,
        "vagas": vagas,
        "area": area,
        "area_total": areas.get("área total"),
        "area_construida": areas.get("área construída") or areas.get("área útil"),
        "area_terreno": areas.get("área do terreno"),
        "link": url,
        "imagem": og["content"] if og and og.get("content") else "",
    }


def carregar_anterior():
    if not os.path.exists(ARQ_JSON):
        return {}
    try:
        with open(ARQ_JSON, encoding="utf-8") as f:
            dados = json.load(f)
        return {i["codigo"]: i for i in dados.get("imoveis", [])}
    except (OSError, ValueError, KeyError) as e:
        log(f"AVISO: não consegui ler o imoveis.json anterior ({e}); tratando tudo como novo.")
        return {}


def dias_desde(txt, hoje):
    try:
        return (hoje - date.fromisoformat(txt)).days
    except (TypeError, ValueError):
        return 10 ** 6


def aplicar_status(novo, antigo, hoje):
    """Define status/valor_antigo comparando com o registro anterior."""
    hoje_s = hoje.isoformat()
    novo["ultima_vez_visto"] = hoje_s
    if antigo is None or antigo.get("status") == "removido":
        novo.update(status="novo", valor_antigo=None, primeira_vez_visto=hoje_s, status_desde=hoje_s)
        return
    novo["primeira_vez_visto"] = antigo.get("primeira_vez_visto", hoje_s)
    if novo["valor"] != antigo.get("valor") and antigo.get("valor") is not None and novo["valor"] is not None:
        novo.update(status="valor alterado", valor_antigo=antigo["valor"], status_desde=hoje_s)
        return
    # sem mudança hoje: mantém o destaque anterior enquanto estiver dentro do prazo
    st = antigo.get("status")
    desde = antigo.get("status_desde")
    if st in ("novo", "valor alterado") and dias_desde(desde, hoje) < DIAS_DESTAQUE:
        novo.update(status=st, valor_antigo=antigo.get("valor_antigo"), status_desde=desde)
    else:
        novo.update(status="", valor_antigo=None, status_desde=None)


def salvar(imoveis):
    pacote = {
        "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fonte": SITE,
        "total": sum(1 for i in imoveis if i["status"] != "removido"),
        "imoveis": imoveis,
    }
    texto = json.dumps(pacote, ensure_ascii=False, indent=2)
    for caminho, conteudo in ((ARQ_JSON, texto),
                              (ARQ_JS, "window.IMOVEIS_DATA = " + texto + ";\n")):
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(conteudo)
        os.replace(tmp, caminho)  # troca atômica: nunca deixa o arquivo pela metade
    return pacote


def main():
    hoje = date.today()
    anterior = carregar_anterior()
    log(f"Iniciando coleta. Imóveis na lista anterior: {len(anterior)}")

    try:
        urls = urls_do_sitemap()
    except Exception as e:
        log(f"ERRO: não consegui ler o sitemap ({e}). Lista atual mantida.")
        return 1
    if not urls:
        log("ERRO: sitemap sem imóveis. Lista atual mantida.")
        return 1
    log(f"Sitemap: {len(urls)} imóveis encontrados.")

    coletados, falhas, inexistentes = {}, [], []
    for n, url in enumerate(urls, 1):
        codigo = re.search(r"/imovel/(\d+)/", url).group(1)
        try:
            coletados[codigo] = extrair_imovel(baixar(url), url)
        except PaginaNaoExiste:
            inexistentes.append(codigo)
        except Exception as e:
            falhas.append(codigo)
            log(f"  falha em {codigo}: {e}")
        if n % 25 == 0:
            log(f"  {n}/{len(urls)} páginas lidas")
        time.sleep(PAUSA + random.uniform(0, 0.5))

    if len(falhas) > MAX_FALHAS * len(urls):
        log(f"ERRO: {len(falhas)} de {len(urls)} páginas falharam. Lista atual mantida.")
        return 1

    resultado = []
    for codigo, novo in coletados.items():
        aplicar_status(novo, anterior.get(codigo), hoje)
        resultado.append(novo)
    # páginas que falharam hoje: mantém o registro antigo (se existir) sem marcar nada
    for codigo in falhas:
        if codigo in anterior and anterior[codigo].get("status") != "removido":
            resultado.append(anterior[codigo])

    # removidos: estavam na lista anterior e saíram do site
    vistos = set(coletados) | set(falhas)
    removidos = 0
    for codigo, antigo in anterior.items():
        if codigo in vistos:
            continue
        if antigo.get("status") == "removido":
            if dias_desde(antigo.get("status_desde"), hoje) < DIAS_DESTAQUE:
                resultado.append(antigo)   # continua aparecendo como removido por alguns dias
        else:
            antigo = dict(antigo, status="removido", status_desde=hoje.isoformat())
            resultado.append(antigo)
            removidos += 1

    resultado.sort(key=lambda i: i["codigo"])
    pacote = salvar(resultado)

    cont = {}
    for i in resultado:
        cont[i["status"] or "sem mudança"] = cont.get(i["status"] or "sem mudança", 0) + 1
    log(f"Concluído. Ativos: {pacote['total']} | falhas: {len(falhas)} | resumo: {cont}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
