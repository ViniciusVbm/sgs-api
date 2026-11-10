# 010 · Dados de demonstração · Design

- Status: Aprovado (Vinicius, 09/11/2026; sem revisão por pares, pela exceção pontual V7 de `steering/sdd-workflow.md`). Histórico: autoria original de rafareloM (03/10/2026); revisão técnica de ViniciusVbm (09/11/2026); implementada antes da aprovação, por decisão do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9); aprovação registrada na regularização (`docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 7, item V3)

## Formato
Arquivos JSON em `seeds/demo/` (`referencias.json`, `unidades.json`, `usuarios.json`, `vinculos.json`), lidos com a biblioteca padrão e validados pelos mesmos schemas Pydantic da API. A carga passa pelos casos de uso (spec 006), então os dados de seed respeitam as regras de validação e geram auditoria com o ator sistema (`actor_user_id` nulo, `metadata.origem = "sgs-admin seed demo"`).

## Idempotência
Chave natural: código nas referências; CNES quando houver, senão (`district`, `name_normalized`), nas unidades; unidade + nome nos vínculos; `username` nos usuários. O que já existe é pulado.

## Comando
`sgs-admin seed demo` (`argparse`, `src/tools/sgs_admin.py`). Recusado em `prod` (R1.6). É executado à mão depois das migrações (`docs/instalacao.md`); o compose não o roda sozinho e não há `--reset` (para recomeçar, recria-se o banco).

Versão original deste design (YAML, Typer, ator `sistema-seed`, `--reset`, seed no compose): commit `7b63009`, substituída em 09/11/2026 (item V3).

## Conversor da planilha
`scripts/converter_planilha_rede.py` (openpyxl) lê a aba `REDE_SAUDE_RECIFE_GEO`, classifica cada linha com regras explícitas e testáveis, grava YAML e um CSV de rejeitos. A planilha original fica fora do repositório (`.gitignore`), a menos que o cliente autorize.

## Estratégia de testes
- Integração: seed duas vezes → mesmas contagens; casos especiais presentes; recusa em `prod`.
- Unidade: classificador de linhas da planilha com linhas de exemplo sintéticas.

## Revisão técnica (09/11/2026; aprovada, Vinicius, 09/11/2026, item V3)
- Formato: **JSON** em `seeds/demo/` (biblioteca padrão), no lugar de YAML: o PyYAML não está na `steering/tech.md`. Os registros são validados pelos mesmos schemas Pydantic da API.
- Comando: `argparse` (decisão da 002: o Typer não está na `steering/tech.md`).
- Ator da auditoria: o seed grava como sistema (`actor_user_id` nulo, `metadata.origem = "sgs-admin seed demo"`).
- Dados reaproveitados da `feat/003-interface-dashboard` (`src/resources/seeds/2_SQL_Insercao_Dados.sql`): nomes, endereços e telefones das 30 unidades e os 30 equipamentos, adaptados às referências da 0006 (distrito e tipo por código). Os CNES da 003 são fictícios e foram mantidos como fictícios.
- Domínios fechados (D1): distritos (8), áreas técnicas (4), tipos de unidade, de equipamento e de serviço, papéis (7) e permissões (17) ficam com a quantidade real, sem registros inventados; a justificativa fica em `docs/banco/06-trinta-tuplas.md`.
- Usuários: 30 fictícios, cobrindo os 7 papéis e os escopos. A senha não vai para o Git: vem de `SGS_SEED_SENHA` ou é gerada e mostrada uma vez no terminal.
- T3 (conversor da planilha): **fora desta entrega**. A planilha REDE_SAUDE_RECIFE_GEO não está disponível no repositório nem localmente.

## Divergências da auditoria de 09/11/2026 e como foram resolvidas
Levantadas em `docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 3.3 e decididas pelo dono em 09/11/2026 (item V3).
- **D010-1:** resolvida. Formato e Comando descrevem JSON e `argparse`.
- **D010-2:** resolvida. `--reset` saiu do design.
- **D010-3:** resolvida. O seed automático no compose saiu do design.
- ~~**D010-4** (R1.4)~~: retirada na revisão técnica final (09/11/2026). Não é divergência: o 2FA não depende do seed. Fora de `dev`, o login exige o cadastro do segundo fator (`src/modules/identity/application/login.py`), e o `Settings` recusa `MFA_OBRIGATORIO=false` fora de `dev` (`src/core/config.py`; `tests/unit/core/test_config.py::test_mfa_so_pode_ser_desligado_em_dev`).
- **D010-5:** documental. O "Pronto quando" da T1 cita `tests/unit/seeds/test_yaml_valido.py`, que não existe desde a troca de YAML por JSON; a prova é `tests/integration/tools/test_seed_demo.py`.
- **D010-6** (revisão de 09/11/2026, agente; aguarda o dono): documental, aguarda o dono. A seção "Conversor da planilha" ainda diz que o script grava YAML, mas a revisão técnica trocou o seed para JSON; o caminho `scripts/` foge do padrão dos comandos (`src/tools/`); e o `openpyxl` não está no `pyproject.toml` (se o cliente mandar CSV, a biblioteca padrão basta). Proposta: JSON no formato de `seeds/demo/`, comando em `src/tools/`, leitor de CSV ou de XLSX conforme o arquivo que chegar. Como o design está aprovado, a correção do texto volta para o dono aprovar.
