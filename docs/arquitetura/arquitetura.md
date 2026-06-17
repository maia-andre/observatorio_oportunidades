# Arquitetura do Observatório de Oportunidades Institucionais

Este documento serve como referência central para a arquitetura tecnológica e a infraestrutura do projeto. Ele descreve o estado atual do sistema e deve ser atualizado progressivamente à medida que avançamos pelas fases (do MVP até o Centro de Inteligência).

---

## Fase 0: MVP de Descoberta

O foco da **Fase 0** foi estabelecer uma fundação estável e autônoma, validando o fluxo básico de coleta, persistência e exibição. Foi projetada para evitar overengineering, priorizando a estabilidade da orquestração dos dados.

### 1. Stack Tecnológico (MVP)
- **Banco de Dados:** SQLite (arquivo local em `database/observatorio.db`) como **padrão da Fase 0** — **não requer Docker**, o que simplifica e padroniza o setup entre as máquinas dos desenvolvedores. O PostgreSQL continua suportado (basta definir a variável `DATABASE_URL`) e permanece como alvo para as fases posteriores; o `docker-compose.yml` para subir o Postgres é mantido como opcional.
- **ORM e Validação:** `SQLModel` (que envelopa o SQLAlchemy e o Pydantic), garantindo que a declaração do banco e a validação das classes ocorram em um único ponto, mantendo o código enxuto.
- **Backend/Servidor Web:** `FastAPI`.
- **Frontend (Painel Simples):** Integrado ao backend usando templates `Jinja2` e estilizado via CDN com `PicoCSS`. Para a Fase 0, a renderização Server-Side HTML elimina a necessidade de subir um ambiente Node/Next.js complexo apenas para validação.
- **Extração de Dados:** 
  - Scripts isolados baseados em `requests`, `feedparser` (para RSS Nível A) e `BeautifulSoup` com `lxml` (para manipulação de XML e Sitemaps).

### 2. Estratégia dos Coletores
Os coletores (dentro da pasta `collectors/`) foram desenhados como **scripts Python autônomos**. Essa decisão arquitetural permite que, em ambiente de produção, eles sejam disparados por agendadores simples de sistema (cronjobs, GitHub Actions, AWS EventBridge) sem sobrecarregar a memória do servidor da API Web (FastAPI).

### 3. Modelagem de Dados Inicial (`Opportunity`)
O banco foi planejado com o mínimo de metadados exigidos pela fase. A estratégia primária de **deduplicação** para evitar redundância nas coletas diárias é a criação de uma restrição única (Unique Constraint) no campo `url`.

```python
# Tabela: opportunity
id: int (PK)
title: str
description: str (Nullable)
url: str (Unique Index)
published_date: datetime (Nullable)
source: str
collected_at: datetime
```

---

## Como Rodar o Projeto

Siga os passos abaixo para levantar a infraestrutura e simular o povoamento do banco de dados na sua máquina.

### Pré-requisitos
- Python 3.10+
- (Opcional) Docker e Docker Compose — **apenas** se optar por usar PostgreSQL em vez do SQLite padrão

### Passo a Passo

1. **Banco de Dados (SQLite — padrão):**
   Nenhuma ação necessária. O arquivo `database/observatorio.db` é criado automaticamente no primeiro boot do servidor.

   > **Opcional (PostgreSQL):** se preferir Postgres, suba o container e aponte a variável de ambiente antes de iniciar o servidor e os coletores:
   > ```bash
   > docker-compose up -d
   > # Windows (PowerShell): $env:DATABASE_URL = "postgresql://observatorio:observatorio_password@localhost:5432/observatorio_db"
   > # Linux/Mac:            export DATABASE_URL="postgresql://observatorio:observatorio_password@localhost:5432/observatorio_db"
   > ```

2. **Configurar o Ambiente Virtual (Python):**
   ```bash
   python -m venv venv
   
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. **Instalar as Dependências:**
   Com o ambiente ativado, instale as bibliotecas base:
   ```bash
   pip install -r requirements.txt
   ```

4. **Iniciar o Servidor Web (Painel):**
   Levante a aplicação FastAPI (o banco e as tabelas serão criados automaticamente no primeiro boot).
   Mantenha esta aba do terminal aberta.
   ```bash
   uvicorn backend.main:app --reload
   ```
   *Navegue até `http://localhost:8000` para visualizar a interface (ainda sem dados).*

5. **Executar a Coleta de Dados:**
   Abra uma nova aba no terminal, certifique-se de ativar o ambiente virtual (`venv\Scripts\activate`) e execute os disparos autônomos:
   ```bash
   python collectors/rss/rss_collector.py
   python collectors/api/api_collector.py
   ```

6. **Validação Final:**
   Retorne ao navegador (`http://localhost:8000`) e atualize a página. A tabela HTML processada pelo Jinja2 exibirá as oportunidades capturadas em tempo real.
