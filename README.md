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

O caixa não vem com o `git`, então antes é preciso atualizar a lista de pacotes e instalá-lo:

```bash
sudo apt-get update
sudo apt install -y git
```

Depois clone e instale:

```bash
git clone https://github.com/cnandocg/calculadora-pdv.git
cd calculadora-pdv
sudo ./pdv-calculadora.sh instalar
```

### Comandos

O `pdv-calculadora.sh` é um script só, e a palavra depois dele diz o que ele deve fazer. É como escolher uma opção de um menu.

| Comando | O que faz |
|---|---|
| `sudo ./pdv-calculadora.sh instalar` | Instala tudo e já liga o atalho Ctrl+C |
| `sudo ./pdv-calculadora.sh desativar` | Desliga o Ctrl+C e fecha a calculadora, mas deixa tudo instalado. Vale também depois de reiniciar |
| `sudo ./pdv-calculadora.sh ativar` | Liga de novo o Ctrl+C |
| `sudo ./pdv-calculadora.sh status` | Mostra se está instalada, ativada e rodando |
| `sudo ./pdv-calculadora.sh desinstalar` | Remove tudo e deixa o caixa como era antes |

O `desinstalar` faz três coisas:
1. Desliga o atalho e fecha a calculadora, se estiver aberta.
2. Tira a linha que foi colocada no `/pdv/inicia_pdv`.
3. Apaga a pasta `/opt/pdv-calculadora`.

Os pacotes do apt (`xbindkeys`, `xdotool`) continuam instalados, mas parados, sem efeito nenhum. Se quiser removê-los também:
```bash
sudo apt-get remove xbindkeys xdotool
```

**Onde fica instalada:** o `instalar` copia tudo para `/opt/pdv-calculadora`, e é de lá que o atalho e a calculadora rodam:

| Arquivo | Função |
|---|---|
| `/opt/pdv-calculadora/calculadora.py` | A calculadora |
| `/opt/pdv-calculadora/abrir-calculadora.sh` | Abre/fecha a calculadora quando aperta Ctrl+C |
| `/opt/pdv-calculadora/xbindkeysrc` | Configuração do atalho Ctrl+C |
| `/opt/pdv-calculadora/pdv-calculadora.sh` | Cópia do script de comandos |
| `/opt/pdv-calculadora/ativo` | Existe quando o atalho está ativado |

Além disso, uma linha é colocada no `/pdv/inicia_pdv`, com backup em `/pdv/inicia_pdv.antes-calculadora`.

**Posso apagar a pasta do clone?** Sim. Depois do `instalar`, a pasta `calculadora-pdv` não é mais usada e a calculadora continua funcionando:
```bash
rm -rf calculadora-pdv
```
Daí em diante, use os comandos pelo caminho completo, por exemplo `sudo /opt/pdv-calculadora/pdv-calculadora.sh status`.
Só é preciso clonar de novo para **reinstalar ou atualizar** (`instalar`).

**Atenção:** não apague a pasta `/opt/pdv-calculadora` na mão. Para remover, use o `desinstalar`, que também tira a linha do `inicia_pdv`.

**Onde rodar:**
- **Na pasta do git clone:** `cd calculadora-pdv` e depois `sudo ./pdv-calculadora.sh <opção>`. O `./` significa "o script desta pasta".
- **De qualquer lugar**, mesmo se a pasta do clone foi apagada: `sudo /opt/pdv-calculadora/pdv-calculadora.sh <opção>`. A exceção é o `instalar`, que precisa rodar da pasta do clone, porque é de lá que ele copia os arquivos.

Se digitar sem nenhuma palavra, ou com uma palavra errada, o script só mostra as opções e não faz nada:
```
Uso: ./pdv-calculadora.sh {instalar|ativar|desativar|status|desinstalar}
```

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
