import time
import math
import random
from concurrent.futures import ProcessPoolExecutor

# =========================================================================
#6. PROCESSAMENTO LENTO E MULTIPROCESSING
# Responsabilidade: Executar cálculos matemáticos lentos simulando o 
# contexto de delivery de comida, utilizando processos separados (multiprocessing)
# para tarefas pesadas, evitando o bloqueio do servidor.
# =========================================================================

class PermissaoNegadaError(Exception):
    pass


def _calcular_simulacao_vendas_pesada(num_registros: int) -> dict:
    """
    Função pura que executa o processamento pesado de CPU.
    IMPORTANTE: Deve ser uma função de nível de módulo (global) para que possa
    ser serializada (pickled) corretamente pelo ProcessPoolExecutor.
    
    Simula uma auditoria massiva de vendas e projeção de faturamento da lanchonete.
    """
    faturamento_total = 0.0
    cupons_analisados = 0
    
    # Simulação intensiva de CPU gerando dados matemáticos pesados
    for i in range(num_registros):
        # Operações matemáticas flutuantes intencionais para ocupar a CPU
        faturamento_total += math.sin(i) * math.cos(i) + (i % 100)
        if i % 2 == 0:
            cupons_analisados += 1
            
    # Ajustando o valor simulado para algo legível no contexto de delivery
    faturamento_final = abs(faturamento_total) * 0.05
    ticket_medio = faturamento_final / max(cupons_analisados, 1)
    
    return {
        "status": "Sucesso",
        "mensagem": "Relatório analítico de auditoria macro concluído.",
        "cupons_auditados": cupons_analisados,
        "faturamento_projetado_total": round(faturamento_final, 2),
        "ticket_medio_simulado": round(ticket_medio, 2)
    }


def processamento_basico_motoboy(num_pedidos: int) -> dict:
    """
    [PERMISSÃO: USUÁRIO / BÁSICO]
    Simula uma estimativa estatística de tempo de espera e roteirização leve.
    Como é leve/médio, roda em thread comum (sequencial nesta chamada).
    """
    # Loops intencionais para gerar o processamento lento
    tempo_acumulado = 0.0
    for pedido in range(1, num_pedidos + 1):
        # Simula cálculo de rota em grafo fictício por iteração
        for passo in range(2_000_000):  
            tempo_acumulado += (passo % 3) * 0.000001
            
    tempo_estimado_entrega = round(20 + (tempo_acumulado % 40), 1)
    return {
        "status": "Sucesso",
        "tipo": "Básico (Simulação de Entrega/Motoboy)",
        "pedidos_analisados": num_pedidos,
        "tempo_estimado_espera_minutos": tempo_estimado_entrega
    }


def processamento_avancado_auditoria(num_registros: int) -> dict:
    """
    [PERMISSÃO: ADMINISTRADOR / AVANÇADO]
    Dispara o cálculo pesado utilizando multiprocessamento para não travar o servidor.
    """
    # Usamos o ProcessPoolExecutor para garantir que o cálculo rode em outro processo do SO
    with ProcessPoolExecutor(max_workers=1) as executor:
        futuro = executor.submit(_calcular_simulacao_vendas_pesada, num_registros)
        resultado = futuro.result()  # Bloqueia apenas a thread atual do cliente
        
    resultado["tipo"] = "Avançado (Multiprocessing - Auditoria de Vendas)"
    return resultado


def despachar_processamento(perfil_usuario: str, tipo_operacao: str, *args) -> str:
    perfil = perfil_usuario.lower().strip()
    operacao = tipo_operacao.upper().strip()
    
    cronometro_inicio = time.time()
    
    if operacao == "SIMULAR_ENTREGA":
        # Operação que qualquer usuário pode executar, mas é lenta
        num_pedidos = args[0] if args else 5
        resultado_dados = processamento_basico_motoboy(int(num_pedidos))
        
    elif operacao == "AUDITORIA_VENDAS":
        # Operação que apenas administradores podem executar, e é muito pesada
        if perfil != "administrador":
            raise PermissaoNegadaError(
                f"Erro: O perfil '{perfil_usuario}' não possui a permissão necessária para executar Auditoria."
            )
            
        num_registros = args[0] if args else 15_000_000  # Valor padrão alto para estressar CPU
        resultado_dados = processamento_avancado_auditoria(int(num_registros))
        
    else:
        return f"ERRO: Operação de processamento '{tipo_operacao}' desconhecida.\n"

    tempo_decorrido = time.time() - cronometro_inicio
    
    resposta_formatada = (
        f"--- RESULTADO PROCESSAMENTO LENTO ---\n"
        f"Tipo: {resultado_dados.get('tipo', 'Não definido')}\n"
        f"Detalhes: {resultado_dados}\n"
        f"Tempo de Computação no Servidor: {tempo_decorrido:.4f} segundos\n"
        f"--------------------------------------\n"
    )
    
    return resposta_formatada