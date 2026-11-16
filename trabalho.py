# =====================================================================
# SIMULADOR DA MÁQUINA NORMA (MRN) — VERSÃO SIMPLES EM PYTHON
#
#   Memoria  -> Módulo 1: registradores, números grandes, DEC protegido
#   Maquina  -> Módulo 2: lê INC/DEC/TST e executa (IP, rótulos, ciclos)
#   Macros   -> Módulo 3: transforma ZER, +, .-, *, div, mod em INC/DEC/TST
#   Terminal -> Módulo 4: comandos, step, run, limite de ciclos
#
# Executar:  python norma.py            (ou: python norma.py arquivo.norma)
# =====================================================================

import re
import sys


# =====================================================================
# MÓDULO 1 — MEMÓRIA
# =====================================================================
class Memoria:
    def __init__(self):
        # nome do registrador -> valor. Só existe quando é usado
        # (alocação dinâmica). O int do Python não tem limite de tamanho.
        self.regs = {}

    # Nome precisa ser em letras maiúsculas (A, B, Q, R, AUX1...)
    def valida(self, nome):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", nome):
            raise Exception(f"Registrador inválido: '{nome}' (use letras maiúsculas).")

    # Registrador que nunca foi usado vale 0
    def ler(self, nome):
        self.valida(nome)
        return self.regs.get(nome, 0)

    # Carga inicial (comando "set"). Só aceita valores em N (>= 0).
    def definir(self, nome, valor):
        self.valida(nome)
        if valor < 0:
            raise Exception("Só são aceitos valores naturais (>= 0).")
        self.regs[nome] = valor

    # INC R: soma 1
    def inc(self, nome):
        self.regs[nome] = self.ler(nome) + 1

    # DEC R (DECREMENTO PROTEGIDO): só subtrai se R > 0; se for 0, ignora.
    def dec(self, nome):
        if self.ler(nome) > 0:
            self.regs[nome] -= 1

    def eh_zero(self, nome):
        return self.ler(nome) == 0

    def limpar(self):
        self.regs.clear()

    # Texto com os registradores ativos, ex.: "A=8  B=3  C=0"
    def texto(self):
        if not self.regs:
            return "(nenhum registrador em uso)"
        return "  ".join(f"{nome}={self.regs[nome]}" for nome in sorted(self.regs))


# =====================================================================
# MÓDULO 2 — MOTOR DE EXECUÇÃO
# =====================================================================
class Maquina:
    def __init__(self):
        self.mem = Memoria()
        self.instr = []        # ex.: ["TST", "A", "L1", "L2"]
        self.rot = {}          # rótulo -> índice da instrução
        self.ip = 0            # ponteiro de instruções
        self.ciclos = 0        # instruções executadas
        self.limite = 100000   # trava contra loop infinito

    def terminou(self):
        return self.ip >= len(self.instr)

    # Texto da instrução que será executada agora
    def atual(self):
        return "(fim)" if self.terminou() else " ".join(self.instr[self.ip])

    # Recebe linhas só com INC/DEC/TST (rótulo opcional: "L1: TST A L2 L3")
    def carregar(self, linhas):
        instr, rot = [], {}

        for linha in linhas:
            # Se a linha começa com "rótulo:", guarda onde ele aponta
            m = re.match(r"^([A-Za-z_]\w*)\s*:\s*(.*)$", linha)
            if m:
                if m.group(1) in rot:
                    raise Exception(f"Rótulo repetido: {m.group(1)}")
                rot[m.group(1)] = len(instr)
                linha = m.group(2)
            if linha == "":
                continue  # linha só com rótulo

            p = linha.split()
            p[0] = p[0].upper()
            valida = (p[0] in ("INC", "DEC") and len(p) == 2) or (p[0] == "TST" and len(p) == 4)
            if not valida:
                raise Exception(f"Instrução inválida: {linha}")
            instr.append(p)

        # FIM é um rótulo implícito: desviar para ele encerra o programa
        rot.setdefault("FIM", len(instr))

        # Todo rótulo usado em TST precisa existir
        for p in instr:
            if p[0] == "TST":
                for r in (p[2], p[3]):
                    if r not in rot:
                        raise Exception(f"Rótulo não existe: {r}")

        self.instr, self.rot = instr, rot
        self.reiniciar()

    def reiniciar(self):
        self.ip = 0
        self.ciclos = 0

    # Executa UMA instrução
    def passo(self):
        if self.terminou():
            return
        if self.ciclos >= self.limite:
            raise Exception(f"Limite de {self.limite} ciclos atingido (possível loop infinito).")

        p = self.instr[self.ip]

        if p[0] == "INC":
            self.mem.inc(p[1])
            self.ip += 1
        elif p[0] == "DEC":
            self.mem.dec(p[1])
            self.ip += 1
        else:  # TST R L_ZERO L_NON_ZERO
            destino = p[2] if self.mem.eh_zero(p[1]) else p[3]
            self.ip = self.rot[destino]

        self.ciclos += 1

    def executar(self):
        while not self.terminou():
            self.passo()


