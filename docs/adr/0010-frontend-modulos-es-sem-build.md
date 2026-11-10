# ADR-0010: Frontend no mesmo repositório, em JavaScript com módulos ES, sem framework e sem build

- Status: Proposto
- Decisão de direção do time sobre a integração: registrada em `docs/PLANO_INTEGRACAO_FRONTEND.md`. A **aceitação formal deste ADR** continua pendente.
- Data: 2026-11-09
- Requisitos relacionados: spec 012 (R1, R3, R15); RF-01, RF-06, RF-09, RS-01, RS-02

## Contexto
O grupo tem um protótipo navegável em HTML (página única, 1.935 linhas, JavaScript puro, sem dependências), validado com o cliente. A spec 011 previa o front num repositório separado; hoje o repositório publicado é único e o CI já sobe a API com o compose. As forças em jogo:
- preservar a interface aprovada;
- não introduzir uma segunda cadeia de ferramentas (Node, npm, empacotador) num grupo pequeno e com prazos (21/11);
- servir o front no mesmo domínio, para o cookie de refresh `SameSite=Strict` e uma CSP restritiva;
- manter as regras de acesso no backend.

## Decisão
O front fica em `frontend/app/` neste repositório:
- é JavaScript em **módulos ES nativos do navegador**, sem framework, sem empacotador e sem dependência npm;
- é servido pelo Caddy (`file_server`) no mesmo domínio da API, com CSP.

## Consequências
- **Mais fácil:**
  - aproveitar o protótipo quase como está;
  - nada para instalar além do que o projeto já tem;
  - deploy num passo (o compose);
  - sem CORS.
- **Mais difícil:**
  - sem tipagem nem minificação;
  - a organização em módulos e o escape (`html\`\``) dependem de disciplina e de um teste estático;
  - estilos inline do protótipo pedem uma exceção temporária de CSP (`style-src 'unsafe-inline'`).
- **A fazer:**
  - mudar o `Caddyfile` e o compose (volume do front);
  - teste estático dos `.js`;
  - atualizar o `steering/structure.md` com a pasta `frontend/`.
- **Substitui:** a frase da spec 011 "Interface (front-end): fica para spec própria, no repositório do front".

## Alternativas consideradas
- React, Vue ou Svelte com Vite: exigiriam Node, npm e build no CI e a reescrita do protótipo.
- Repositório separado: precisaria de CORS, de domínio ou cookie entre sites e de dois pipelines.
- Servir pelo FastAPI (`StaticFiles`): mistura o front no processo da API; cache e CSP ficam mais simples no Caddy.
