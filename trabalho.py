# =====================================================================
# SIMULADOR DA MÁQUINA NORMA (MRN) — VERSÃO COMPACTA
# Só funções, listas e dicionários.
#   Módulo 1: memória  | Módulo 2: motor  | Módulo 3: macros  | Módulo 4: terminal
# Executar:  python trabalho.py    (ou: python trabalho.py arquivo.norma)
# =====================================================================
import sys


# ============ MÓDULO 1 — MEMÓRIA ============
# Registradores num dicionário: {"A": 5, "B": 3}. Só existem quando usados.
# O int do Python não tem limite de tamanho (números grandes).

def ler(mem, r):                 # registrador nunca usado vale 0
    return mem.get(r, 0)

def inc(mem, r):                 # INC R
    mem[r] = ler(mem, r) + 1

def dec(mem, r):                 # DEC R protegido: se R = 0, não faz nada
    if ler(mem, r) > 0:
        mem[r] = mem[r] - 1

def definir(mem, r, valor):      # carga inicial (comando "set")
    if not (r.isalnum() and r.isupper() and r[0].isalpha()):
        raise Exception(f"Registrador inválido: '{r}' (use letras maiúsculas).")
    if valor < 0:
        raise Exception("Só são aceitos valores naturais (>= 0).")
    mem[r] = valor

def texto_regs(mem):             # ex.: "A=8  B=3  C=0"
    if len(mem) == 0:
        return "(nenhum registrador em uso)"
    return "  ".join(r + "=" + str(mem[r]) for r in sorted(mem))


# ============ MÓDULO 2 — MOTOR ============
# Programa = lista de instruções, ex.: ["TST", "A", "L1", "L2"]
# Rótulos  = dicionário {"L1": 0, "L2": 3} (rótulo -> posição)

def compilar(linhas):            # linhas só com INC/DEC/TST -> (prog, rotulos)
    prog = []
    rotulos = {}
    for linha in linhas:
        pos = linha.find(":")                  # "rótulo: instrução"
        if pos != -1:
            nome = linha[:pos].strip()
            if nome in rotulos:
                raise Exception(f"Rótulo repetido: {nome}")
            rotulos[nome] = len(prog)
            linha = linha[pos + 1:].strip()
        if linha == "":
            continue                           # linha só com rótulo
        p = linha.split()
        p[0] = p[0].upper()
        if not ((p[0] in ("INC", "DEC") and len(p) == 2) or (p[0] == "TST" and len(p) == 4)):
            raise Exception(f"Instrução inválida: {linha}")
        prog.append(p)

    if "FIM" not in rotulos:                   # FIM implícito: encerra o programa
        rotulos["FIM"] = len(prog)
    for p in prog:
        if p[0] == "TST" and (p[2] not in rotulos or p[3] not in rotulos):
            raise Exception(f"Rótulo não existe em: {' '.join(p)}")
    return prog, rotulos

def passo(prog, rotulos, mem, ip):             # executa UMA instrução; devolve o novo IP
    p = prog[ip]
    if p[0] == "INC":
        inc(mem, p[1])
        return ip + 1
    if p[0] == "DEC":
        dec(mem, p[1])
        return ip + 1
    if ler(mem, p[1]) == 0:                    # TST R L_ZERO L_NON_ZERO
        return rotulos[p[2]]
    return rotulos[p[3]]

def executar(prog, rotulos, mem, ip, ciclos, limite):   # devolve (ip, ciclos)
    while ip < len(prog) and ciclos < limite:  # para ao terminar ou no limite
        ip = passo(prog, rotulos, mem, ip)
        ciclos = ciclos + 1
    return ip, ciclos


# ============ MÓDULO 3 — MACROS ============
# Cada macro devolve uma LISTA de linhas só com INC/DEC/TST.
# Macros: ZER R | A := A + B | A := A .- B | C := A * B | Q := A div B | R := A mod B
# Reservados: C (auxiliar da soma/subtração), T0, T1, T2, T3. Auxiliares começam em 0.

contador = 0                     # para criar rótulos diferentes (_L0, _L1, ...)

def novo():
    global contador
    contador = contador + 1
    return "_L" + str(contador - 1)

def goto(rotulo):                # desvio incondicional
    return "TST T0 " + rotulo + " " + rotulo

