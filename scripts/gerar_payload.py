"""Gera o JSON de request pro POST /analisar a partir de dois arquivos de texto.

Uso:
    python scripts/gerar_payload.py <vaga.txt> <curriculo.txt>

Cola o JSON impresso direto no campo "Try it out" do Swagger (/docs) — colar o
texto bruto com quebras de linha reais quebra o JSON, então geramos aqui já
com as quebras escapadas corretamente.
"""

import json
import sys


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Uso: python {sys.argv[0]} <vaga.txt> <curriculo.txt>", file=sys.stderr)
        sys.exit(1)

    vaga_path, curriculo_path = sys.argv[1], sys.argv[2]

    with open(vaga_path, encoding="utf-8") as f:
        vaga_texto = f.read()
    with open(curriculo_path, encoding="utf-8") as f:
        curriculo = f.read()

    payload = {"vaga_texto": vaga_texto, "curriculo": curriculo}
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
