"""Comando de administração `sgs-admin` (spec 002 § Decisões: `argparse`; spec 011, R6.8).

    uv run sgs-admin banco particoes [--meses N]

Subcomandos:
- `banco particoes`: garante as partições mensais do log do banco (`db_change_log`) do mês atual
  até N meses à frente (padrão: 12, o mesmo da migração) com `sp_ensure_monthly_partitions`.
  Mostra cada partição criada e, como aviso, cada mês pulado porque a partição DEFAULT já tem
  registros dele (011/R6.5 a R6.8).

A conexão vem da configuração (`Settings`), como nas migrações: DATABASE_MIGRATION_URL (dono do
banco) ou, na falta dela, DATABASE_URL. O login da API não executa o procedimento (011/R10.1):
sem a URL do dono, o comando sai com erro. O `create-user` da spec 002 (T8) entra como outro
subcomando de primeiro nível.

    uv run sgs-admin create-user --username admin --nome "Administrador" [--papel ADMIN_TI]

- `create-user` (spec 002, T8): cria um usuário local com senha Argon2id e uma atribuição de
  papel, e grava `usuario.criado` e `papel.atribuido` na mesma transação (AGENTS.md, regra 5). A
  senha vem de `SGS_SENHA_INICIAL` ou é pedida no terminal (duas vezes); nunca vai para o log.
  Conecta com DATABASE_URL (o login da API).
"""

import argparse
import asyncio
import getpass
import os
import sys
from collections.abc import Callable, Sequence

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from src.core.config import Settings, load_settings
from src.core.db import create_engine

# O mesmo horizonte da migração 0011_08 (011/R6.7).
MESES_A_FRENTE = 12
SEM_PRIVILEGIO = "42501"  # SQLSTATE insufficient_privilege

_GARANTIR_PARTICOES = text("CALL sp_ensure_monthly_partitions('db_change_log', :meses)")

