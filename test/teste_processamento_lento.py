"""
=============================================================================
SETOR: PROCESSAMENTO LENTO E MULTIPROCESSING (Alisson, Ana Paula e Samayra)
Testes de integracao demonstrando que o setor funciona de ponta a ponta e
esta corretamente CONECTADO aos demais setores do projeto.
=============================================================================

Sobe o servidor de verdade (subprocess) e prova, com sockets reais:

  1) o comando basico (CALCULO:SIMULAR_ENTREGA) funciona para qualquer
     usuario;
  2) o comando avancado (CALCULO:AUDITORIA_VENDAS) e NEGADO para um usuario
     comum, e a negacao sai no protocolo padronizado do setor de Tolerancia
     a Falhas (ERRO|ERRO_PERMISSAO|...) -- prova de que PermissaoNegadaError
     esta de fato propagando ate `tf.processar_requisicao_segura`, em vez de
     ser engolida dentro do server.py;
  3) o mesmo comando avancado e ACEITO quando a mensagem chega com o prefixo
     "admin " (forma que o client.py realmente usa no menu de processamento
     lento), e o resultado mostra que rodou via multiprocessing;
  4) enquanto o calculo pesado do administrador esta em andamento (em outro
     processo do SO), o servidor continua respondendo IMEDIATAMENTE a outros
     clientes leves -- prova de que threads (Setor Threads) e multiprocessing
     (este setor) estao de fato trabalhando juntos, sem travar ninguem.

Como rodar (na raiz do projeto):
    python3 -m unittest test/teste_processamento_lento.py -v
ou simplesmente:
    python3 test/teste_processamento_lento.py

Exige Python 3.10+ (o server.py usa match/case) e a porta 40000 livre.
=============================================================================
"""

import os
import sys
import time
import socket
import subprocess
import threading
import unittest

# Garante que a raiz do projeto esteja no path para importar os modulos.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from tolerancia_falhas import tolerancia_falhas as tf
from processamento_lento.processamento_lento import (
    despachar_processamento,
    PermissaoNegadaError,
)

try:
    import server  # noqa: E402  (so para checar se o Python suporta server.py)

    SERVER_DISPONIVEL = True
except SyntaxError:
    SERVER_DISPONIVEL = False


HOST = "127.0.0.1"
PORTA = 40000


# ---------------------------------------------------------------------------
# Auxiliares de rede.
# ---------------------------------------------------------------------------
def _porta_ocupada(host, porta):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect((host, porta))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _esperar_servidor(host, porta, timeout=8.0):
    limite = time.time() + timeout
    while time.time() < limite:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            s.connect((host, porta))
            return True
        except OSError:
            time.sleep(0.15)
        finally:
            try:
                s.close()
            except OSError:
                pass
    return False