def esvazia(r, corpo):           # "enquanto R != 0: DEC R e repete o corpo"
    ini, fim, d = novo(), novo(), novo()
    return ([ini + ": TST " + r + " " + fim + " " + d,    # R = 0 ? sai : continua
             d + ": DEC " + r] + corpo + [goto(ini), fim + ":"])

def zer(r):                      # ZER R
    return esvazia(r, [])

def soma(a, b, c):               # A := A + B (B vai para A e C; depois C volta para B)
    return esvazia(b, ["INC " + a, "INC " + c]) + esvazia(c, ["INC " + b])

def subtracao(a, b, c):          # A := A .- B (o DEC protegido segura A em 0)
    return esvazia(b, ["DEC " + a, "INC " + c]) + esvazia(c, ["INC " + b])

def multiplicacao(c, a, b):      # C := A * B (soma B em C, A vezes; T1 guarda A)
    return (zer(c)
            + esvazia(a, ["INC T1"] + soma(c, b, "T2"))
            + esvazia("T1", ["INC " + a]))

def divisao(a, b, q, r):         # Q := A div B e R := A mod B; A e B ficam intactos
    loop, passo_, d, ok, falha, fim, zero = novo(), novo(), novo(), novo(), novo(), novo(), novo()
    linhas = zer(q) + zer(r) + soma(r, a, "T1")           # Q = 0, R = 0, R := A
    linhas.append("TST " + b + " " + zero + " " + loop)   # B = 0 ? divisão por zero
    linhas.append(zero + ":")                             # divisão por zero: R = 0
    linhas = linhas + zer(r) + [goto(fim)]
    # tenta tirar B inteiro de R (T2 conta quanto já foi tirado)
    linhas.append(loop + ": TST " + b + " " + ok + " " + passo_)      # B zerou: coube
    linhas.append(passo_ + ": TST " + r + " " + falha + " " + d)      # R zerou antes: não coube
    linhas = linhas + [d + ": DEC " + r, "DEC " + b, "INC T2", goto(loop)]
    # coube: devolve B, soma 1 em Q e tenta de novo
    linhas = linhas + [ok + ":"] + esvazia("T2", ["INC " + b]) + ["INC " + q, goto(loop)]
    # não coube: devolve o que tirou; o que sobrou em R é o resto
    linhas = linhas + [falha + ":"] + esvazia("T2", ["INC " + r, "INC " + b]) + [fim + ":"]
    return linhas

def atribuicao(dest, x, op, y):  # escolhe a macro de "X := Y op Z"
    if op == "+" or op == ".-":
        if x != dest:
            raise Exception(f"Use o formato: {dest} := {dest} {op} B")
        return soma(dest, y, "C") if op == "+" else subtracao(dest, y, "C")
    if op == "*":
        return multiplicacao(dest, x, y)
    if op == "div":
        return divisao(x, y, dest, "T3")      # quociente em dest
    if op == "mod":
        return divisao(x, y, "T3", dest)      # resto em dest
    raise Exception(f"Operador desconhecido: {op} (use +, .-, *, div, mod)")

def expandir(texto):             # texto com macros -> linhas só com INC/DEC/TST
    global contador
    contador = 0
    saida = []
    for bruta in texto.splitlines():
        linha = bruta.split("//")[0].split("#")[0].strip()    # tira comentários
        if linha == "":
            continue
        pos = linha.find(":")                  # rótulo do usuário (":=" não conta)
        if pos != -1 and linha[pos + 1:pos + 2] != "=":
            saida.append(linha[:pos].strip() + ":")
            linha = linha[pos + 1:].strip()
            if linha == "":
                continue
        p = linha.split()
        if p[0].upper() == "ZER" and len(p) == 2:
            saida = saida + zer(p[1])
        elif len(p) == 5 and p[1] == ":=":
            saida = saida + atribuicao(p[0], p[2], p[3].lower(), p[4])
        else:
            saida.append(linha)                # já é INC / DEC / TST
    return saida


# ============ MÓDULO 4 — TERMINAL ============

def roda(fonte, entrada):        # expande, compila e executa com memória própria
    mem = {}
    for par in entrada.split():
        nome, valor = par.split("=")
        definir(mem, nome, int(valor))
    prog, rotulos = compilar(expandir(fonte))
    ip, ciclos = executar(prog, rotulos, mem, 0, 0, 50000000)
    return mem

