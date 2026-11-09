# Modelo conceitual (entidade-relacionamento)

Notação de pés de galinha (Mermaid). Atributos principais; o detalhe de cada coluna está no [dicionário](04-dicionario-dados.md).

```mermaid
erDiagram
    DISTRITO_SANITARIO ||--o{ UNIDADE_DE_SAUDE : "contém"
    AREA_TECNICA ||--o{ TIPO_DE_UNIDADE : "agrupa"
    TIPO_DE_UNIDADE ||--o{ UNIDADE_DE_SAUDE : "classifica"
    UNIDADE_DE_SAUDE ||--o{ EQUIPAMENTO_DE_SAUDE : "contém (0..n)"
    TIPO_DE_EQUIPAMENTO ||--o{ EQUIPAMENTO_DE_SAUDE : "classifica"
    UNIDADE_DE_SAUDE ||--o{ SERVICO : "oferta (0..n)"
    EQUIPAMENTO_DE_SAUDE |o--o{ SERVICO : "abriga (opcional)"
    TIPO_DE_SERVICO ||--o{ SERVICO : "classifica"
    USUARIO ||--o{ ATRIBUICAO : "recebe"
    PAPEL ||--o{ ATRIBUICAO : "é concedido em"
    PAPEL }o--o{ PERMISSAO : "concede (com escopo máximo)"
    USUARIO ||--o{ SESSAO : "abre"
    SESSAO ||--o{ REFRESH_TOKEN : "renova"
    USUARIO |o--o{ EVENTO_DE_AUDITORIA : "é autor de"
    UNIDADE_DE_SAUDE ||--o{ EVENTO_DE_AUDITORIA : "tem histórico"
    UNIDADE_DE_SAUDE ||--o{ REGISTRO_DO_LOG_DO_BANCO : "escrita registrada"

    UNIDADE_DE_SAUDE { uuid id PK
        string nome
        string cnes "único, opcional"
        string status
        int versao }
    EQUIPAMENTO_DE_SAUDE { uuid id PK
        string nome
        int quantidade }
    SERVICO { uuid id PK
        string nome
        bool no_cnes }
    ATRIBUICAO { string escopo_tipo
        string escopo_id
        date valido_ate }
    EVENTO_DE_AUDITORIA { bigint id PK
        datetime quando
        string acao
        json mudancas
        string hash }
```

Regras de cardinalidade e participação:
- Unidade → distrito e unidade → tipo: obrigatórias (1, N).
- Equipamento → unidade: **opcional**. Equipamento sem unidade é a UTI móvel.
- Serviço → unidade: **opcional** (serviço solto). Serviço → equipamento: opcional, e precisa ser da mesma unidade.
- Papel × permissão: N:N com atributo (escopo máximo). Usuário × papel: N:N com atributos (escopo, validade, origem), materializado em `ATRIBUICAO`.
- Evento de auditoria: entidade fraca da trilha, encadeada pelo hash do evento anterior.
