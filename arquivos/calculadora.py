#!/usr/bin/env python3
"""Calculadora do PDV: tema escuro, historico das contas e teclado completo.

Teclas: numeros e + - * / ( ) % ,   Enter ou = calcula   Backspace apaga
        Delete limpa   Ctrl+Z desfaz   Esc fecha
        Seta cima/baixo percorre o historico e traz o resultado pro visor
        Ctrl+L limpa o historico
Tudo funciona sem mouse (o caixa nao tem).
"""
import json
import os
import sys
from decimal import Decimal, InvalidOperation, getcontext

import gi

os.environ.setdefault("NO_AT_BRIDGE", "1")
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

getcontext().prec = 34
PI = Decimal("3.141592653589793238462643383279503")
HISTORICO = "/tmp/pdv-calculadora-historico.json"
MAX_HISTORICO = 100
DIGITOS = "0123456789"

CSS = b"""
window { background: #1e1e20; }
.topo { background: #2b2b2f; padding: 6px 10px; }
.topo label.titulo { color: #ffffff; font-weight: bold; font-size: 15px; }
.topo button { background: none; border: none; box-shadow: none; color: #ffffff;
               font-weight: bold; font-size: 14px; padding: 4px 10px; border-radius: 6px; }
.topo button:hover { background: #3a3a3f; }
.topo button.fechar { background: #3a3a3f; border-radius: 99px; min-width: 26px;
                      min-height: 26px; padding: 0; }
.topo button.fechar:hover { background: #4a4a50; }
.painel, .painel viewport { background: #35353a; }
list, list row { background: #35353a; color: #e8e8e8; }
list row { padding: 6px 14px; border-bottom: 1px solid #2a2a2e; }
list row:hover { background: #3d3d43; }
list row label { font-size: 18px; }
list row label.igual { color: #9a9a9a; }
list row label.resultado { font-weight: bold; color: #ffffff; }
entry.visor { background: #35353a; color: #ffffff; border: none; border-radius: 0;
              box-shadow: none; font-size: 22px; font-weight: bold; padding: 14px;
              caret-color: #ffffff; }
list row.marcada { background: #3584e4; }
list row.marcada label.igual { color: #dce8f8; }
label.dicas { color: #8e8e93; font-size: 12px; background: #2b2b2f; padding: 0 12px 10px 12px; }
label.erro { color: #ff7b72; font-size: 13px; padding: 0 14px 6px 14px; background: #35353a; }
.teclas { padding: 12px; background: #2b2b2f; }
.teclas button { font-size: 17px; color: #ffffff; border: none; box-shadow: none;
                 border-radius: 8px; background: #3a3a3f; min-height: 44px; }
.teclas button:hover { background: #45454b; }
.teclas button:active { background: #55555c; }
.teclas button.num { background: #505056; }
.teclas button.num:hover { background: #5c5c63; }
.teclas button.igual { background: #3584e4; }
.teclas button.igual:hover { background: #4a93ea; }
.teclas button.igual:active { background: #2a6cbd; }
"""


# ---------------------------------------------------------------- calculo
class ErroConta(Exception):
    pass


def tokeniza(texto):
    t = texto.replace(" ", "").replace("*", "×").replace("x", "×").replace("/", "÷")
    t = t.replace("-", "−").replace("−", "-").replace("–", "-")
    tokens, i = [], 0
    while i < len(t):
        c = t[i]
        if c in DIGITOS or c in ",.":
            j = i
            while j < len(t) and (t[j] in DIGITOS or t[j] in ",."):
                j += 1
            num = t[i:j].replace(",", ".")
            if num.count(".") > 1:
                raise ErroConta("Número inválido")
            try:
                tokens.append(("n", Decimal(num if num != "." else "0")))
            except InvalidOperation:
                raise ErroConta("Número inválido")
            i = j
        elif t.startswith("mod", i):
            tokens.append(("op", "mod"))
            i += 3
        elif c in "+-×÷()%²√π^":
            tokens.append(("op", c))
            i += 1
        else:
            raise ErroConta(f"Caractere inválido: {c}")
    return tokens


