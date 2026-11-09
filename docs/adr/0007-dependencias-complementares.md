# ADR-0007: Dependências complementares da stack (Uvicorn, limits, pytest-cov)

- Status: Aceito (Rafael, 03/10/2026); emenda de 09/11/2026 aceita (Vinicius, 09/11/2026)
- Data: 2026-10-03
- Requisitos relacionados: RS-09, RNF-06; specs 001 (R1.1, R7.1) e 002 (R1.5)

## Contexto
A tabela de `steering/tech.md` fixa a stack, mas três peças necessárias não estavam nela:
- um servidor ASGI para rodar a API no container (a pesquisa da stack, §1, já citava o Uvicorn);
- o rate limit de `POST /auth/login` (002/R1.5), que o design da 002 atribui ao slowapi;
- a cobertura de testes no CI, que o workflow já chamava com `pytest --cov`.

## Decisão
Adicionar à stack, com a mesma regra de versão das demais (série fixa, `uv.lock` com a versão exata):

| Item | Versão | Uso |
|---|---|---|
| Uvicorn | 0.54.x | Servidor ASGI (`uvicorn --factory src.main:create_app`) |
| slowapi | 0.1.x | Rate limit por IP no login; entra no `pyproject.toml` na 002/T7 |
| pytest-cov | 7.x | Relatório de cobertura no CI (só desenvolvimento) |

## Consequências
- `steering/tech.md` passa a listar as três.
- O Uvicorn entra sem o extra `standard` (sem uvloop, httptools e watchfiles) para manter a imagem enxuta; desempenho do servidor não é gargalo no MVP.
- O slowapi tem manutenção modesta (0.1.10, junho de 2026). Se perder suporte, o limite vira uma dependência FastAPI própria sem mudar as rotas.

## Alternativas consideradas
- `fastapi[standard]`: traz o Uvicorn junto com pacotes que não usamos (CLI, templates, formulários, validação de e-mail).
- Hypercorn ou Granian: menos difundidos no ecossistema FastAPI.
- Rate limit próprio em memória: menos código externo, mas reimplementa janela de tempo e chave por IP que o slowapi já resolve e testa.
- CI sem cobertura: perde a métrica usada na revisão dos PRs.

## Emenda (09/11/2026, consolidação final; aceita, Vinicius, 09/11/2026, item V6 de `docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md`)
- **slowapi → limits.** O slowapi aplica o limite por decorador, com um `Limiter` global criado na importação do módulo, o que não combina com a raiz de composição do projeto (um app por `create_app`, um app por teste). A 002/T7 usa direto a biblioteca `limits` (o motor do slowapi), num limitador por app em `src/core/limite.py`, como este ADR já previa ("o limite vira uma dependência FastAPI própria"). As rotas não mudam.
- **pwdlib[argon2] e pyotp** entram no `pyproject.toml` na 002/T3 e T5, como a `steering/tech.md` prevê.
- Com o aceite, `steering/tech.md` passou a listar `limits 5.8.x` no lugar de `slowapi 0.1.x`. O título passou a citar `limits` (antes: "Uvicorn, slowapi, pytest-cov"). O texto original deste ADR, que escolheu o slowapi, fica como registro da decisão de 03/10/2026.
