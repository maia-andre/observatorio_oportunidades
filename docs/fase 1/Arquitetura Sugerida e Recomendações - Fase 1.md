# Arquitetura Sugerida e Recomendações - Fase 1

Com base na investigação da Fase 0, apresentamos a proposta para a evolução do Observatório de Oportunidades Institucionais.

## 1. Arquitetura de Coleta Sugerida

A arquitetura deve ser modular e baseada em "Fetchers" especializados por nível de complexidade:

### Componentes Principais:
1.  **Scheduler**: Orquestrador (ex: GitHub Actions ou Cron) que dispara as coletas em intervalos definidos.
2.  **Fetcher Nível A (RSS)**: Script leve em Python utilizando `feedparser`.
3.  **Fetcher Nível B (API/JSON)**: Módulos específicos para consumir a API do Portal da Transparência e outros endpoints identificados.
4.  **Fetcher Nível C (Scraper Estático)**: Utilização de `BeautifulSoup` com tratamento de headers para evitar bloqueios.
5.  **Fetcher Nível D (Browser Automation)**: Instância de `Playwright` apenas para fontes críticas como PNCP e DOU.
6.  **Normalizador**: Camada que transforma os dados brutos de diferentes fontes em um esquema único (Título, URL, Data, Descrição).
7.  **Banco de Dados**: PostgreSQL para persistência e histórico.

## 2. Lista Priorizada para Automação (Fase 1)

Prioridade baseada em Facilidade de Implementação vs. Valor da Oportunidade:

1.  **Portal da Transparência (API)**: Alto valor, dados estruturados.
2.  **Capta & Prosas**: Agregadores que já consolidam centenas de editais.
3.  **Transferegov.br (RSS)**: Principal fonte de recursos federais.
4.  **ENAP & Prêmio Espírito Público**: Foco em inovação e reconhecimento.
5.  **Sites WordPress (ABIPEM, Santa Isabel, etc.)**: Coleta via RSS é imediata.

## 3. Recomendações de Implementação

*   **Deduplicação**: Implementar um hash baseado na URL e Título para evitar duplicidade de oportunidades encontradas em diferentes agregadores (ex: Capta e Prosas).
*   **Tratamento de Erros SSL**: Para sites com certificados expirados ou problemáticos (como CPB e PNCQ), utilizar `verify=False` nas requisições `requests`, mas com cautela.
*   **User-Agents Dinâmicos**: Utilizar uma lista de User-Agents reais para minimizar bloqueios em sites como CIEE e portais governamentais.
*   **Monitoramento de Sitemaps**: Para sites sem RSS, o monitoramento de mudanças no `sitemap.xml` é uma alternativa mais eficiente que o scraping total da página.

## 4. Próximos Passos (Fase 1)

*   Desenvolver o **Normalizador de Dados**.
*   Configurar o **PostgreSQL** com a estrutura mínima definida na Fase 0.
*   Criar os primeiros 5 **Fetchers** da lista prioritária.
*   Implementar um **Dashboard de Monitoramento** para visualizar as oportunidades capturadas em tempo real.