# =====================================================================
# MÓDULO 3 — MACROS
# Entrada: texto do usuário. Saída: lista de linhas só com INC/DEC/TST.
#
# Macros:  ZER R | A := A + B | A := A .- B | C := A * B
#          Q := A div B | R := A mod B
# Registradores reservados (uso interno): C (auxiliar da soma/subtração),
# T0, T1, T2, T3. Os auxiliares precisam começar em 0 e voltam a 0.
# =====================================================================
contador = 0  # para criar rótulos únicos (_L0, _L1, ...)


def novo_rotulo():
    global contador
    contador += 1
    return f"_L{contador - 1}"


def expandir(texto):
    global contador
    contador = 0
    o = []

    for bruta in texto.splitlines():
        # tira comentários (// ou #)
        linha = re.split(r"//|#", bruta)[0].strip()
        if linha == "":
            continue

        # rótulo do usuário no começo da linha (sem confundir com ":=")
        m = re.match(r"^([A-Za-z_]\w*)\s*:(?!=)\s*(.*)$", linha)
        if m:
            o.append(m.group(1) + ":")
            linha = m.group(2)
            if linha == "":
                continue

        p = linha.split()

        if p[0].upper() == "ZER" and len(p) == 2:
            zer(o, p[1])
        elif len(p) == 5 and p[1] == ":=":
            atribuicao(o, p[0], p[2], p[3].lower(), p[4])
        else:
            o.append(linha)  # já é INC / DEC / TST
    return o


def atribuicao(o, dest, x, op, y):
    if op in ("+", ".-"):
        if x != dest:
            raise Exception(f"Use o formato: {dest} := {dest} {op} B")
        if op == "+":
            soma(o, dest, y, "C")
        else:
            sub(o, dest, y, "C")
    elif op == "*":
        mult(o, dest, x, y)
    elif op == "div":
        divisao(o, x, y, dest, "T3")  # quociente em dest
    elif op == "mod":
        divisao(o, x, y, "T3", dest)  # resto em dest
    else:
        raise Exception(f"Operador desconhecido: {op} (use +, .-, *, div, mod)")


# Desvio incondicional: TST com os dois destinos iguais
def goto(o, rotulo):
    o.append(f"TST T0 {rotulo} {rotulo}")


# "Enquanto R != 0: DEC R e executa o corpo"  (base de todas as macros)
def esvazia(o, r, corpo):
    ini, fim, dec = novo_rotulo(), novo_rotulo(), novo_rotulo()
    o.append(f"{ini}: TST {r} {fim} {dec}")  # R == 0 ? sai : continua
    o.append(f"{dec}: DEC {r}")
    corpo()
    goto(o, ini)
    o.append(f"{fim}:")


