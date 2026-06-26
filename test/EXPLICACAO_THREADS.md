# Setor THREADS — Explicação técnica

## Onde as threads foram usadas

### Servidor (`server.py`)
- A thread principal só executa `sock.accept()` em loop — nunca conversa
  diretamente com um cliente.
- A cada `accept()`, uma **nova `threading.Thread`** é criada executando
  `atender_cliente(conn, endereco)`. Essa thread fica dedicada a UM único
  cliente durante toda a vida da conexão.
- Resultado: o `recv()` bloqueante de um cliente nunca impede o servidor
  de aceitar outro cliente, nem de continuar atendendo os clientes já
  conectados.
- `threads_ativas` + `lock_threads` (um `threading.Lock`) servem só para
  registrar/demonstrar quantos atendimentos estão rodando em paralelo a
  qualquer momento (visível no log do servidor).

### Cliente (`client.py`)
- A thread principal cuida do `menu()`, que usa `input()` — uma chamada
  bloqueante por natureza, pois espera o usuário digitar.
- Uma thread separada (`listen`) só fica em loop fazendo `sock.recv()` e
  empilhando cada mensagem recebida numa `queue.Queue` (`fila_recebidas`).
- Antes de cada exibição do menu, a thread principal drena a fila e
  mostra na tela tudo que o servidor mandou nesse meio tempo
  (`mostrar_mensagens_pendentes()`).
- Um `threading.Event` (`conectado`) substitui a antiga variável global
  mal utilizada, permitindo que as duas threads decidam, de forma segura,
  quando a conexão deve terminar.

## Por que essa abordagem

- **Thread por conexão no servidor** é o jeito mais direto de cumprir a
  exigência "atender mais de um cliente... sem bloqueio grosseiro" sem
  reescrever o protocolo (que é responsabilidade do setor BASE).
  Para a escala de um projeto acadêmico (poucos clientes simultâneos),
  thread-per-connection é simples de explicar e de demonstrar.
- **Fila entre threads no cliente** evita race conditions: como
  `queue.Queue` já é thread-safe, não precisamos de locks manuais para
  passar dados entre a thread de rede e a thread de interface. A
  alternativa mais simples (uma thread só de recepção, sem fila) faria a
  thread de rede chamar `print()` por conta própria, o que embaralharia
  a saída com o `input()` do usuário — por isso a fila + drenagem
  controlada na hora certa.

## Pontos deixados explicitamente para outros setores (TODOs no código)

- **AUTENTICAÇÃO/PERMISSÕES**: validação de login antes de processar
  comandos, e liberação de `menu_admin()`.
- **SEGURANÇA**: onde entram criptografia/descriptografia no fluxo de
  `recv`/`sendall`.
- **PROCESSAMENTO LENTO/MULTIPROCESSING**: comandos pesados devem rodar
  em `multiprocessing.Process` dentro de `processar_requisicao()`, não
  diretamente na thread do cliente.
- **TOLERÂNCIA A FALHAS**: o `except` em `atender_cliente()` cobre só o
  básico (conexão perdida); falhas de protocolo, timeout, etc. devem ser
  expandidas por esse setor.
- **LOGS**: pontos de log já indicados em `processar_requisicao()`.

## Como testar a concorrência

O arquivo `teste_concorrencia.py` simula 3 clientes conectando ao mesmo
tempo: dois "rápidos" e um "lento" (2s de espera entre mensagens). Para
rodar:

```bash
# terminal 1
python3 server.py

# terminal 2
python3 teste_concorrencia.py
```

Resultado esperado: os clientes rápidos terminam em frações de segundo,
**sem esperar** o cliente lento, e o log do servidor mostra
`Threads ativas no momento: 3` em algum ponto da execução.
