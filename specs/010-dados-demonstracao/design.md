# 010 · Dados de demonstração · Design

- Status: Rascunho (revisão técnica de 09/11/2026 por ViniciusVbm na consolidação final; **aguarda aprovação do Rafael**. Implementada antes da aprovação por decisão do usuário; ver `docs/RELATORIO_VALIDACAO_FINAL.md` § Desvios)

## Formato
Arquivos YAML em `seeds/demo/` (`referencias.yaml`, `unidades.yaml`, `usuarios.yaml`), validados pelos mesmos schemas Pydantic da API. A carga passa pelos casos de uso (spec 006), garantindo que dados de seed respeitam as regras de validação e geram auditoria com o ator `sistema-seed`.

## Idempotência
Chave natural: CNES quando houver; senão (`district`, `name_normalized`). Upsert por chave.

## Comando
`sgs-admin seed demo [--reset]` (Typer). `--reset` só em `dev`/`test`. O compose de `dev` roda o seed após as migrações.

## Conversor da planilha
`scripts/converter_planilha_rede.py` (openpyxl) lê a aba `REDE_SAUDE_RECIFE_GEO`, classifica cada linha com regras explícitas e testáveis, grava YAML e um CSV de rejeitos. A planilha original fica fora do repositório (`.gitignore`), a menos que o cliente autorize.

## Estratégia de testes
- Integração: seed duas vezes → mesmas contagens; casos especiais presentes; recusa em `prod`.
- Unidade: classificador de linhas da planilha com linhas de exemplo sintéticas.

## Revisão técnica (09/11/2026; aguarda aprovação do Rafael)
- Formato: **JSON** em `seeds/demo/` (biblioteca padrão), no lugar de YAML: o PyYAML não está na `steering/tech.md`. Os registros são validados pelos mesmos schemas Pydantic da API.
- Comando: `argparse` (decisão da 002: o Typer não está na `steering/tech.md`).
- Ator da auditoria: o seed grava como sistema (`actor_user_id` nulo, `metadata.origem = "sgs-admin seed demo"`).
- Dados reaproveitados da `feat/003-interface-dashboard` (`src/resources/seeds/2_SQL_Insercao_Dados.sql`): nomes, endereços e telefones das 30 unidades e os 30 equipamentos, adaptados às referências da 0006 (distrito e tipo por código). Os CNES da 003 são fictícios e foram mantidos como fictícios.
- Domínios fechados (D1): distritos (8), áreas técnicas (4), tipos de unidade, de equipamento e de serviço, papéis (7) e permissões (17) ficam com a quantidade real, sem registros inventados; a justificativa fica em `docs/banco/30-tuplas.md`.
- Usuários: 30 fictícios, cobrindo os 7 papéis e os escopos. A senha não vai para o Git: vem de `SGS_SEED_SENHA` ou é gerada e mostrada uma vez no terminal.
- T3 (conversor da planilha): **fora desta entrega**. A planilha REDE_SAUDE_RECIFE_GEO não está disponível no repositório nem localmente.
