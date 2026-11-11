# Âncora externa da trilha de auditoria

Procedimento manual da spec 013 (R5.4, R5.7 a R5.10; ADR-0012). Valem as decisões do proprietário (P1, P2, P6).

## O que é
Um JSON de uma linha, versão 1, que fixa um ponto da cadeia:

```json
{"versao": 1, "cadeia_id": "<hash do primeiro evento>", "id": 1234, "hash": "<hash do evento 1234>",
 "total": 1234, "instante": "2026-11-11T18:00:00.000000Z", "banco": "sgs"}
```

- `cadeia_id` identifica a cadeia. Ele sobrevive à restauração em outro servidor e é diferente em bancos com o mesmo nome.
- `banco` é só informativo.
- A âncora não contém dado pessoal.

## Gerar
```bash
docker compose -f docker/compose.yml exec -T api sgs-admin auditoria ancorar > ancora.json
```

- Só lê o banco, numa transação `REPEATABLE READ, READ ONLY`, e não grava nada (`tests/integration/tools/test_sgs_admin_ancorar.py`).
- Códigos de saída:
  - 0: âncora emitida;
  - 1: cadeia divergente, sem âncora;
  - 2: cadeia vazia.
- **Quando gerar:**
  - todo dia em que houver atividade relevante;
  - antes e depois de migrações e de mudanças estruturais;
  - imediatamente antes de cada backup.

## Guardar
| Regra | Como |
|---|---|
| Duas cópias, separadas dos backups | Uma local, fora do banco e dos containers. Outra num armazenamento privado na nuvem, independente do ambiente local |
| Um arquivo por âncora | `ancoras/AAAA/MM/AAAA-MM-DDTHHMMSSZ.json` |
| Histórico | Nunca sobrescrever nem apagar âncoras antigas: são elas que acusam a reescrita de períodos antigos |
| **Não vale** | O mesmo servidor ou volume do banco, o mesmo banco (inclusive outra tabela), o servidor da API, o backup do banco como única cópia, o repositório Git do projeto |
| Acesso | Só o proprietário escreve e lê. **Não há segregação de funções:** a mesma pessoa administra o banco e guarda as âncoras. É risco aceito do projeto acadêmico (P6), não uma separação simulada |

## Verificar
- Pela tela: `#/cadeia`, preenchendo `cadeia_id`, `id` e `hash`.
- Direto no banco, sem a API e sem gravar nada:

  ```bash
  docker compose -f docker/compose.yml cp ancora.json api:/tmp/ancora.json
  docker compose -f docker/compose.yml exec -T api sgs-admin auditoria verificar --ancora /tmp/ancora.json
  ```

  Fora do container, o mesmo comando roda com `uv run sgs-admin …` e `DATABASE_URL` apontando para o banco a verificar.

- Códigos de saída:
  - 0: íntegra (cadeia, cabeça e âncora conferem);
  - 1: divergente;
  - 2: âncora ilegível, de outra versão ou com campo inválido.
- **Rotina:** verificar com a âncora mais recente; antes da entrega final, verificar também com uma âncora antiga.

## Recuperar
- **Perda da cópia local:** usar a cópia externa, e vice-versa.
- **Perda das duas:** verificar a cadeia sem âncora. Se estiver íntegra, gerar uma âncora nova na hora e registrar que a proteção contra reescrita recomeça a partir dela.
- **Depois de restaurar o banco:** verificar com a última âncora anterior ao backup restaurado (`backup-restauracao.md`). As âncoras posteriores não vão conferir; isso marca a janela de perda e é registrado como incidente de perda de dados, não como adulteração.

## Divergência
1. Não "corrigir" a cadeia nem reescrever eventos.
2. Fazer um backup imediato do estado atual como evidência.
3. Registrar o resultado da verificação (JSON da CLI) e o evento divergente.
4. Comunicar o dono e, se houver dado pessoal envolvido, o encarregado de dados.

## Rotina automatizada (fora do escopo)
A geração e a guarda são manuais nesta entrega. Uma rotina automatizada, com spec própria, precisaria de:
- execução agendada fora do servidor do banco;
- publicação num destino com credencial só de acréscimo, independente do banco;
- alerta quando falhar;
- opcionalmente, carimbo de tempo de terceiro (RFC 3161).