# Mensagem do servidor: severidade em inglês (não muda com o idioma do banco) e texto.
Mensagem = tuple[str, str]


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada do `sgs-admin`; devolve o código de saída."""
    args = _parser().parse_args(argv)
    comando: Callable[[argparse.Namespace], int] = args.comando
    return comando(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sgs-admin", description="Comandos de administração da API do SGS."
    )
    comandos = parser.add_subparsers(title="comandos", required=True, metavar="COMANDO")

    banco = comandos.add_parser("banco", help="manutenção do banco de dados")
    do_banco = banco.add_subparsers(title="comandos", required=True, metavar="COMANDO")
    particoes = do_banco.add_parser(
        "particoes",
        help="garante as partições mensais do log do banco",
        description=(
            "Garante as partições mensais do log do banco (db_change_log) do mês atual até N"
            " meses à frente, sem apagar nenhuma. Conecta com DATABASE_MIGRATION_URL."
        ),
    )
    particoes.add_argument(
        "--meses",
        type=_meses,
        default=MESES_A_FRENTE,
        metavar="N",
        help=f"meses à frente do atual (padrão: {MESES_A_FRENTE})",
    )
    particoes.set_defaults(comando=_banco_particoes)

    criar = comandos.add_parser(
        "create-user",
        help="cria um usuário local (o primeiro administrador)",
        description=(
            "Cria um usuário local com senha Argon2id e um papel. A senha vem de"
            " SGS_SENHA_INICIAL ou é pedida no terminal. Conecta com DATABASE_URL."
        ),
    )
    criar.add_argument("--username", required=True)
    criar.add_argument("--nome", required=True, help="nome de exibição")
    criar.add_argument("--email", default=None)
    criar.add_argument("--papel", default="ADMIN_TI", help="código do papel (padrão: ADMIN_TI)")
    criar.add_argument(
        "--escopo-tipo", default="global", choices=("global", "area", "distrito", "unidade")
    )
    criar.add_argument("--escopo-id", default=None)
    criar.set_defaults(comando=_create_user)

    seed = comandos.add_parser("seed", help="dados de demonstração (spec 010)")
    do_seed = seed.add_subparsers(title="comandos", required=True, metavar="COMANDO")
    demo = do_seed.add_parser(
        "demo",
        help="carrega a massa de demonstração (idempotente; recusada em prod)",
        description=(
            "Carrega referências, unidades, equipamentos, serviços e 30 usuários fictícios de"
            " seeds/demo/. Rodar de novo não duplica. A senha dos usuários vem de SGS_SEED_SENHA"
            " ou é gerada e mostrada uma vez. Conecta com DATABASE_URL."
        ),
    )
    demo.set_defaults(comando=_seed_demo)
    return parser


def _meses(valor: str) -> int:
    try:
        meses = int(valor)
    except ValueError:
        raise argparse.ArgumentTypeError("use um número inteiro") from None
    if meses < 0:
        raise argparse.ArgumentTypeError("use 0 ou mais meses")
    return meses


def _banco_particoes(args: argparse.Namespace) -> int:
    settings = load_settings()
    url = settings.database_migration_url or settings.database_url
    try:
        mensagens = asyncio.run(garantir_particoes(url.get_secret_value(), settings, args.meses))
    except DBAPIError as erro:
        if getattr(erro.orig, "sqlstate", None) != SEM_PRIVILEGIO:
            raise
        # Mensagem fixa: a do erro traz o SQL, e o traceback não ajuda quem administra.
        sys.stderr.write(
            "sgs-admin: o usuário de banco não pode executar sp_ensure_monthly_partitions;"
            " defina DATABASE_MIGRATION_URL com o dono do banco\n"
        )
        return 1
    for severidade, texto in mensagens:
        if severidade == "WARNING":
            sys.stderr.write(f"aviso: {texto}\n")
        else:
            sys.stdout.write(f"{texto}\n")
    sys.stdout.write(
        f"Partições do log do banco garantidas do mês atual até {args.meses} meses à frente.\n"
    )
    return 0


async def garantir_particoes(url: str, settings: Settings, meses: int) -> list[Mensagem]:
    """Executa `sp_ensure_monthly_partitions` numa transação e devolve as mensagens do banco."""
    mensagens: list[Mensagem] = []
    engine = create_engine(url, settings, pooled=False)
    try:
        async with engine.begin() as conexao:
            # O procedimento fala por RAISE NOTICE/WARNING, que chegam ao asyncpg fora do
            # resultado da instrução, por um ouvinte da conexão.
            bruta = await conexao.get_raw_connection()
            if bruta.driver_connection is None:
                raise RuntimeError("conexão com o banco sem o driver asyncpg")
            bruta.driver_connection.add_log_listener(
                lambda _conexao, msg: mensagens.append((msg.severity_en, msg.message))
            )
            await conexao.execute(_GARANTIR_PARTICOES, {"meses": meses})
    finally:
        await engine.dispose()
    return mensagens


SENHA_MINIMA = 12


def _senha() -> str | None:
    senha = os.environ.get("SGS_SENHA_INICIAL")
    if senha is None:
        senha = getpass.getpass("Senha: ")
        if senha != getpass.getpass("Repita a senha: "):
            sys.stderr.write("sgs-admin: as senhas não conferem\n")
            return None
    if len(senha) < SENHA_MINIMA:
        sys.stderr.write(f"sgs-admin: use uma senha com ao menos {SENHA_MINIMA} caracteres\n")
        return None
    return senha


def _create_user(args: argparse.Namespace) -> int:
    senha = _senha()
    if senha is None:
        return 1
    settings = load_settings()
    try:
        usuario_id = asyncio.run(
            criar_usuario(
                settings.database_url.get_secret_value(),
                settings,
                username=args.username,
                nome=args.nome,
                email=args.email,
                senha=senha,
                papel=args.papel,
                escopo_tipo=args.escopo_tipo,
                escopo_id=args.escopo_id,
            )
        )
    except ValueError as erro:
        sys.stderr.write(f"sgs-admin: {erro}\n")
        return 1
    sys.stdout.write(
        f"Usuário {args.username} criado (id {usuario_id}) com o papel {args.papel}.\n"
    )
    return 0


async def criar_usuario(
    url: str,
    settings: Settings,
    *,
    username: str,
    nome: str,
    email: str | None,
    senha: str,
    papel: str,
    escopo_tipo: str = "global",
    escopo_id: str | None = None,
) -> str:
    """Cria o usuário e a atribuição numa transação, com auditoria. Levanta `ValueError` com uma
    mensagem para o terminal se o usuário já existe, o papel não existe ou o escopo não confere."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.ids import uuid7
    from src.modules.access.domain.atribuicoes import Atribuicao
    from src.modules.access.infrastructure.repository import SqlRepositorioDeAtribuicoes
    from src.modules.audit.application.registrar import Ator, Entidade, registrar
    from src.modules.audit.infrastructure.repository import SqlAuditStore
    from src.modules.identity.domain.users import User, UserSource
    from src.modules.identity.infrastructure.passwords import Argon2PasswordHasher
    from src.modules.identity.infrastructure.repository import SqlUserRepository

    engine = create_engine(url, settings, pooled=False)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as sessao, sessao.begin():
            usuarios = SqlUserRepository(sessao)
            if await usuarios.get_by_username(username) is not None:
                raise ValueError(f"já existe o usuário {username!r}")
            atribuicoes = SqlRepositorioDeAtribuicoes(sessao)
            definicao = await atribuicoes.papel(papel)
            if definicao is None:
                raise ValueError(f"papel inexistente: {papel!r}")
            if escopo_tipo != definicao.escopo_exigido:
                raise ValueError(f"o papel {papel} exige escopo {definicao.escopo_exigido}")
            if escopo_tipo != "global" and (
                escopo_id is None or not await atribuicoes.escopo_existe(escopo_tipo, escopo_id)
            ):
                raise ValueError("escopo inexistente")
            usuario = User(
                id=uuid7(),
                username=username,
                display_name=nome,
                source=UserSource.LOCAL,
                password_hash=Argon2PasswordHasher().hash(senha),
                email=email,
            )
            await usuarios.add(usuario)
            atribuicao_id = uuid7()
            await atribuicoes.inserir(
                Atribuicao(
                    id=atribuicao_id,
                    user_id=usuario.id,
                    papel=papel,
                    scope_type=escopo_tipo,
                    scope_id=escopo_id if escopo_tipo != "global" else None,
                    origin="direct",
                    valid_until=None,
                    granted_by=None,
                )
            )
            loja = SqlAuditStore(sessao)
            sistema = Ator()
            entidade = Entidade(tipo="usuario", id=str(usuario.id))
            await registrar(
                loja,
                acao="usuario.criado",
                ator=sistema,
                entidade=entidade,
                metadados={"username": usuario.username, "origem": "sgs-admin create-user"},
            )
            await registrar(
                loja,
                acao="papel.atribuido",
                ator=sistema,
                entidade=entidade,
                metadados={
                    "atribuicao_id": str(atribuicao_id),
                    "papel": papel,
                    "escopo_tipo": escopo_tipo,
                    "escopo_id": escopo_id,
                    "origem": "sgs-admin create-user",
                },
            )
    finally:
        await engine.dispose()
    return str(usuario.id)


def _seed_demo(args: argparse.Namespace) -> int:
    from src.tools.seed_demo import SeedRecusado, carregar

    settings = load_settings()
    try:
        contagem = asyncio.run(
            carregar(
                settings.database_url.get_secret_value(),
                settings,
                senha=os.environ.get("SGS_SEED_SENHA"),
            )
        )
    except SeedRecusado as erro:
        sys.stderr.write(f"sgs-admin: {erro}\n")
        return 1
    for tipo in sorted(set(contagem.criados) | set(contagem.pulados)):
        sys.stdout.write(
            f"{tipo}: {contagem.criados.get(tipo, 0)} criados,"
            f" {contagem.pulados.get(tipo, 0)} já existiam\n"
        )
    if contagem.senha_gerada is not None:
        sys.stdout.write(
            "Senha gerada para os usuários demo.* (anote, não será mostrada de novo):"
            f" {contagem.senha_gerada}\n"
        )
    return 0
