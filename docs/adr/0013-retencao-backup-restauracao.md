# ADR-0013: Retenção da trilha, backup e restauração

- Status: Aceito (Vinicius, proprietário, 11/11/2026; spec 013 aprovada)
- Data: 2026-11-11
- Requisitos relacionados: RS-05; spec 013 (R9.1 a R9.7)

## Contexto
A retenção de 2 anos (RS-05) só existia no papel (`steering/security.md`, `docs/architecture/modelo-dados.md`). Não havia procedimento de backup nem prova de que uma restauração preservaria a cadeia, a constraint `NOT VALID` da 013 e os triggers de imutabilidade. O projeto é acadêmico e tem um único responsável operacional.

## Decisão
- **Retenção:** pelo menos 2 anos online para `audit_log` e `db_change_log`. Depois disso, arquivamento, sem descarte automático. Um descarte futuro depende de um procedimento aprovado pelo dono e grava evento na trilha. Esta decisão não implementa descarte.
- **Backup:** `pg_dump -Fc` do banco, com donos e ACLs, mais `pg_dumpall --roles-only --no-role-passwords`, e o `sha256sum` de cada arquivo.
  - Diário enquanto houver desenvolvimento ativo, e um extra antes de migrações e de mudanças estruturais.
  - Retenção de 7 backups diários, mais os backups dos marcos acadêmicos.
  - Cópia principal local, separada do banco e dos containers; segunda cópia em armazenamento privado na nuvem; nunca no Git.
- **Metas:** RPO de 24 h e RTO de até 4 h, como metas acadêmicas, não como garantias empresariais.
- **Restauração e ensaio:** restauração num servidor novo, conferida pelo catálogo e por `sgs-admin auditoria verificar --ancora`. Um ensaio completo antes da entrega final, com evidências em `docs/operacao/evidencias/`.
- **Responsável:** um só, o proprietário, que acumula operador de backup, operador de âncora, verificador e guardião das cópias. A falta de segregação de funções é risco aceito.
- **Sem agendador** nem serviço de backup automatizado.

O procedimento está em `docs/operacao/backup-restauracao.md`.

## Consequências
- O ensaio automatizado (`tests/integration/audit/test_backup_restauracao.py`) restaura num segundo PostgreSQL 17 descartável e comprova:
  - catálogo igual ao da origem;
  - constraint ainda `NOT VALID`;
  - eventos antigos íntegros;
  - INSERT sem tipo recusado;
  - cadeia, cabeça e âncora conferindo.
- A execução depende de disciplina humana. Sem agendador, um backup esquecido aumenta a perda de dados além do RPO.
- O dump tem dados pessoais e segredos cifrados (TOTP), por isso é guardado com acesso restrito.

## Alternativas consideradas
- **Backup físico contínuo (WAL/PITR) ou réplica:** dariam RPO menor, mas exigem infraestrutura e operação além do escopo acadêmico.
- **Descarte automático depois de 2 anos:** recusado. Apagaria evidência sem decisão humana, e a base legal precisa ser validada com o encarregado de dados (LGPD art. 37; Marco Civil art. 15 apenas como referência).
