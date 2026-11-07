"""Regras puras da unidade de saúde (spec 006, design § Campos estruturais e § Diff e auditoria)."""

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

# O que o `\s` do Postgres casa num banco UTF-8 com locale `en_US.utf8` (imagem `postgres:17`).
# Fica de fora o que o Python chama de espaço e o Postgres não: U+00A0, U+2007, U+202F (espaços
# não separáveis), U+0085 e U+001C a U+001F.
_ESPACOS_DO_POSTGRES = re.compile(
    "[\t\n\v\f\r \u1680\u2000-\u2006\u2008-\u200a\u2028\u2029\u205f\u3000]+"
)


def normalizar_nome(nome: str) -> str:
    """Nome sem acento, em minúsculas e sem espaços extras (006/R1.4, 011/R5.1).

    Espelha, passo a passo e na mesma ordem, a `fn_normalize_name` do banco (design da 011,
    § Na 0006), que gera `health_units.name_normalized`:

        regexp_replace(lower(public.unaccent('public.unaccent'::regdictionary, btrim(p_name))),
                       '\\s+', ' ', 'g')

    1. `btrim` sem segundo argumento tira só o espaço comum (U+0020) das pontas;
    2. `unaccent` vira decomposição NFD sem as marcas combinantes;
    3. `lower`;
    4. cada sequência do `\\s` do Postgres vira um espaço.

    Conferida contra o banco (`postgres:17`, locale `en_US.utf8`) para letras latinas acentuadas
    e espaços. Fica de fora o que o `unaccent.rules` translitera além dos acentos (travessão
    U+2013, aspas curvas, ligaduras e letras cortadas como "æ", "ß", "ø", "ł") e as poucas marcas
    combinantes que ele mantém (U+034F, U+0363 a U+036F): aí os dois lados divergem. A unicidade
    (índice único sobre `name_normalized`) e a busca usam a função do banco, que é a fonte da
    verdade; para consultar o banco, chame `fn_normalize_name` no SQL.

    Como o `btrim` vem antes do `regexp_replace`, um tab ou uma quebra de linha na ponta vira um
    espaço que fica no resultado; isso está em Perguntas em aberto da 011 (R5.1). Se a regra mudar
    na 011, mude aqui também.
    """
    sem_pontas = nome.strip(" ")
    decomposto = unicodedata.normalize("NFD", sem_pontas)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return _ESPACOS_DO_POSTGRES.sub(" ", sem_acento.lower())


@dataclass(frozen=True, slots=True)
class Mudanca:
    """Um campo que mudou, com o valor de antes e o de depois (006/R3.5)."""

    campo: str
    de: object
    para: object


def diff(antes: Mapping[str, object], depois: Mapping[str, object]) -> list[Mudanca]:
    """Campos de `depois` cujo valor difere do de `antes`, na ordem de `depois` (006/R3.5).

    `depois` pode trazer só os campos enviados no PATCH: campo ausente de `depois` não é comparado.
    """
    return [
        Mudanca(campo=campo, de=antes.get(campo), para=valor)
        for campo, valor in depois.items()
        if antes.get(campo) != valor
    ]


CAMPOS_ESTRUTURAIS = frozenset({"district_id", "unit_type_id", "cnes"})
"""Distrito, tipo e CNES: alterá-los exige `unidade:update` com escopo global ou de área (R3.4)."""


def campos_estruturais_alterados(mudancas: Iterable[Mudanca]) -> list[str]:
    """Campos estruturais entre as mudanças, na ordem delas, para o 403 apontá-los (006/R3.4).

    Recebe o resultado de `diff`: enviar um campo estrutural com o valor que ele já tem não é
    alterá-lo. A verificação do escopo fica no caso de uso.
    """
    return [m.campo for m in mudancas if m.campo in CAMPOS_ESTRUTURAIS]
