# Relatório Técnico por Site - Fase 0

Este relatório detalha a investigação técnica realizada em cada uma das fontes identificadas para o Observatório de Oportunidades Institucionais.

## 1. Fontes Nível A (RSS Disponível)
Estes sites são os mais fáceis de monitorar, permitindo uma coleta automatizada via parser de XML.

| Site | RSS URL | Tecnologia |
| :--- | :--- | :--- |
| ABIPEM | https://www.abipem.org.br/feed | WordPress |
| BFUCA UNESCO | https://bfucaunesco.org.br/feed | WordPress |
| ICISMEP | https://icismep.mg.gov.br/feed | WordPress |
| Estônia Hub | https://estoniahub.com.br/feed | WordPress |
| Transferegov.br | https://www.gov.br/rss.xml | Gov.br |
| Santa Isabel | https://site.santaisabel.sp.gov.br/feed | WordPress |
| ABNT | https://abnt.org.br/feed | WordPress |
| Capta | https://capta.org.br/feed | WordPress |
| CENPEC | https://www.cenpec.org.br/feed | WordPress |
| Prêmio Espírito Público | https://premioespiritopublico.org.br/feed | WordPress |

## 2. Fontes Nível B (API/JSON ou Sitemap Robusto)
Sites que possuem estrutura de dados acessível via endpoints ou sitemaps detalhados.

| Site | Estratégia | Tecnologia |
| :--- | :--- | :--- |
| Portal da Transparência | API Pública (JSON) | Custom |
| ONA | Sitemap / JSON Detectado | Next.js |
| Agência SP | JSON Detectado | WordPress |
| ENAP | Sitemap / Gov.br | Gov.br |
| IQG | Sitemap / JSON Detectado | Next.js |
| Ranking Municípios | JSON Detectado | Gov.br |
| Caixa Sustentabilidade | Sitemap / Gov.br | Gov.br |
| Conexão Inovação | Sitemap / JSON Detectado | Next.js |
| Google Education | Sitemap | Portal Próprio |
| Comunicação SP | Sitemap | Gov.br |
| Conasems | JSON Detectado | WordPress |

## 3. Fontes Nível C (HTML Estático / BeautifulSoup)
Sites que requerem parsing de HTML simples via Requests + BeautifulSoup.

| Site | Tecnologia |
| :--- | :--- |
| Radar Transparência | Next.js |
| Tree Cities | Next.js |
| Certificadora Social | Next.js |
| Congresso Nacional | Portal Próprio |
| Prosas | Portal Próprio |
| Prêmio Quality | Next.js |
| OBMEP | Next.js |

## 4. Fontes com Erros Técnicos ou Nível D (Dinâmico)
Estes sites apresentaram falhas de conexão, timeout ou exigem renderização dinâmica (Playwright).

| Site | Erro/Observação |
| :--- | :--- |
| PNCP | Timeout (Requer Playwright) |
| CPB | Erro de Certificado SSL |
| Diário Oficial (DOU) | Timeout (Requer Playwright/API específica) |
| MAPA (Agricultura) | Timeout |
| PNCQ | Erro de Certificado SSL |
| CIEE | Erro 403 (Proteção Anti-Bot) |
| WABA | Erro 406 |
| Ciudades Educadoras | Erro de Certificado SSL |

---
*Nota: A viabilidade técnica da Fase 0 é de 63.16%, superando o critério de sucesso de 50%.*
