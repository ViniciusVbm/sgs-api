"""Catálogo das consultas e views expostas (spec 011, R3; T19).

Cada entrada diz ao front (e a quem apresenta o projeto) o que a consulta mostra, por que existe,
que parâmetros aceita, que colunas devolve, que permissão exige e que gráfico combina com ela,
sem precisar ler o SQL. O texto da justificativa resume o cabeçalho do `.sql` correspondente.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntradaDoCatalogo:
    nome: str
    rota: str
    titulo: str
    justificativa: str
    tecnica_sql: str
    parametros: tuple[str, ...]
    colunas: tuple[str, ...]
    permissao: str
    grafico_sugerido: str
    arquivo_sql: str | None = None
    """Arquivo em `dashboard/infrastructure/sql` das consultas servidas pela rota genérica."""
    paginada: bool = True


_FILTROS = ("distrito", "tipo", "area")
_PAGINA = ("pagina", "tamanho")

CATALOGO: tuple[EntradaDoCatalogo, ...] = (
    EntradaDoCatalogo(
        nome="unidades-sem-servico",
        rota="/api/v1/dashboard/consultas/unidades-sem-servico",
        titulo="Unidades sem nenhum serviço cadastrado",
        justificativa="Lacuna do cadastro: a unidade ativa que não oferta nada pede revisão.",
        tecnica_sql="anti join (LEFT JOIN ... WHERE s.id IS NULL)",
        parametros=("distrito", "tipo", *_PAGINA),
        colunas=("id", "nome", "cnes", "tipo", "distrito"),
        permissao="dashboard:read",
        grafico_sugerido="tabela",
    ),
    EntradaDoCatalogo(
        nome="conciliacao-unidade-equipamento",
        rota="/api/v1/dashboard/consultas/conciliacao-unidade-equipamento",
        titulo="Conciliação unidade x equipamento",
        justificativa="Numa resposta: pares, unidades sem equipamento e equipamentos sem unidade.",
        tecnica_sql="FULL OUTER JOIN",
        parametros=("distrito", "tipo", *_PAGINA),
        colunas=(
            "unidade_id",
            "unidade_nome",
            "distrito",
            "equipamento_id",
            "equipamento_nome",
            "equipamento_tipo",
            "situacao",
        ),
        permissao="dashboard:read",
        grafico_sugerido="barras empilhadas por situação",
    ),
    EntradaDoCatalogo(
        nome="distritos-sem-cnes-acima-da-rede",
        rota="/api/v1/dashboard/consultas/distritos-sem-cnes-acima-da-rede",
        titulo="Distritos com mais unidades sem CNES que a rede",
        justificativa="Onde se concentra a falta de CNES, comparada com o percentual da rede.",
        tecnica_sql="subconsulta escalar no HAVING",
        parametros=(*_FILTROS, *_PAGINA),
        colunas=(
            "district_id",
            "district_name",
            "total_units",
            "units_without_cnes",
            "percent_without_cnes",
            "network_percent_without_cnes",
        ),
        permissao="dashboard:read",
        grafico_sugerido="barras com linha de referência (percentual da rede)",
        arquivo_sql="districts_cnes_above_network.sql",
    ),
    EntradaDoCatalogo(
        nome="unidades-com-servico-fora-do-cnes",
        rota="/api/v1/dashboard/consultas/unidades-com-servico-fora-do-cnes",
        titulo="Unidades com serviço fora do CNES",
        justificativa="Serviço fora do CNES não entra nos indicadores federais: regularizar.",
        tecnica_sql="subconsulta correlacionada com EXISTS",
        parametros=(*_FILTROS, *_PAGINA),
        colunas=(
            "unit_id",
            "name",
            "cnes",
            "unit_type_name",
            "district_name",
            "services_outside_cnes_count",
        ),
        permissao="dashboard:read",
        grafico_sugerido="tabela",
        arquivo_sql="units_with_services_outside_cnes.sql",
    ),
    EntradaDoCatalogo(
        nome="inventario",
        rota="/api/v1/dashboard/inventario",
        titulo="Inventário da rede (vw_unit_inventory)",
        justificativa="Definição única do inventário: tipo, área, distrito, situação e contagens.",
        tecnica_sql="view com 3 JOINs e 2 LEFT JOINs com agregados; função fn_registration_status",
        parametros=(*_FILTROS, "situacao", *_PAGINA),
        colunas=(
            "unit_id",
            "name",
            "cnes",
            "status",
            "registration_status",
            "unit_type_name",
            "technical_area_name",
            "district_name",
            "equipment_count",
            "service_count",
            "services_outside_cnes_count",
        ),
        permissao="dashboard:read",
        grafico_sugerido="tabela com filtros",
        arquivo_sql="unit_inventory.sql",
    ),
    EntradaDoCatalogo(
        nome="unidades-por-categoria",
        rota="/api/v1/dashboard/consultas/unidades-por-categoria",
        titulo="Unidades por status, tipo, área, distrito e situação cadastral",
        justificativa="Distribuição da rede para conferir os dados inseridos (Etapa 03).",
        tecnica_sql="UNION ALL de agregações sobre a vw_unit_inventory",
        parametros=_FILTROS,
        colunas=("categoria", "chave", "rotulo", "quantidade"),
        permissao="dashboard:read",
        grafico_sugerido="pizza ou barras, uma por categoria",
        arquivo_sql="units_by_category.sql",
        paginada=False,
    ),
    EntradaDoCatalogo(
        nome="equipamentos-por-tipo-e-distrito",
        rota="/api/v1/dashboard/consultas/equipamentos-por-tipo-e-distrito",
        titulo="Equipamentos por tipo e distrito",
        justificativa="Como os equipamentos de saúde se distribuem pela rede (Etapa 03).",
        tecnica_sql="JOIN de cinco tabelas com GROUP BY e SUM",
        parametros=_FILTROS,
        colunas=(
            "equipment_type_code",
            "equipment_type_name",
            "district_id",
            "district_name",
            "equipment_count",
            "total_quantity",
        ),
        permissao="dashboard:read",
        grafico_sugerido="barras agrupadas (tipo x distrito)",
        arquivo_sql="equipments_by_type_district.sql",
        paginada=False,
    ),
    EntradaDoCatalogo(
        nome="alteracoes-por-periodo",
        rota="/api/v1/dashboard/consultas/alteracoes-por-periodo",
        titulo="Alterações de unidades nos últimos 7 e 30 dias, por distrito",
        justificativa="Onde o cadastro está sendo mantido (Etapa 03).",
        tecnica_sql="vw_unit_history com count(*) FILTER e subconsulta IN para o tipo",
        parametros=_FILTROS,
        colunas=("district_id", "district_name", "last_7_days", "last_30_days"),
        permissao="dashboard:read",
        grafico_sugerido="barras lado a lado (7 e 30 dias)",
        arquivo_sql="changes_by_period.sql",
        paginada=False,
    ),
    EntradaDoCatalogo(
        nome="alteracoes-recentes",
        rota="/api/v1/dashboard/consultas/alteracoes-recentes",
        titulo="As 10 alterações mais recentes",
        justificativa="Quem mudou o quê, por último, no escopo do usuário (Etapa 03).",
        tecnica_sql="vw_unit_history (4 JOINs) ordenada por data",
        parametros=_FILTROS,
        colunas=(
            "audit_id",
            "occurred_at",
            "action",
            "unit_id",
            "unit_name",
            "district_name",
            "actor_name",
        ),
        permissao="dashboard:read",
        grafico_sugerido="linha do tempo",
        arquivo_sql="recent_changes.sql",
        paginada=False,
    ),
    EntradaDoCatalogo(
        nome="resumo",
        rota="/api/v1/dashboard/resumo",
        titulo="Resumo da rede",
        justificativa="Indicadores de unidades, qualidade e alterações numa chamada só (009/R1).",
        tecnica_sql="agregações sobre as views e subconsultas escalares",
        parametros=_FILTROS,
        colunas=("unidades", "qualidade", "alteracoes", "gerado_em"),
        permissao="dashboard:read",
        grafico_sugerido="cartões de indicador e gráficos de distribuição",
        paginada=False,
    ),
    EntradaDoCatalogo(
        nome="historico-da-unidade",
        rota="/api/v1/unidades/{id}/historico",
        titulo="Histórico de uma unidade (vw_unit_history)",
        justificativa="O que mudou, quando e por quem, com equipamentos e serviços (008/R1).",
        tecnica_sql="view com 4 JOINs; índice ix_audit_log_entity",
        parametros=("de", "ate", "autor", "campo", *_PAGINA),
        colunas=("id", "quando", "acao", "autor", "papeis", "mudancas"),
        permissao="auditoria:read",
        grafico_sugerido="linha do tempo",
    ),
    EntradaDoCatalogo(
        nome="log-do-banco",
        rota="/api/v1/auditoria/banco",
        titulo="Log do banco (trigger trg_registry_change_log)",
        justificativa="Toda escrita no cadastro, inclusive fora da API, gravada por trigger.",
        tecnica_sql="tabela particionada por mês, preenchida por trigger",
        parametros=("de", "ate", "tabela", "fora_da_api", *_PAGINA),
        colunas=("id", "quando", "tabela", "operacao", "linha", "colunas", "usuario_do_banco"),
        permissao="auditoria:read",
        grafico_sugerido="tabela",
    ),
    EntradaDoCatalogo(
        nome="particoes-do-log",
        rota="/api/v1/auditoria/banco/particoes",
        titulo="Partições mensais do log do banco",
        justificativa="As partições que o procedimento com cursor criou e as linhas de cada uma.",
        tecnica_sql="catálogo do PostgreSQL (pg_inherits); procedimento com CURSOR",
        parametros=(),
        colunas=("nome", "inicio", "fim", "linhas"),
        permissao="auditoria:read",
        grafico_sugerido="barras por mês",
        paginada=False,
    ),
)

POR_NOME = {entrada.nome: entrada for entrada in CATALOGO}