# ZER R: esvazia R
def zer(o, r):
    esvazia(o, r, lambda: None)


# A := A + B (soma preservativa). Move B para A e para o auxiliar C,
# depois devolve C para B, para B ficar intacto.
def soma(o, a, b, c):
    esvazia(o, b, lambda: o.extend([f"INC {a}", f"INC {c}"]))
    esvazia(o, c, lambda: o.append(f"INC {b}"))


# A := A .- B (subtração monótona). O DEC protegido segura A em 0.
def sub(o, a, b, c):
    esvazia(o, b, lambda: o.extend([f"DEC {a}", f"INC {c}"]))
    esvazia(o, c, lambda: o.append(f"INC {b}"))


# C := A * B (soma B em C, A vezes). T1 guarda A para restaurar no fim.
def mult(o, c, a, b):
    zer(o, c)

    def corpo():
        o.append("INC T1")
        soma(o, c, b, "T2")

    esvazia(o, a, corpo)
    esvazia(o, "T1", lambda: o.append(f"INC {a}"))


# Q := A div B e R := A mod B (subtrações sucessivas). A e B ficam intactos.
# R começa como cópia de A. Enquanto der para tirar B de R: R -= B e Q++.
# T2 conta quanto de B já foi tirado nesta tentativa (para poder devolver).
def divisao(o, a, b, q, r):
    zer(o, q)
    zer(o, r)
    soma(o, r, a, "T1")  # R := A

    loop, passo, dec = novo_rotulo(), novo_rotulo(), novo_rotulo()
    ok, falha, fim, zero = novo_rotulo(), novo_rotulo(), novo_rotulo(), novo_rotulo()

    o.append(f"TST {b} {zero} {loop}")  # B == 0 ? divisão por zero

    # Divisão por zero: Q = 0 e R = 0
    o.append(f"{zero}:")
    zer(o, r)
    goto(o, fim)

    # Tenta tirar B inteiro de R
    o.append(f"{loop}: TST {b} {ok} {passo}")    # B zerou: tirou tudo
    o.append(f"{passo}: TST {r} {falha} {dec}")  # R zerou antes: não coube
    o.append(f"{dec}: DEC {r}")
    o.append(f"DEC {b}")
    o.append("INC T2")
    goto(o, loop)

    # Coube: devolve B, conta mais um no quociente e tenta de novo
    o.append(f"{ok}:")
    esvazia(o, "T2", lambda: o.append(f"INC {b}"))
    o.append(f"INC {q}")
    goto(o, loop)

    # Não coube: devolve o que tirou; o que sobrou em R é o resto
    o.append(f"{falha}:")
    esvazia(o, "T2", lambda: o.extend([f"INC {r}", f"INC {b}"]))

    o.append(f"{fim}:")


# =====================================================================
# MÓDULO 4 — INTERFACE (terminal)
# =====================================================================
maq = Maquina()
carregado = False


def mostra():
    print(f"IP={maq.ip}  ciclos={maq.ciclos}  limite={maq.limite}")
    print("Registradores:", maq.mem.texto())


def exige_programa():
    if not carregado:
        raise Exception("Nenhum programa carregado. Use: carregar <arquivo>")


# Mostra o programa (já expandido), com ">" na instrução atual
def listar():
    exige_programa()
    for i, p in enumerate(maq.instr):
        rotulos = ",".join(nome for nome, idx in maq.rot.items() if idx == i)
        print(("> " if i == maq.ip else "  ") + f"{i:4}  {rotulos:<12}" + " ".join(p))


# Expande, carrega, define os registradores ("A=5 B=3") e executa
def roda(fonte, entrada):
    m = Maquina()
    m.limite = 50_000_000
    m.carregar(expandir(fonte))
    for par in entrada.split():
        nome, valor = par.split("=")
        m.mem.definir(nome, int(valor))
    m.executar()
    return m


