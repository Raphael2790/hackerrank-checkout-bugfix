"""Trava do treino: hook PreToolUse do Claude Code.

Roda antes de cada ferramenta que o agente usa. Se a chamada citar os testes ocultos, o gabarito ou os rastros
da criação do desafio, ou fizer uma busca que alcançaria essas pastas, o hook sai com código 2: o Claude Code
bloqueia a chamada e mostra o motivo ao agente.
"""
import json
import re
import sys

BLOQUEIOS = [
    (r"hidden[\s_-]?tests", "testes ocultos"),
    (r"gabarito|\.b64\b|base64|b64decode", "gabarito"),
    (r"\.claude[\\/]+(plans|projects|file-history|todos|shell-snapshots)", "rastros da criação do desafio"),
    (r"appdata[\\/]+local[\\/]+temp", "pasta temporária"),
    (r"\.\.[\\/]+hackerrank-", "outros repositórios de treino"),
    (r"\bgit\s+grep\b", "git grep busca no repositório inteiro"),
    (r"\bgrep\b[^|;&\n]*\s(-[a-z]*r[a-z]*|--recursive)(?=\s|$)", "busca recursiva pelo terminal"),
    (r"\bfindstr\b[^|;&\n]*\s/s\b", "busca recursiva pelo terminal"),
    (r"(?s)(?=.*\b(select-string|sls)\b)(?=.*\s-r(ecurse)?\b)", "busca recursiva pelo terminal"),
    (r"\brg\b[^|;&\n]*\s(--no-ignore\S*|--hidden|-u+)(?=\s|$)", "busca que ignora o .ignore"),
    (r"\bpytest\b[^|;&\n]*\s\.{1,2}[\\/]?(?=\s|$)", "pytest na raiz coletaria os testes ocultos"),
]


def textos(valor, chave=None):
    """Todos os textos da entrada da ferramenta, menos a descrição (que é só um rótulo)."""
    if chave == "description":
        return
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for k, v in valor.items():
            yield from textos(v, k)
    elif isinstance(valor, list):
        for v in valor:
            yield from textos(v)


def main() -> int:
    try:
        evento = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except ValueError:
        return 0
    entrada = "\n".join(textos(evento.get("tool_input") or {})).lower()
    for padrao, motivo in BLOQUEIOS:
        if re.search(padrao, entrada):
            sys.stderr.reconfigure(encoding="utf-8")
            print(
                f"BLOQUEADO pela trava do treino ({motivo}). Pelas regras do CLAUDE.md, você não acessa testes "
                "ocultos, gabarito nem rastros da criação do desafio, e só busca em app/, tests/ ou meus_testes/. "
                "Não tente outro caminho para o mesmo conteúdo.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
