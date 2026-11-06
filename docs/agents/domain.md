# Documentação de domínio

Como as skills de engenharia devem consumir a documentação de domínio deste repo ao explorar o código. O layout é de **contexto único**.

## Antes de explorar, leia

- **`GLOSSARY.md`** na raiz. Enquanto ele não existir, o vocabulário do cliente está em `steering/product.md` § "Domínio (vocabulário do cliente)".
- **`docs/adr/`**: leia os ADRs que tocam a área em que você vai mexer. O índice com status fica em `docs/adr/README.md`.

Se algum desses arquivos não existir, **siga em frente sem comentar**. Não aponte a ausência nem sugira criá-los antecipadamente. A skill `/domain-modeling` (acionada por `/grill-with-docs` e `/improve-codebase-architecture`) cria esses arquivos quando um termo ou decisão é de fato resolvido.

## Estrutura

```
/
├── GLOSSARY.md            ← criado quando o primeiro termo for resolvido
├── steering/product.md    ← vocabulário do cliente (fonte provisória)
├── docs/adr/
│   ├── README.md          ← índice e status
│   ├── 0000-modelo.md     ← modelo de ADR
│   ├── 0001-fastapi-como-backend.md
│   └── ...
└── src/
```

## Use o vocabulário do glossário

Quando sua saída nomear um conceito de domínio (título de issue, proposta de refatoração, hipótese, nome de teste), use o termo como definido no `GLOSSARY.md` (ou, até ele existir, em `steering/product.md`). Não troque por sinônimos que o glossário evita. Termos de domínio ficam em português, conforme a seção "Idioma" do `AGENTS.md` (ex.: `unidade`, `equipamento`, `Distrito Sanitário`).

Se o conceito de que você precisa ainda não está no glossário, isso é um sinal: ou você está inventando uma linguagem que o projeto não usa (reconsidere), ou há uma lacuna real (anote para o `/domain-modeling`).

## ADRs novos

- Siga o modelo `docs/adr/0000-modelo.md`, continue a numeração e acrescente a linha na tabela de `docs/adr/README.md`.
- ADRs são imutáveis: para mudar uma decisão, crie um ADR que substitua o antigo e marque o antigo como "Substituído por".
- Um ADR novo nasce como `Proposto`. Quem muda para `Aceito` é um integrante humano, como acontece com as specs.

## Aponte conflitos com ADRs

Se sua saída contradiz um ADR existente, diga isso explicitamente em vez de passar por cima em silêncio:

> _Contradiz o ADR-0002 (monólito modular com camadas), mas vale reabrir porque…_
