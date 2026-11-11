# Backup e restauração do banco (trilha de auditoria incluída)

Procedimento da spec 013 (R9.1 a R9.7; ADR-0013), com as decisões do proprietário (P1, P2, P6). São metas e procedimentos de um projeto acadêmico, não garantias de operação empresarial. Não há agendador.

## Política
| Item | Decisão |
|---|---|
| Retenção dos registros | `audit_log` e `db_change_log` com pelo menos 2 anos online (RS-05). Depois, arquivamento, sem descarte automático. Descarte futuro só com procedimento aprovado pelo dono e evento gravado na trilha |
| Frequência | Diário enquanto houver desenvolvimento ativo, mais um backup antes de migrações e de mudanças estruturais |
| Retenção dos backups | 7 diários, mais os backups dos marcos acadêmicos (preservados) |
| Local | Cópia principal em armazenamento local separado do banco e dos containers; segunda cópia em armazenamento privado na nuvem. **Nunca no Git.** As âncoras ficam à parte dos backups (`ancora-auditoria.md`) |
| RPO / RTO | 24 h / até 4 h, como metas. O ensaio mede o tempo real |
| Responsável | O proprietário, único responsável: operador de backup, verificador e guardião das cópias. Sem segregação de funções (risco aceito, P6) |
| Ensaio | Um ensaio completo antes da entrega final, em banco descartável e sem tocar em ambientes existentes |
| Base legal | **A validar** com o encarregado de dados e o jurídico da Secretaria: LGPD art. 37 (registro das operações de tratamento) e Marco Civil da Internet art. 15 (guarda de registros de acesso de aplicações, só como referência). Não há prazo legal universal assumido aqui |

## Backup
Os comandos rodam no container `db`, com o dono do banco, e gravam fora do volume do banco.

1. Gerar a âncora: `sgs-admin auditoria ancorar > ancora.json` (`ancora-auditoria.md`) e guardá-la à parte.
2. Exportar os papéis, sem senhas:

   ```bash
   docker compose -f docker/compose.yml exec -T db pg_dumpall -U sgs --roles-only --no-role-passwords > papeis.sql
   ```

3. Exportar o banco, com donos e ACLs (sem `--no-owner` nem `--no-privileges`):

   ```bash
   docker compose -f docker/compose.yml exec -T db pg_dump -U sgs -Fc -d sgs > sgs-AAAA-MM-DD.dump
   ```

4. Calcular o checksum e guardá-lo junto: `sha256sum sgs-AAAA-MM-DD.dump papeis.sql > sgs-AAAA-MM-DD.sha256`.
5. Copiar os arquivos para os dois locais da política. O dump tem dados pessoais e segredos cifrados (TOTP), então vai para local de acesso restrito.

## Restauração em banco novo
1. Conferir o checksum: `sha256sum -c sgs-AAAA-MM-DD.sha256`.
2. Subir um PostgreSQL 17 novo e vazio, sem ligação com o banco de origem.
3. Recriar os papéis com `psql -f papeis.sql`. Os papéis que já existirem dão aviso, não falha. Definir senhas novas para os logins (`sgs_api`), fora de qualquer repositório.
4. Criar o banco com o mesmo dono e restaurar:

   ```bash
   createdb sgs
   pg_restore --exit-on-error --single-transaction -d sgs sgs-AAAA-MM-DD.dump
   ```

5. Conferir a revisão das migrações: `SELECT version_num FROM alembic_version` deve ser a da origem. Nenhuma migração é aplicada como parte da restauração.
6. **Conferir o catálogo** (as consultas são as de `CATALOGO` em `tests/integration/audit/test_backup_restauracao.py`):
   - `ck_audit_log_origem_obrigatoria` presente com `convalidated = false`;
   - os triggers de `audit_log`, `db_change_log` (mãe e cada partição) e `trg_registry_change_log` presentes com `tgenabled = 'A'`;
   - funções SECURITY DEFINER com `search_path` fixo;
   - `sgs_app` com SELECT e INSERT no `audit_log`, só SELECT no `db_change_log`, e nada mais;
   - lista de partições igual à da origem.
7. **Verificar a cadeia** com a última âncora anterior ao backup, sem precisar subir a API:

   ```bash
   DATABASE_URL=<banco restaurado> uv run sgs-admin auditoria verificar --ancora ancora.json
   ```

   O esperado é código 0, com `integra`, `cabeca_confere`, `cadeia_confere` e `ancora_confere` verdadeiros.
8. As âncoras posteriores ao backup não vão conferir. Isso marca a janela de perda: registrar como incidente de perda de dados, não como adulteração.
9. Gerar uma âncora nova do banco restaurado antes de colocá-lo em uso.

## Evidências
Cada restauração, real ou de ensaio, deixa um registro em `evidencias/` com:
- data, passos e horários;
- checksum e tamanho do backup;
- a âncora usada;
- o JSON da verificação;
- a saída da conferência do catálogo;
- a duração medida (comparada com o RTO);
- quem executou e quem conferiu.

Nunca guardar ali dump, senha, token ou dado pessoal.

**Ensaio de 11/11/2026:** `evidencias/ensaio-restauracao-2026-11-11.json`, gerado por `tests/integration/audit/test_backup_restauracao.py::test_restauracao_preserva_cadeia_ancora_e_protecoes`, com dois PostgreSQL 17 descartáveis (origem e um servidor novo):
- catálogo restaurado igual ao da origem;
- constraint ainda `NOT VALID`;
- eventos anteriores à 013 íntegros;
- INSERT sem tipo recusado;
- cadeia, cabeça e âncora conferindo.

Para repetir:

```bash
SGS_EVIDENCIAS_DIR=docs/operacao/evidencias env -u SGS_TEST_DATABASE_URL \
  uv run pytest -m slow tests/integration/audit/test_backup_restauracao.py
```

## Conferência dos requisitos da T15
| Requisito | Comportamento | Evidência | Situação |
|---|---|---|---|
| R5.8 (procedimento da âncora) | Geração, guarda em duas cópias, acesso, histórico, uso, recuperação e divergência descritos | `ancora-auditoria.md`; CLI testada em `test_sgs_admin_ancorar.py` e `test_sgs_admin_verificar.py` | Atendido como procedimento. A execução é humana e não há segregação de funções (P6) |
| R9.3 (backup e restauração documentados) | Formato, frequência, local, responsável, RPO/RTO, restauração e conferência do catálogo e da cadeia | Esta página; ADR-0013 | Atendido. RPO/RTO são metas, não medidas de produção |
| R9.5 (sem prazo legal universal) | Referências legais como pontos a validar com o encarregado de dados | § Política, linha "Base legal" | Atendido. A validação jurídica fica pendente com a Secretaria |
| R9.6 (evidências) | Modelo de evidências e registro do ensaio, sem dado sensível | § Evidências; `evidencias/ensaio-restauracao-2026-11-11.json` | Atendido para o ensaio. A restauração real, quando houver, segue o mesmo modelo |