class Parser:
    """Precedencia: + -  <  × ÷ mod  <  unario/√  <  ^ ²  %.
    Porcentagem de caixa: 200+10% = 220, 200-10% = 180, 200×10% = 20."""

    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    def ver(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def pega(self):
        tok = self.ver()
        self.i += 1
        return tok

    def conta(self):
        if not self.t:
            raise ErroConta("")
        v = self.soma()
        if self.i != len(self.t):
            raise ErroConta("Expressão incompleta")
        return v

    def soma(self):
        v, _ = self.produto()
        while self.ver() in (("op", "+"), ("op", "-")):
            op = self.pega()[1]
            d, pct = self.produto()
            if pct is not None:
                d = v * pct / 100
            v = v + d if op == "+" else v - d
        return v

    def produto(self):
        v, pct = self.unario()
        while True:
            tk = self.ver()
            if tk in (("op", "×"), ("op", "÷"), ("op", "mod")):
                op = self.pega()[1]
                d, _ = self.unario()
                if op == "×":
                    v = v * d
                elif d == 0:
                    raise ErroConta("Divisão por zero")
                elif op == "÷":
                    v = v / d
                else:
                    v = v % d
                pct = None
            elif tk[0] == "n" or tk in (("op", "("), ("op", "π"), ("op", "√")):
                d, _ = self.unario()  # multiplicacao implicita: 2π, 3(4+1)
                v, pct = v * d, None
            else:
                return v, pct

    def unario(self):
        tk = self.ver()
        if tk == ("op", "-"):
            self.pega()
            v, pct = self.unario()
            return -v, (-pct if pct is not None else None)
        if tk == ("op", "+"):
            self.pega()
            return self.unario()
        if tk == ("op", "√"):
            self.pega()
            v, _ = self.unario()
            if v < 0:
                raise ErroConta("Raiz de número negativo")
            return v.sqrt(), None
        return self.posfixo()

    def posfixo(self):
        v = self.primario()
        pct = None
        while True:
            tk = self.ver()
            if tk == ("op", "²"):
                self.pega()
                v, pct = v * v, None
            elif tk == ("op", "^"):
                self.pega()
                e, _ = self.unario()
                if e != e.to_integral_value() or abs(e) > 1000:
                    raise ErroConta("Expoente inválido")
                v, pct = v ** int(e), None
            elif tk == ("op", "%"):
                self.pega()
                v, pct = v / 100, v
            else:
                return v, pct

    def primario(self):
        tk = self.pega()
        if tk[0] == "n":
            return tk[1]
        if tk == ("op", "π"):
            return PI
        if tk == ("op", "("):
            v = self.soma()
            if self.ver() == ("op", ")"):
                self.pega()
            return v  # parentese aberto no final e aceito
        raise ErroConta("Expressão incompleta")


def calcula(texto):
    return Parser(tokeniza(texto)).conta()


def formata(v):
    if v == v.to_integral_value() and abs(v) < Decimal("1e15"):
        s = str(v.quantize(Decimal(1)))
    else:
        s = f"{v.quantize(Decimal('1e-10')):f}".rstrip("0").rstrip(".") if abs(v) < Decimal("1e15") else f"{v:.6E}"
    if s in ("-0", ""):
        s = "0"
    return s.replace(".", ",")


def bonita(expr):
    return (expr.replace("*", "×").replace("/", "÷").replace("-", "−").replace(".", ","))


# ---------------------------------------------------------------- tela
class Calculadora(Gtk.Window):
    def __init__(self):
        super().__init__(title="Calculadora")
        self.set_default_size(560, 640)
        self.desfazer_pilha = []
        self.recem_calculado = False

        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(caixa)

        # topo
        topo = Gtk.Box(spacing=6)
        topo.get_style_context().add_class("topo")
        b_desf = Gtk.Button(label="↶  Desfazer")
        b_desf.set_can_focus(False)
        b_desf.connect("clicked", lambda *_: self.desfazer())
        titulo = Gtk.Label(label="Calculadora")
        titulo.get_style_context().add_class("titulo")
        b_limpa_hist = Gtk.Button(label="Limpar histórico (Ctrl+L)")
        b_limpa_hist.set_can_focus(False)
        b_limpa_hist.connect("clicked", lambda *_: self.limpa_historico())
        b_fecha = Gtk.Button(label="✕")
        b_fecha.set_can_focus(False)
        b_fecha.get_style_context().add_class("fechar")
        b_fecha.connect("clicked", lambda *_: self.sair())
        topo.pack_start(b_desf, False, False, 0)
        topo.set_center_widget(titulo)
        topo.pack_end(b_fecha, False, False, 0)
        topo.pack_end(b_limpa_hist, False, False, 0)
        caixa.pack_start(topo, False, False, 0)

        # historico
        self.lista = Gtk.ListBox()
        self.lista.set_selection_mode(Gtk.SelectionMode.NONE)
        self.lista.set_valign(Gtk.Align.END)
        self.lista.connect("row-activated", self.usa_linha)
        self.rolagem = Gtk.ScrolledWindow()
        self.rolagem.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.rolagem.get_style_context().add_class("painel")
        self.rolagem.add(self.lista)
        caixa.pack_start(self.rolagem, True, True, 0)

        # visor
        self.visor = Gtk.Entry()
        self.visor.get_style_context().add_class("visor")
        self.visor.connect("activate", lambda *_: self.igual())
        self.visor.connect("changed", lambda *_: self.erro.set_text(""))
        caixa.pack_start(self.visor, False, False, 0)
        self.erro = Gtk.Label(xalign=0)
        self.erro.get_style_context().add_class("erro")
        caixa.pack_start(self.erro, False, False, 0)

        # teclas
        grade = Gtk.Grid(row_spacing=8, column_spacing=8,
                         row_homogeneous=True, column_homogeneous=True)
        grade.get_style_context().add_class("teclas")
        teclas = [
            ("C", 0, 0, ""), ("(", 1, 0, ""), (")", 2, 0, ""), ("mod", 3, 0, ""), ("π", 4, 0, ""),
            ("7", 0, 1, "num"), ("8", 1, 1, "num"), ("9", 2, 1, "num"), ("÷", 3, 1, ""), ("√", 4, 1, ""),
            ("4", 0, 2, "num"), ("5", 1, 2, "num"), ("6", 2, 2, "num"), ("×", 3, 2, ""), ("x²", 4, 2, ""),
            ("1", 0, 3, "num"), ("2", 1, 3, "num"), ("3", 2, 3, "num"), ("−", 3, 3, ""),
            ("0", 0, 4, "num"), (",", 1, 4, ""), ("%", 2, 4, ""), ("+", 3, 4, ""),
        ]
        for rot, x, y, cls in teclas:
            b = Gtk.Button(label=rot)
            b.set_can_focus(False)
            if cls:
                b.get_style_context().add_class(cls)
            b.connect("clicked", self.clique, rot)
            grade.attach(b, x, y, 1, 1)
        b_igual = Gtk.Button(label="=")
        b_igual.set_can_focus(False)
        b_igual.get_style_context().add_class("igual")
        b_igual.connect("clicked", lambda *_: self.igual())
        grade.attach(b_igual, 4, 3, 1, 2)
        caixa.pack_start(grade, False, False, 0)
        dicas = Gtk.Label(label="Enter = calcula   ↑↓ = histórico   Del = limpa   "
                                "Ctrl+L = limpa histórico   Ctrl+Z = desfaz   Esc = fecha")
        dicas.get_style_context().add_class("dicas")
        caixa.pack_start(dicas, False, False, 0)
        self.nav = None

        self.connect("key-press-event", self.tecla)
        self.connect("destroy", Gtk.main_quit)
        self.carrega_historico()
        self.visor.grab_focus()

    # ---- historico
    def carrega_historico(self):
        try:
            with open(HISTORICO) as f:
                itens = json.load(f)[-MAX_HISTORICO:]
        except (OSError, ValueError):
            itens = []
        self.historico = itens
        for expr, res in itens:
            self.adiciona_linha(expr, res)
        GLib.idle_add(self.rola_fim)

    def salva_historico(self):
        try:
            with open(HISTORICO, "w") as f:
                json.dump(self.historico[-MAX_HISTORICO:], f)
        except OSError:
            pass

    def limpa_historico(self):
        self.desmarca()
        self.historico = []
        for row in self.lista.get_children():
            self.lista.remove(row)
        self.salva_historico()
        self.visor.grab_focus_without_selecting()

    def adiciona_linha(self, expr, res):
        g = Gtk.Grid(column_homogeneous=True)
        for i, (txt, cls, xa) in enumerate(((expr, "", 0), ("=", "igual", 0.5), (res, "resultado", 1))):
            lb = Gtk.Label(label=txt, xalign=xa)
            lb.set_ellipsize(3 if i == 0 else 0)
            if cls:
                lb.get_style_context().add_class(cls)
            g.attach(lb, i, 0, 1, 1)
        row = Gtk.ListBoxRow()
        row.set_can_focus(False)
        row.resultado = res
        row.add(g)
        row.show_all()
        self.lista.add(row)

    def rola_fim(self):
        adj = self.rolagem.get_vadjustment()
        adj.set_value(adj.get_upper())
        return False

    def usa_linha(self, _lista, row):
        self.insere(row.resultado)

    # ---- historico pelo teclado
    def desmarca(self):
        for row in self.lista.get_children():
            row.get_style_context().remove_class("marcada")
        self.nav = None

    def navega(self, passo):
        linhas = self.lista.get_children()
        if not linhas:
            return
        if self.nav is None:
            self.nav = len(linhas) if passo < 0 else len(linhas) - 1
        i = self.nav + passo
        if i >= len(linhas):  # passou do fim: volta pro visor vazio
            self.desmarca()
            self.visor.set_text("")
            return
        i = max(0, i)
        self.desmarca()
        self.nav = i
        linhas[i].get_style_context().add_class("marcada")
        adj = self.rolagem.get_vadjustment()
        alloc = linhas[i].get_allocation()
        if alloc.y < adj.get_value():
            adj.set_value(alloc.y)
        elif alloc.y + alloc.height > adj.get_value() + adj.get_page_size():
            adj.set_value(alloc.y + alloc.height - adj.get_page_size())
        self.guarda()
        self.visor.set_text(linhas[i].resultado)
        self.visor.set_position(-1)
        self.recem_calculado = True

    # ---- edicao
    def guarda(self):
        txt = self.visor.get_text()
        if not self.desfazer_pilha or self.desfazer_pilha[-1] != txt:
            self.desfazer_pilha.append(txt)

    def desfazer(self):
        if self.desfazer_pilha:
            self.visor.set_text(self.desfazer_pilha.pop())
            self.visor.set_position(-1)
        self.visor.grab_focus_without_selecting()

    def insere(self, txt):
        self.desmarca()
        self.guarda()
        if self.recem_calculado and (txt[0] in DIGITOS or txt in (",", "π", "√", "(")):
            self.visor.set_text("")  # comeca conta nova depois do =
        self.recem_calculado = False
        self.visor.grab_focus_without_selecting()
        pos = self.visor.get_position()
        self.visor.insert_text(txt, pos)
        self.visor.set_position(pos + len(txt))

    def clique(self, _b, rot):
        if rot == "C":
            self.limpa()
        elif rot == "x²":
            self.insere("²")
        else:
            self.insere(rot)

    def limpa(self):
        self.guarda()
        self.visor.set_text("")
        self.recem_calculado = False
        self.visor.grab_focus_without_selecting()

    def igual(self):
        expr = self.visor.get_text().strip()
        if not expr:
            return
        try:
            res = formata(calcula(expr))
        except ErroConta as e:
            self.erro.set_text(str(e) or "Expressão inválida")
            return
        except (InvalidOperation, OverflowError, ZeroDivisionError):
            self.erro.set_text("Resultado inválido")
            return
        self.desmarca()
        self.guarda()
        expr_b = bonita(expr)
        self.historico.append([expr_b, res])
        self.salva_historico()
        self.adiciona_linha(expr_b, res)
        GLib.idle_add(self.rola_fim)
        self.visor.set_text(res)
        self.visor.set_position(-1)
        self.recem_calculado = True

    def tecla(self, _w, ev):
        k = Gdk.keyval_name(ev.keyval) or ""
        ctrl = ev.state & Gdk.ModifierType.CONTROL_MASK
        if k == "Escape":
            self.sair()
        elif k in ("Return", "KP_Enter", "equal", "KP_Equal"):
            self.igual()
        elif ctrl and (k.lower() == "l" or k in ("Delete", "KP_Delete")):
            self.limpa_historico()
        elif k in ("Up", "KP_Up"):
            self.navega(-1)
        elif k in ("Down", "KP_Down"):
            self.navega(1)
        elif k == "Delete" and not self.visor.get_selection_bounds():
            self.desmarca()
            self.limpa()
        elif ctrl and k.lower() == "z":
            self.desfazer()
        elif ctrl:
            return False
        elif k in ("KP_Decimal", "KP_Separator", "period", "comma"):
            self.insere(",")
        elif k in ("asterisk", "KP_Multiply"):
            self.insere("×")
        elif k in ("slash", "KP_Divide"):
            self.insere("÷")
        elif k in ("minus", "KP_Subtract"):
            self.insere("−")
        elif k in ("plus", "KP_Add"):
            self.insere("+")
        elif k == "BackSpace":
            self.recem_calculado = False
            self.guarda()
            return False
        elif ev.string and ev.string.isprintable() and len(ev.string) == 1:
            self.insere(ev.string)
        else:
            return False
        return True

    def sair(self):
        self.destroy()


def main():
    if "--teste" in sys.argv:
        for e, esperado in [("10+10", "20"), ("4587-45", "4542"), ("200+10%", "220"),
                            ("200-10%", "180"), ("200×10%", "20"), ("1,5*2", "3"),
                            ("10÷3", "3,3333333333"), ("√16+3²", "13"), ("2(3+1)", "8"),
                            ("7 mod 3", "1"), ("-5+2", "-3"), ("0,1+0,2", "0,3")]:
            r = formata(calcula(e))
            print(("OK " if r == esperado else "ERRO"), e, "=", r)
        return
    prov = Gtk.CssProvider()
    prov.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
    Calculadora().show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
