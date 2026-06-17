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
    ("Premiações",       ["premio", "premiacao", "reconhecimento"]),
    ("Certificações",    ["certificacao", "certificado", "selo", "acreditacao"]),
    ("Saúde",            ["saude", "hospital", "ubs", "sanitaria", "vacina", "epidem"]),
    ("Educação",         ["educacao", "escola", "ensino", "professor", "aluno", "bolsa de estudo"]),
    ("Sustentabilidade", ["sustentavel", "sustentabilidade", "ambiental", "climatic", "clima", "residuos", "reciclag", "energia limpa"]),
    ("Mobilidade",       ["mobilidade", "transporte", "transito", "ciclovia", "pedestre"]),
    ("Inovação",         ["inovacao", "cidades inteligentes", "smart cit", "tecnologia", "startup", "transformacao digital"]),
    # Convênios fica por último: atua como guarda-chuva para "editais/chamadas"
    # genéricos que não casaram com uma categoria mais específica acima.
    ("Convênios",        ["convenio", "chamamento", "chamada publica", "chamada aberta", "termo de fomento", "edital", "chamada"]),
])