# Bateria obrigatória do enunciado: TC-01 a TC-04
def testes():
    casos = [
        ("TC-01", "A := A + B", "A=5 B=3 C=0", "A=8 B=3 C=0"),
        ("TC-02", "A := A .- B", "A=3 B=5", "A=0"),
        ("TC-03", "C := A * B", "A=4 B=3 C=0", "A=4 B=3 C=12"),
        ("TC-04", "Q := A div B\nR := A mod B", "A=14 B=3", "Q=4 R=2"),
    ]
    for id_, fonte, entrada, esperado in casos:
        m = roda(fonte, entrada)
        ok = all(m.mem.ler(nome) == int(valor)
                 for nome, valor in (par.split("=") for par in esperado.split()))
        print(f"{id_}  entrada: {entrada:<13} esperado: {esperado:<13} "
              f"obtido: {m.mem.texto()}  -> {'OK' if ok else 'FALHOU'}")


# Pergunta a operação, A e B, e executa PELO MOTOR (macros -> INC/DEC/TST)
def calc():
    fontes = ["A := A + B", "A := A .- B", "C := A * B", "Q := A div B\nR := A mod B"]
    op = input("Operação (1: A+B  2: A.-B  3: A*B  4: A div B e A mod B): ").strip()
    if op not in ("1", "2", "3", "4"):
        raise Exception("Operação inválida.")
    a = input("A = ").strip()
    b = input("B = ").strip()
    m = roda(fontes[int(op) - 1], f"A={a} B={b}")
    print(f"Resultado: {m.mem.texto()}   ({m.ciclos} ciclos)")


# Lê um comando e chama a função certa. Erros viram mensagem, sem fechar o programa.
def executa(linha):
    global carregado
    p = linha.split()
    cmd = p[0].lower()

    try:
        if cmd == "carregar":
            caminho = linha[len(p[0]):].strip().strip('"')
            with open(caminho, encoding="utf-8") as f:
                maq.carregar(expandir(f.read()))
            carregado = True
            print(f"Programa carregado: {len(maq.instr)} instruções.")

        elif cmd == "set":  # set A 5 B 3 C 0
            if len(p) < 3 or len(p) % 2 == 0:
                raise Exception("Uso: set A 5 [B 3 ...]")
            for i in range(1, len(p), 2):
                maq.mem.definir(p[i], int(p[i + 1]))
            mostra()

        elif cmd == "regs":
            mostra()

        elif cmd == "listar":
            listar()

        elif cmd == "step":  # step [n]
            exige_programa()
            qtd = int(p[1]) if len(p) > 1 else 1
            for _ in range(qtd):
                if maq.terminou():
                    break
                ip, texto = maq.ip, maq.atual()
                maq.passo()
                print(f"IP {ip}: {texto}   | {maq.mem.texto()}")
            if maq.terminou():
                print("Programa terminou.")

        elif cmd == "run":
            exige_programa()
            try:
                maq.executar()
                print("Programa terminou.")
            except Exception as e:
                print(e)  # trava anti-loop
            mostra()

        elif cmd == "limite":
            maq.limite = int(p[1])
            print(f"Limite de ciclos = {maq.limite}")

        elif cmd == "reset":  # zera registradores, IP e ciclos
            maq.mem.limpar()
            maq.reiniciar()
            print("Tudo zerado.")

        elif cmd == "testes":
            testes()

        elif cmd == "calc":
            calc()

        else:
            print(f"Comando desconhecido: {p[0]}")

    except Exception as e:
        print("Erro:", e)


def main():
    print("=== Simulador da Máquina Norma ===")
    print("Comandos: carregar, set, regs, listar, step, run, limite, reset, testes, calc, sair")

    if len(sys.argv) > 1:
        executa("carregar " + sys.argv[1])

    while True:
        try:
            linha = input("norma> ").strip()
        except EOFError:
            break
        if linha == "sair":
            break
        if linha:
            executa(linha)


if __name__ == "__main__":
    main()