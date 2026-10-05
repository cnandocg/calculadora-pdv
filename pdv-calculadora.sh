#!/bin/bash
# Calculadora no PDV Arius com atalho Ctrl+C.
#
# Uso: sudo ./pdv-calculadora.sh {instalar|ativar|desativar|status|desinstalar}

set -e

DESTINO=/opt/pdv-calculadora
INICIA_PDV=/pdv/inicia_pdv
MARCA="# pdv-calculadora"
FLAG="$DESTINO/ativo"
ORIGEM="$(cd "$(dirname "$0")" && pwd)"

msg()  { echo -e "\e[1;32m[calculadora]\e[0m $*"; }
erro() { echo -e "\e[1;31m[calculadora]\e[0m $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || erro "Rode como root (sudo)."

# Sessao X do caixa (startx do inicia_pdv), para agir sem reiniciar o PDV.
usa_x_do_caixa() {
    export DISPLAY=:0
    local auth
    auth=$(ls -t /tmp/serverauth.* 2>/dev/null | head -1)
    [ -n "$auth" ] && export XAUTHORITY="$auth"
    xdpyinfo >/dev/null 2>&1
}

liga_atalho() {
    # No boot o inicia_pdv roda sem HOME e o xbindkeys da segfault sem ele.
    export HOME="${HOME:-/root}"
    pkill -x xbindkeys 2>/dev/null || true
    xbindkeys -f "$DESTINO/xbindkeysrc"
}

desliga_atalho() {
    pkill -x xbindkeys 2>/dev/null || true
    pkill -f "^python3 /opt/pdv-calculadora/calculadora.py" 2>/dev/null || true
}

instalar() {
    [ -f "$INICIA_PDV" ] || erro "$INICIA_PDV nao encontrado. Este e um PDV Arius?"

    msg "Instalando pacotes (xbindkeys, xdotool, python3-gi)..."
    # Alguns caixas tem repositorio quebrado no sources.list; nao trava por isso.
    apt-get update -qq || msg "apt-get update com erros, seguindo com o cache atual."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xbindkeys xdotool x11-utils python3-gi gir1.2-gtk-3.0 >/dev/null

    msg "Copiando arquivos para $DESTINO"
    mkdir -p "$DESTINO"
    install -m 755 "$ORIGEM/arquivos/abrir-calculadora.sh" "$DESTINO/"
    install -m 644 "$ORIGEM/arquivos/xbindkeysrc" "$DESTINO/"
    install -m 755 "$ORIGEM/arquivos/calculadora.py" "$DESTINO/"
    install -m 755 "$ORIGEM/pdv-calculadora.sh" "$DESTINO/"

    if ! grep -q "$MARCA" "$INICIA_PDV"; then
        cp -p "$INICIA_PDV" "$INICIA_PDV.antes-calculadora"
        # Entra logo antes da linha que sobe o PDV (a que nao esta comentada).
        sed -i "0,/^java -jar AriusPdv.jar/s||$DESTINO/pdv-calculadora.sh sessao $MARCA\n&|" "$INICIA_PDV"
        grep -q "$MARCA" "$INICIA_PDV" || erro "Nao achei 'java -jar AriusPdv.jar' em $INICIA_PDV."
        msg "inicia_pdv alterado (backup: $INICIA_PDV.antes-calculadora)"
    fi

    ativar
}

ativar() {
    [ -d "$DESTINO" ] || erro "Nao instalado. Rode: $0 instalar"
    touch "$FLAG"
    if usa_x_do_caixa; then
        liga_atalho
        msg "Ativada. Ctrl+C abre/fecha a calculadora."
    else
        msg "Ativada. Vale a partir do proximo inicio do PDV."
    fi
}

desativar() {
    rm -f "$FLAG"
    usa_x_do_caixa && desliga_atalho
    msg "Desativada. Ctrl+C nao abre mais a calculadora."
}

# Chamado pelo inicia_pdv, dentro do X, antes do Java subir.
sessao() {
    [ -f "$FLAG" ] && liga_atalho
    exit 0
}

status() {
    [ -d "$DESTINO" ] && echo "Instalada:        sim" || echo "Instalada:        nao"
    [ -f "$FLAG" ]    && echo "Ativada:          sim" || echo "Ativada:          nao"
    grep -q "$MARCA" "$INICIA_PDV" 2>/dev/null && echo "No inicia_pdv:    sim" || echo "No inicia_pdv:    nao"
    pgrep -x xbindkeys >/dev/null && echo "Atalho rodando:   sim" || echo "Atalho rodando:   nao"
}

desinstalar() {
    desativar
    if [ -f "$INICIA_PDV" ]; then
        sed -i "/$MARCA/d" "$INICIA_PDV"
        msg "Linha removida do inicia_pdv."
    fi
    rm -rf "$DESTINO"
    msg "Removida. (Pacotes apt mantidos; para remover: apt-get remove xbindkeys xdotool)"
}

case "$1" in
    instalar)    instalar ;;
    ativar)      ativar ;;
    desativar)   desativar ;;
    sessao)      sessao ;;
    status)      status ;;
    desinstalar) desinstalar ;;
    *) echo "Uso: $0 {instalar|ativar|desativar|status|desinstalar}"; exit 1 ;;
esac
