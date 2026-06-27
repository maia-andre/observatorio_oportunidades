"""Taxonomia e palavras-chave da Fase 2 — Curadoria Automatizada (issue #7).

Mapa ORDENADO `categoria → [palavras-chave]`. A ordem define a prioridade:
a **primeira** categoria com alguma palavra-chave correspondente vence.

As palavras-chave devem ser escritas **sem acento e em minúsculas**, pois o
classificador (`processing/classifier.py`) normaliza o texto da oportunidade da
mesma forma (lowercase + remoção de acentos) antes de comparar. Usa-se
correspondência por substring, então radicais ("climatic", "smart cit") casam
variações de gênero/número.
"""

from collections import OrderedDict

# Em Python 3.7+ os dicts já preservam a ordem de inserção; OrderedDict deixa
# explícita a intenção de "ordem = prioridade".
RULES = OrderedDict([
    ("Emendas",          ["emenda", "emenda parlamentar"]),
    ("Premiações",       ["premio", "premiacao", "premiacoes", "reconhecimento", "award", "prize", "concurso"]),
    ("Certificações",    ["certificacao", "certificado", "selo", "acreditacao", "credenciamento"]),
    ("Saúde",            ["saude", "hospital", "ubs", "sanitaria", "vacina", "epidem", "diagnostico",
                          "laboratorial", "fiocruz", "medic", "pediatria", "doenca", "sorolog", "virus", "viral"]),
    ("Educação",         ["educacao", "escola", "ensino", "professor", "aluno", "bolsa", "estagi",
                          "mestrado", "pos-graduacao", "graduacao", "diploma", "docente", "extensao",
                          "congresso", "capacitacao", "qualificacao", "seminario", "workshop", "oficina"]),
    ("Sustentabilidade", ["sustentavel", "sustentabilidade", "sustainability", "ambiental", "ambientais",
                          "climatic", "clima", "residuos", "reciclag", "energia limpa", "ibama", "economia circular",
                          "pesqueiro", "defeso"]),
    ("Mobilidade",       ["mobilidade", "transporte", "transito", "ciclovia", "pedestre", "aviacao", "aeroporto", "portos"]),
    ("Inovação",         ["inovacao", "cidades inteligentes", "smart cit", "tecnologia", "startup",
                          "transformacao digital", "innovation"]),
    # Licitações/compras públicas (fontes estruturadas, ex.: PNCP). Vem antes do
    # guarda-chuva "Convênios" para capturar o vocabulário de contratação pública.
    ("Licitações",       ["licitacao", "pregao", "registro de precos", "srp", "concorrencia",
                          "tomada de precos", "dispensa de licitacao", "aquisicao", "contratacao de"]),
    # Convênios fica por último: atua como guarda-chuva para "editais/chamadas"
    # genéricos que não casaram com uma categoria mais específica acima.
    ("Convênios",        ["convenio", "chamamento", "chamada publica", "chamada aberta", "termo de fomento", "edital", "chamada"]),
])

# Termos negativos (B1b): vetam a categoria inteira mesmo que uma palavra-chave
# tenha casado — úteis contra falsos-positivos. categoria -> termos (sem acento).
NEGATIVES = {
    # "concurso público" (servidores) casa "concurso" mas não é premiação.
    "Premiações": ["concurso publico"],
}
