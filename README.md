# pdv-calculadora

Abre uma calculadora moderna (tema escuro, com histórico das contas) por cima do **PDV Arius** com **Ctrl+C**, sem fechar o caixa.
O mesmo atalho fecha a calculadora e devolve o foco do teclado para o PDV.

## Por que Ctrl+C e não Shift+C

No mapeamento de teclas do Arius (tabela `mapeamentotecla` do `pdvCad.db`):

| Tecla | Operação no PDV |
|---|---|
| Shift | Totaliza Venda |
| C | Consulta Mercadoria |
| Ctrl | (não mapeada, ignorada) |

O Arius processa a tecla no momento em que ela é pressionada, então Shift+C totalizaria a venda.
Com Ctrl+C o PDV ignora o Ctrl e o C é capturado pelo atalho antes de chegar ao caixa.

## Uso no caixa

```bash
git clone https://github.com/cnandocg/calculadora-pdv.git
cd calculadora-pdv
sudo ./pdv-calculadora.sh instalar
```

| Comando | O que faz |
|---|---|
| `instalar` | Instala xbindkeys/xdotool/python3-gi, copia para `/opt/pdv-calculadora`, adiciona uma linha no `/pdv/inicia_pdv` (backup em `inicia_pdv.antes-calculadora`) e ativa |
| `ativar` | Liga o atalho (na hora, se o PDV estiver aberto) |
| `desativar` | Desliga o atalho e fecha a calculadora |
| `status` | Mostra se está instalada/ativa |
| `desinstalar` | Remove a linha do `inicia_pdv` e a pasta `/opt/pdv-calculadora` |

Depois de instalado, os comandos também ficam em `/opt/pdv-calculadora/pdv-calculadora.sh`.

## Como funciona

- `xbindkeys` captura Ctrl+C no X do caixa e chama `abrir-calculadora.sh`.
- O X do PDV roda sem gerenciador de janelas, então o script guarda a janela que tinha o foco,
  centraliza e foca a calculadora, e ao fechar devolve o foco para o PDV.

## A calculadora

`arquivos/calculadora.py` (Python 3 + GTK3, já presente no Ubuntu do caixa).

Tudo funciona **sem mouse** (os caixas não têm). Os atalhos aparecem no rodapé da calculadora.

| Tecla | Função |
|---|---|
| Enter ou `=` | Calcula |
| `+ - * /` `( )` `%` | Operações (teclado normal ou numérico) |
| `,` ou `.` | Decimal |
| ↑ / ↓ | Percorre o histórico e traz o resultado para o visor |
| Backspace | Apaga |
| Delete | Limpa o visor |
| Ctrl+L (ou Ctrl+Delete) | Limpa o histórico |
| Ctrl+Z | Desfaz |
| Esc ou Ctrl+C | Fecha e volta para o PDV |

- O histórico fica em `/tmp`, então vale para o dia e zera quando o caixa reinicia.
- Porcentagem de caixa: `200+10% = 220`, `200-10% = 180`, `200×10% = 20`.
- Contas em decimal exato (`0,1+0,2 = 0,3`).
- Teste rápido das contas: `python3 arquivos/calculadora.py --teste`

## Créditos

Desenvolvido por **Claudio Fernando**.
