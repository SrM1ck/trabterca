# Simulador da Máquina Norma (MRN)
Trabalho prático de Análise de Computabilidade e Complexidade de Algoritmos

# Sobre
Simulador da Máquina de Registradores Norma, escrito em Python. Executa as
instruções INC, DEC (decremento protegido) e TST, e expande macros de alto nível
(ZER, soma, subtração, multiplicação, divisão e resto).
## Requisitos
- Python 3.8 ou superior. Não precisa instalar nenhuma biblioteca.
## Como executar:
### Opção 1: pelo terminal
Na pasta do projeto, abra o terminal e rode:

    python trabalho.py

Para já abrir com um programa carregado:

    python trabalho.py exemplos/tc01.norma

(Em alguns computadores o comando pde até ser `py` ou `python3`.)

### Opção 2: por uma IDE (PyCharm foi a usada nesse projeto por exemplo)
1. Abra o PyCharm e vá em **File > Open**. Escolha a pasta do projeto.
2. Abra o arquivo `trabalho.py`.
3. Clique com o botão direito no código e escolha **Run 'trabalho'** (ou
   aperte `Shift+F10`).
4. Na janela **Run**, na parte de baixo, aparece o prompt `norma>`. Clique
   dentro dessa janela e digite os comandos, apertando Enter.

Para já abrir com um programa carregado, vá em **Run > Edit Configurations** e
escreva `exemplos/tc01.norma` no campo **Parameters**.
## Comandos
| Comando | O que faz |
|---|---|
| `carregar <arquivo>` | Carrega um arquivo `.norma` ou `.txt` |
| `set A 5 B 3 C 0` | Define o valor dos registradores |
| `regs` | Mostra IP, ciclos e registradores |
| `listar` | Mostra o programa expandido, com `>` na instrução atual |
| `step [n]` | Executa n instruções (padrão 1), mostrando o estado |
| `run` | Executa até terminar ou até o limite de ciclos |
| `limite <n>` | Define o limite de ciclos (proteção contra loop infinito) |
| `reset` | Zera registradores, IP e ciclos |
| `testes` | Roda os 4 casos de teste obrigatórios (TC-01 a TC-04) |
| `sair` | Encerra |
## Exemplo de uso (TC-01)

    norma> carregar exemplos/tc01.norma
    norma> set A 5 B 3 C 0
    norma> run
    Registradores: A=8  B=3  C=0
## Linguagem dos programas (.norma)
Instruções primitivas, uma por linha, com rótulo opcional:

    INC R
    DEC R
    L1: TST R L_ZERO L_NON_ZERO

Macros:

    ZER R
    A := A + B        (soma preservativa, auxiliar C)
    A := A .- B       (subtração monótona, auxiliar C)
    C := A * B
    Q := A div B
    R := A mod B

Regras:
- Registradores em letras maiúsculas.
- O auxiliar `C` deve começar em 0.
- `T0`, `T1`, `T2` e `T3` são reservados para uso interno das macros.
- Divisão por zero termina com Q = 0 e R = 0.

## Estrutura do código (trabalho.py)
- Módulo 1: memória e registradores (DEC protegido)
- Módulo 2: motor de execução (INC, DEC, TST, IP e rótulos)
- Módulo 3: expansão de macros
- Módulo 4: terminal, passo a passo e trava de ciclos
## Testes
No simulador, digite `testes`. Os 4 casos do enunciado devem aparecer como OK.