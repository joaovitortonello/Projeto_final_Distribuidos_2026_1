# Grupo 6: Processamento Lento e Multiprocessing
Acadêmicos:
- Alisson Rafael Siliprandi Haubert
- Ana Paula Ragievicz
- Samayra Calgaroto

Este módulo é o componente responsável pelo gerenciamento de tarefas computacionalmente intensivas e simulações de longa duração do sistema de delivery/lanchonete. Ele foi projetado seguindo princípios de alto desacoplamento e responsabilidade única, isolando toda a lógica de negócio pesada do servidor principal (`server.py`).

---

##  Objetivos

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