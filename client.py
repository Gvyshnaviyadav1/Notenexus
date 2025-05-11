import socket
import threading

def listen_for_messages(sock):
    while True:
        try:
            msg = sock.recv(1024).decode("utf-8", "replace")
            print(msg, end="", flush=True)
        except:
            print("\nDisconnected from server.")
            break

def start_client(host='localhost', port=1207):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except ConnectionRefusedError:
        print("Could not connect to server.")
        return
    #threading.Thread(target=listen_for_messages, args=(sock,), daemon=True).start()
    listener = threading.Thread(target=listen_for_messages, args=(sock,))
    listener.start()
    while True:
        try:
            msg = input()
            sock.sendall(msg.encode())
            if msg.strip().isdigit() and int(msg.strip()) == 13:
                print("Logging out.")
                break
        except:
            print("Error sending message.")
            break
    sock.close()

if __name__ == "__main__":
    start_client()