def _enviar_e_receber(mensagem, host=HOST, porta=PORTA, timeout=15.0):
    """Conecta, envia uma mensagem, le UMA resposta e fecha. Devolve string."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, porta))
        s.sendall(mensagem.encode("utf-8"))
        dados = s.recv(8192)
        return dados.decode("utf-8", errors="replace")
    finally:
        try:
            s.close()
        except OSError:
            pass


# ===========================================================================
# 1) TESTES DE UNIDADE DO MODULO (sem rede)
# ===========================================================================
class TesteModuloProcessamentoLento(unittest.TestCase):

    def test_basico_funciona_para_qualquer_perfil(self):
        resposta = despachar_processamento("usuario", "SIMULAR_ENTREGA", 1)
        self.assertIn("Básico", resposta)
        self.assertIn("Tempo de Computação no Servidor", resposta)

    def test_avancado_nega_usuario_comum(self):
        with self.assertRaises(PermissaoNegadaError):
            despachar_processamento("usuario", "AUDITORIA_VENDAS", 500)

    def test_avancado_funciona_para_administrador(self):
        resposta = despachar_processamento("administrador", "AUDITORIA_VENDAS", 500)
        self.assertIn("Avançado", resposta)
        self.assertIn("Multiprocessing", resposta)

    def test_operacao_desconhecida(self):
        resposta = despachar_processamento("usuario", "OPERACAO_QUE_NAO_EXISTE")
        self.assertIn("ERRO", resposta)


# ===========================================================================
# 2) TESTES DE INTEGRACAO: servidor real + protocolo + concorrencia
# ===========================================================================
@unittest.skipUnless(SERVER_DISPONIVEL, "server.py exige Python 3.10+ (match/case)")
class TesteIntegracaoProcessamentoLento(unittest.TestCase):
    proc = None

    @classmethod
    def setUpClass(cls):
        if _porta_ocupada(HOST, PORTA):
            raise unittest.SkipTest(
                f"porta {PORTA} ja esta ocupada (servidor rodando?); pulei o teste de integracao"
            )
        env = dict(os.environ)
        env["TF_TIMEOUT_INATIVIDADE"] = "0"  # sem timeout idle durante o teste
        cls.proc = subprocess.Popen(
            [sys.executable, "server.py"],
            cwd=RAIZ,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not _esperar_servidor(HOST, PORTA, timeout=8.0):
            cls.proc.terminate()
            raise unittest.SkipTest("servidor nao subiu a tempo")

    @classmethod
    def tearDownClass(cls):
        if cls.proc is not None:
            cls.proc.terminate()
            try:
                cls.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.proc.kill()

    def test_basico_via_socket(self):
        resposta = _enviar_e_receber("CALCULO:SIMULAR_ENTREGA|2")
        self.assertIn("Básico", resposta)
        self.assertFalse(tf.e_resposta_de_erro(resposta))

    def test_avancado_negado_segue_protocolo_padrao_de_erro(self):
        """
        Prova da CONEXAO entre os setores Processamento Lento e Tolerancia a
        Falhas: a negacao de permissao precisa sair como
        'ERRO|ERRO_PERMISSAO|...' (e nao como uma string solta tipo
        'ERRO_AUTORIZACAO: ...'), porque e assim que o client.py reconhece e
        formata erros via tf.e_resposta_de_erro / descrever_erro_para_usuario.
        """
        resposta = _enviar_e_receber("CALCULO:AUDITORIA_VENDAS|1000")
        self.assertTrue(
            tf.e_resposta_de_erro(resposta),
            msg=f"esperava 'ERRO|ERRO_PERMISSAO|...', veio: {resposta!r}",
        )
        self.assertIn(tf.ERRO_PERMISSAO, resposta)

    def test_avancado_aceito_com_prefixo_admin_roda_multiprocessing(self):
        """
        Prova de que o protocolo usado de verdade pelo client.py (mensagem
        prefixada com 'admin ', ver menu_processamento_lento) e reconhecido
        pelo server.py e realmente despachado para este setor -- e nao cai
        no fallback generico 'DEMO_TCP_OK'.
        """
        resposta = _enviar_e_receber("admin CALCULO:AUDITORIA_VENDAS|1000")
        self.assertNotIn("DEMO_TCP_OK", resposta)
        self.assertIn("Avançado", resposta)
        self.assertIn("Multiprocessing", resposta)

    def test_calculo_pesado_nao_bloqueia_outros_clientes(self):
        """
        Demonstra a integracao Threads + Multiprocessing: dispara uma
        auditoria pesada (processo separado) e, enquanto ela ainda esta
        rodando, um segundo cliente leve consegue ser atendido quase
        imediatamente -- a thread do cliente pesado fica bloqueada esperando
        o ProcessPoolExecutor, mas isso nao trava as demais threads.
        """
        resultado_pesado = {}
        resultado_leve = {}

        def cliente_pesado():
            inicio = time.time()
            resultado_pesado["resposta"] = _enviar_e_receber(
                "admin CALCULO:AUDITORIA_VENDAS|30000000", timeout=30.0
            )
            resultado_pesado["duracao"] = time.time() - inicio

        t_pesado = threading.Thread(target=cliente_pesado)
        t_pesado.start()

        # Da um tempo para o calculo pesado realmente comecar antes de medir
        # o cliente leve, para nao testar uma corrida de largada.
        time.sleep(0.3)

        inicio_leve = time.time()
        resultado_leve["resposta"] = _enviar_e_receber("LISTADEITENS", timeout=5.0)
        resultado_leve["duracao"] = time.time() - inicio_leve

        t_pesado.join(timeout=30.0)

        self.assertIn("ITENS:", resultado_leve["resposta"])
        # O cliente leve deve ser atendido bem mais rapido que o pesado --
        # se o calculo pesado bloqueasse o servidor inteiro, essa diferenca
        # nao existiria.
        self.assertLess(resultado_leve["duracao"], 2.0)
        self.assertIn("Multiprocessing", resultado_pesado.get("resposta", ""))
        self.assertGreater(
            resultado_pesado.get("duracao", 0), resultado_leve["duracao"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
