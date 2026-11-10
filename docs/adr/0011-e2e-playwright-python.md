# ADR-0011: Playwright com Python para os testes end-to-end do frontend

- Status: Proposto
- Decisão do dono da spec 012: DF11, Vinicius, 09/11/2026. A **aceitação deste ADR pelo grupo** continua pendente.
- Data: 2026-11-09
- Requisitos relacionados: spec 012 (estratégia de testes, T2, T4 a T14); Entrega 11 de Projetos (testes de aceitação)

## Contexto
O critério de conclusão da integração exige testes end-to-end no navegador (login com 2FA, perfis, CRUD, responsividade, XSS). O projeto já testa em Python (pytest, testcontainers) e não tem Node (ADR-0010). Testes só da API não verificam a interface.

## Decisão
Os testes E2E do front usam o **Playwright para Python** (`pytest-playwright`), como dependência de **desenvolvimento**:
- ficam em `tests/e2e_front/`, marcados `slow`;
- rodam contra o compose com `sgs-admin seed demo`;
- geram o código TOTP com `pyotp`, que já é dependência.

## Consequências
- **Mais fácil:**
  - um só runner (pytest) e uma só linguagem;
  - capturas de tela para a paridade visual;
  - leitura do console para violações de CSP.
- **Mais difícil:**
  - o CI precisa instalar o navegador (`playwright install --with-deps chromium`), uns 150 MB e mais tempo de job;
  - os E2E são mais lentos e, por isso, ficam fora do `make check`.
- **A fazer:**
  - incluir `pytest-playwright` no grupo dev do `pyproject.toml`, com versão fixada, e na `steering/tech.md`;
  - criar o passo no CI;
  - documentar em `docs/instalacao.md`.

## Alternativas consideradas
- Playwright ou Cypress em Node: trazem npm, contra o ADR-0010.
- Selenium: mais verboso e mais frágil para esperas.
- Nenhum E2E de navegador: não atende ao critério de conclusão.
