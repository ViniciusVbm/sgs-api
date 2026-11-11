# ADR-0012: Âncora externa sem chave e modelo de confiança da trilha

- Status: Aceito (Vinicius, proprietário, 11/11/2026; spec 013 aprovada)
- Data: 2026-11-11
- Requisitos relacionados: RF-08, RS-05; spec 013 (R5.1 a R5.12, R6.6 a R6.8)

## Contexto
A trilha (`audit_log`, spec 001) é encadeada por SHA-256: cada evento guarda `hash = SHA-256(prev_hash || conteúdo canônico)`. Isso detecta alteração e remoção no meio. Não detectava a remoção dos últimos eventos, e nada protege contra quem controla o banco como dono ou superusuário, que pode reescrever a cadeia inteira e a cabeça (`audit_chain_head`) de forma coerente.

## Decisão
1. **Cabeça da cadeia na verificação.** A verificação lê a cabeça e todos os eventos numa única transação `REPEATABLE READ, READ ONLY` e compara o hash do último evento com `audit_chain_head.last_hash` (spec 013, T8).
2. **Âncora externa, sem chave criptográfica.** A âncora é um JSON (versão 1) com:
   - `cadeia_id`, o hash do primeiro evento;
   - `id` e `hash` do último evento verificado;
   - total de eventos, instante e nome do banco.

   Ela é gerada por `sgs-admin auditoria ancorar` e guardada fora do banco (`docs/operacao/ancora-auditoria.md`). A verificação, pela API ou por `sgs-admin auditoria verificar --ancora`, confere se a cadeia é a mesma e se o evento ancorado ainda tem o hash guardado (T9).
3. **`ENABLE ALWAYS`** nos triggers de imutabilidade do `audit_log` e do `db_change_log` e no `trg_registry_change_log`. Assim, `session_replication_role = replica` não os desliga (T10).
4. **Modelo de confiança declarado**, sem prometer imutabilidade absoluta:

| Quem | O que a solução garante |
|---|---|
| Cliente, usuário autenticado, contêiner vizinho | Não escolhe o IP gravado (proxy `/32`) nem altera eventos |
| Processo da API comprometido (`sgs_app`) | Não altera nem apaga eventos; pode **inserir** eventos falsos encadeados (não detectável) |
| Dono das tabelas ou superusuário | **Só detecção**: a cabeça acusa um corte simples no fim; a âncora acusa a reescrita do que é anterior a ela. DETACH ou DROP de partição e `DISABLE TRIGGER` continuam possíveis |
| Quem controla o banco e as âncoras | Nada é garantido. No projeto, o proprietário é o único responsável pelas duas coisas: risco aceito (spec 013, P6) |

## Consequências
- Remoção no fim, no meio, no começo e alteração de qualquer campo do conteúdo canônico são detectadas. Os testes estão em `tests/integration/audit/test_adulteracao.py`.
- A âncora só protege se for guardada fora do servidor do banco e do servidor da API. Guardá-la no mesmo servidor, no mesmo banco ou só dentro do backup não vale como evidência independente.
- A verificação offline pela CLI não depende da API de produção e não grava nada, então serve para conferir uma cópia restaurada.
- Ficam como trabalho futuro, com spec própria:
  - uma rotina automatizada que publique a âncora num destino só de acréscimo, com alerta de falha;
  - um carimbo de tempo de terceiro (RFC 3161);
  - HMAC com gestão de chaves.

## Alternativas consideradas
- **HMAC com chave:** autenticaria o hash, mas exigiria gerar, guardar, girar e recuperar a chave e versionar o algoritmo por linha. Isso é desproporcional ao escopo acadêmico, e quem tem o banco e a chave reescreve tudo do mesmo jeito.
- **Event trigger contra DROP/DETACH:** exige superusuário para ser criado e pode ser desligado por superusuário. Não adotado (P5).
- **Só a cabeça, sem âncora:** um superusuário ajusta a cabeça junto com a cadeia, e o corte passa despercebido.
