import socket
import time
import threading

HOST = "127.0.0.1"
PORT = 40000


def cliente_simulado(nome, delay_entre_mensagens, mensagens):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    print(f"[{nome}] conectado em t={time.time():.2f}")

    for msg in mensagens:
        time.sleep(delay_entre_mensagens)
        s.sendall(msg.encode("utf-8"))
        resposta = s.recv(4096).decode("utf-8", errors="replace").strip()
        print(f"[{nome}] t={time.time():.2f} enviou={msg!r} recebeu={resposta!r}")

    s.sendall(b"CLOSECONNECTION")
    s.recv(4096)
    s.close()
    print(f"[{nome}] desconectado em t={time.time():.2f}")


t0 = time.time()

# Cliente A: bem lento entre mensagens (simula usuario digitando devagar)
threads = [
    threading.Thread(target=cliente_simulado, args=("CLIENTE_LENTO", 2.0, ["LISTADEITENS", "oi"])),
    threading.Thread(target=cliente_simulado, args=("CLIENTE_RAPIDO_1", 0.1, ["teste1", "teste2", "teste3"])),
    threading.Thread(target=cliente_simulado, args=("CLIENTE_RAPIDO_2", 0.1, ["abc", "def"])),
]

for t in threads:
    t.start()

for t in threads:
    t.join()

print(f"\nTempo total do teste: {time.time() - t0:.2f}s")
print("Se CLIENTE_RAPIDO_1 e CLIENTE_RAPIDO_2 terminaram MUITO antes do")
print("CLIENTE_LENTO, isso comprova que o servidor nao bloqueou clientes")
print("rapidos esperando o cliente lento.")
