#!/bin/bash
# Atalho para Mac: dê duplo clique. (Na primeira vez: chmod +x atualizar.command)
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 não encontrado. Instale em https://www.python.org/downloads/ (passo 1 do README.md)."
  read -r -p "Pressione Enter para fechar..."
  exit 1
fi

python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt || {
  echo "Não consegui instalar as dependências. Verifique a internet."
  read -r -p "Pressione Enter para fechar..."
  exit 1
}

echo "Coletando imóveis (leva alguns minutos, há pausas de propósito)..."
if python3 coletor.py; then
  echo; echo "PRONTO! Agora abra o arquivo buscar.html"
else
  echo; echo "A atualização falhou - a lista anterior foi mantida. Veja coletor.log"
fi
read -r -p "Pressione Enter para fechar..."
