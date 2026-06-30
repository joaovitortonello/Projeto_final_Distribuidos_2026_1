# Grupo 6: Processamento Lento e Multiprocessing
Acadêmicos:
- Alisson Rafael Siliprandi Haubert
- Ana Paula Ragievicz
- Samayra Calgaroto

Este módulo é o componente responsável pelo gerenciamento de tarefas computacionalmente intensivas e simulações de longa duração do sistema de delivery/lanchonete. Ele foi projetado seguindo princípios de alto desacoplamento e responsabilidade única, isolando toda a lógica de negócio pesada do servidor principal (`server.py`).

---

## Objetivos

1. **Evitar o Bloqueio da CPU:** Garantir que requisições administrativas pesadas (como relatórios macro) rodem em processos paralelos separados no Sistema Operacional, impedindo que o núcleo principal do servidor congele as threads de atendimento dos outros clientes.
2. **Fornecer Métricas de Tempo:** Mensurar e retornar o tempo exato (com precisão de milissegundos) gasto pelo processador para executar cada operação.
3. **Oferecer Ganchos de Integração:** Disponibilizar uma interface limpa (`despachar_processamento`) para que os setores de **Autenticação** e **Tolerância a Falhas** injetem suas respectivas regras de negócio e capturas de exceção.

---

## Funcionalidades e Contexto de Negócio

As operações implementadas utilizam o ecossistema e dados simulados de uma lanchonete/delivery:

### 1. Processamento Básico: `processamento_basico_motoboy`
* **Público-alvo:** Usuários Comuns / Clientes.
* **Contexto:** Simula uma estimativa estatística complexa do tempo de espera de entrega e cálculo de rotas de motoboys.
* **Mecanismo Técnico:** Utiliza loops intencionais de ponto flutuante para simular uma carga de processamento na CPU de forma sequencial na thread atual do cliente.

### 2. Processamento Avançado: `processamento_avancado_auditoria`
* **Público-alvo:** Administradores do Sistema.
* **Contexto:** Simula uma auditoria massiva de cupons fiscais emitidos pela lanchonete com projeção de faturamento macro e cálculo de ticket médio.
* **Mecanismo Técnico:** **Uso obrigatório do módulo `multiprocessing`** (através do `concurrent.futures.ProcessPoolExecutor`). O cálculo matemático pesado é despachado para um processo real do Sistema Operacional, liberando a concorrência de threads do servidor.

---

## Arquitetura de Integração

O módulo expõe a função principal:
```python
despachar_processamento(perfil_usuario: str, tipo_operacao: str, *args) -> str
```

* `perfil_usuario`: hoje vem de um *mock* feito pelo `server.py` (`"administrador"` se a
  palavra `admin` aparecer na mensagem recebida, `"usuario"` caso contrário) enquanto o
  setor de **Autenticação/Permissões** não está pronto. O `despachar_processamento` não
  sabe nem precisa saber de onde o perfil veio — só decide com base na string recebida.
* `tipo_operacao`: `"SIMULAR_ENTREGA"` (básico) ou `"AUDITORIA_VENDAS"` (avançado).
* `*args`: parâmetro numérico opcional (quantidade de pedidos / registros). Se omitido,
  usa um valor padrão razoável para demonstração.
* Retorno: sempre uma `str` pronta para ser enviada ao cliente pelo socket (texto
  formatado com tipo, detalhes e tempo de execução), ou levanta `PermissaoNegadaError`
  quando o perfil não tem permissão para a operação pedida.

---

## Protocolo usado na rede (como o `client.py` e o `server.py` conversam com este setor)

O cliente manda uma linha de texto pelo socket no formato:

```
CALCULO:<OPERACAO>|<PARAMETRO>
```

e, para simular um login de administrador (enquanto o setor de Autenticação não está
pronto), prefixa a mensagem com `admin `:

```
admin CALCULO:AUDITORIA_VENDAS|1000000
```

Exemplos reais enviados pelo `client.py` (opção `[4] processamento lento` do menu):

| Ação no menu | Mensagem enviada | Permissão exigida |
|---|---|---|
| 1 — Simular rota de entrega | `CALCULO:SIMULAR_ENTREGA|5` | qualquer usuário |
| 2 — Auditoria de vendas, sem marcar admin | `CALCULO:AUDITORIA_VENDAS|10000000` | nega (não-admin) |
| 2 — Auditoria de vendas, marcando admin | `admin CALCULO:AUDITORIA_VENDAS|10000000` | administrador |

No `server.py`, dentro de `processar_requisicao`, o trecho responsável por reconhecer e
despachar esse comando procura `"CALCULO:"` em qualquer posição do texto recebido — não
só no início — exatamente para reconhecer tanto `CALCULO:...` quanto `admin CALCULO:...`.

### Integração com o setor de Tolerância a Falhas

Quando um usuário sem permissão pede `AUDITORIA_VENDAS`, `despachar_processamento`
levanta `PermissaoNegadaError`. Esse erro **não é capturado dentro deste setor nem
dentro do `server.py`** — ele sobe até `tf.processar_requisicao_segura` (chamado em
`atender_cliente`, no `server.py`), que:

1. reconhece a exceção pelo nome da classe (contém `"Permiss"`);
2. registra o erro no log do setor de Tolerância a Falhas;
3. devolve ao cliente a resposta padronizada `ERRO|ERRO_PERMISSAO|mensagem`.

Assim o cliente já exibe a mensagem de forma amigável via
`tf.descrever_erro_para_usuario`, sem que este setor precise conhecer o protocolo de
erro de outro setor.

---

## Como testar

Na **raiz do projeto**:

```bash
# Teste dedicado deste setor (sobe o servidor de verdade e troca mensagens reais)
python3 test/teste_processamento_lento.py
```

O teste comprova, na ordem:

1. `SIMULAR_ENTREGA` funciona para um usuário comum;
2. `AUDITORIA_VENDAS` é **negada** para um usuário comum, no protocolo padrão
   `ERRO|ERRO_PERMISSAO|...` (prova de que a integração com Tolerância a Falhas
   funciona);
3. `AUDITORIA_VENDAS` é **aceita** para o perfil administrador e roda via
   `multiprocessing` (prova de que o cálculo pesado não é executado direto na thread);
4. o servidor continua respondendo **outros clientes leves** enquanto o cálculo pesado
   do administrador está em andamento em outro processo do sistema operacional — ou
   seja, threads (Setor Threads) e multiprocessing (este setor) trabalhando juntos sem
   travar ninguém.

### Demonstração manual rápida

```bash
# Terminal 1
python3 server.py

# Terminal 2
python3 client.py
# -> [4] processamento lento -> [1] (básico) ou [2] (avançado, testando S/N para admin)
```