def testes():                    # bateria obrigatória TC-01 a TC-04
    casos = [("TC-01", "A := A + B", "A=5 B=3 C=0", "A=8 B=3 C=0"),
             ("TC-02", "A := A .- B", "A=3 B=5", "A=0"),
             ("TC-03", "C := A * B", "A=4 B=3 C=0", "A=4 B=3 C=12"),
             ("TC-04", "Q := A div B\nR := A mod B", "A=14 B=3", "Q=4 R=2")]
    for nome_caso, fonte, entrada, esperado in casos:
        mem = roda(fonte, entrada)
        resultado = "OK"
        for par in esperado.split():
            nome, valor = par.split("=")
            if ler(mem, nome) != int(valor):
                resultado = "FALHOU"
        print(f"{nome_caso}  entrada: {entrada:<13} esperado: {esperado:<13} "
              f"obtido: {texto_regs(mem)}  -> {resultado}")

# Estado da máquina carregada
regs = {}                        # registradores
prog = []                        # instruções
rotulos = {}                     # rótulos
ip = 0                           # ponteiro de instruções
ciclos = 0                       # instruções executadas
limite = 100000                  # trava contra loop infinito
carregado = False

print("=== Simulador da Máquina Norma ===")
print("Comandos: carregar, set, regs, listar, step, run, limite, reset, testes, sair")
pendentes = []
if len(sys.argv) > 1:
    pendentes.append("carregar " + sys.argv[1])

while True:
    if len(pendentes) > 0:
        linha = pendentes.pop(0)
    else:
        try:
            linha = input("norma> ").strip()
        except EOFError:    #caso raro caso de erro tipo alguem digitar Ctrl + z
            break
    if linha == "sair":
        break
    if linha == "":
        continue
    p = linha.split()
    cmd = p[0].lower()   #converte o que foi digitado para minusculas

    if cmd in ("listar", "step", "run") and not carregado:
        print("Nenhum programa carregado. Use: carregar <arquivo>")
        continue

    try:
        if cmd == "carregar":
            arquivo = open(linha[len(p[0]):].strip().strip('"'), encoding="utf-8")
            texto = arquivo.read()
            arquivo.close()
            prog, rotulos = compilar(expandir(texto))
            ip = 0
            ciclos = 0
            carregado = True
            print(f"Programa carregado: {len(prog)} instruções.")

        elif cmd == "set":                         # set A 5 B 3 C 0
            if len(p) < 3 or len(p) % 2 == 0:
                raise Exception("Uso: set A 5 [B 3 ...]")
            for i in range(1, len(p), 2):
                definir(regs, p[i], int(p[i + 1]))
            print(f"IP={ip}  ciclos={ciclos}  limite={limite}\nRegistradores: {texto_regs(regs)}")

        elif cmd == "regs":
            print(f"IP={ip}  ciclos={ciclos}  limite={limite}\nRegistradores: {texto_regs(regs)}")

        elif cmd == "listar":                      # ">" marca a instrução atual
            for i in range(len(prog)):
                marca = "> " if i == ip else "  "
                nomes = " ".join(n for n in rotulos if rotulos[n] == i)
                print(marca + str(i).rjust(3) + "  " + nomes.ljust(12) + " ".join(prog[i]))

        elif cmd == "step":                        # step [n]
            qtd = int(p[1]) if len(p) > 1 else 1
            for i in range(qtd):
                if ip >= len(prog):
                    print("Programa terminou.")
                    break
                if ciclos >= limite:
                    print(f"Limite de {limite} ciclos atingido (possível loop infinito).")
                    break
                antes = ip
                ip = passo(prog, rotulos, regs, ip)
                ciclos = ciclos + 1
                print(f"IP {antes}: {' '.join(prog[antes])}   | {texto_regs(regs)}")

        elif cmd == "run":
            ip, ciclos = executar(prog, rotulos, regs, ip, ciclos, limite)
            if ip < len(prog):
                print(f"Limite de {limite} ciclos atingido (possível loop infinito).")
            else:
                print("Programa terminou.")
            print(f"IP={ip}  ciclos={ciclos}  limite={limite}\nRegistradores: {texto_regs(regs)}")

        elif cmd == "limite":
            limite = int(p[1])
            print(f"Limite de ciclos = {limite}")

        elif cmd == "reset":                       # zera registradores, IP e ciclos
            regs.clear()
            ip = 0
            ciclos = 0
            print("Tudo zerado.")

        elif cmd == "testes":
            testes()

        else:
            print(f"Comando desconhecido: {p[0]}")

    except Exception as erro:
        print("Erro:", erro)