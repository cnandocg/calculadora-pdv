#!/bin/bash
# Abre/fecha a calculadora por cima do PDV Arius (chamado pelo xbindkeys).
# O X do caixa roda sem gerenciador de janelas, entao o foco do teclado
# e controlado aqui: guarda a janela do PDV, foca a calculadora e, ao
# fechar, devolve o foco para o PDV.

CALC=/opt/pdv-calculadora/calculadora.py
ESTADO=/tmp/pdv-calculadora.foco

export DISPLAY="${DISPLAY:-:0}"

# Janela do PDV que recebe o teclado: o FocusProxy da tela visivel do Arius.
janela_pdv() {
    local w
    for w in $(xwininfo -root -children | awk '/arius-PdvDesktop/ {print $1}'); do
        xwininfo -id "$w" | grep -q 'IsViewable' || continue
        xwininfo -id "$w" -children | awk '/"FocusProxy"/ {print $1; f=1} END {exit !f}' && return
        echo "$w" && return
    done
}

devolve_foco() {
    local alvo
    alvo=$(cat "$ESTADO" 2>/dev/null)
    rm -f "$ESTADO"
    # A janela guardada pode ter sumido (PDV reiniciou, dialogo fechou).
    if [ -z "$alvo" ] || ! xwininfo -id "$alvo" 2>/dev/null | grep -q 'IsViewable'; then
        alvo=$(janela_pdv)
    fi
    [ -n "$alvo" ] && xdotool windowfocus "$alvo" 2>/dev/null
}

# Ja aberta? Mesmo atalho fecha e volta pro caixa.
if pgrep -f "^python3 $CALC" >/dev/null; then
    pkill -f "^python3 $CALC"
    sleep 0.2
    devolve_foco
    exit 0
fi

xdotool getwindowfocus > "$ESTADO" 2>/dev/null

python3 "$CALC" &
PID=$!

JANELA=$(timeout 10 xdotool search --sync --onlyvisible --pid "$PID" | head -1)
if [ -n "$JANELA" ]; then
    # Centraliza na tela
    read -r LARG ALT < <(xdotool getdisplaygeometry)
    eval "$(xdotool getwindowgeometry --shell "$JANELA")"
    xdotool windowmove "$JANELA" $(( (LARG - WIDTH) / 2 )) $(( (ALT - HEIGHT) / 2 ))
    xdotool windowraise "$JANELA"
    xdotool windowfocus --sync "$JANELA"
fi

# Fechada pelo menu da calculadora (Ctrl+Q): devolve o foco tambem.
wait "$PID"
devolve_foco
