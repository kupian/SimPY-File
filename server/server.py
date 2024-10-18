import socket
import os
import sys
from protocol_utils import RECV_BUFFER, send_file, receive_file, REQ_TYPES, get_file_size, allow, deny, get_response, send_listing

HOST = "0.0.0.0"
PORT = sys.argv[1]

def main():

    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.bind(("", int(sys.argv[1])))

    print(f"{HOST}:{PORT}")
    print("Server up and running")

    srv_sock.listen(5)

    while True:
        cli_sock, cli_addr = srv_sock.accept()
        print(f"Connection from client: {cli_addr}")

        request = get_response(cli_sock)
        req_type = request.get("type")

        if req_type == REQ_TYPES.GET.value:
            filename = request.get("filename")
            file_size = get_file_size(filename)
            if file_size == 0:
                deny(cli_sock, "Remote file does not exist")
            else:
                send_file(cli_sock, filename)

        elif req_type == REQ_TYPES.PUT.value:
            filename = request.get("filename")
            content_length = request.get("content_length")
            try:
                with open(filename, "xb") as f:
                    accept_file(cli_sock, filename, content_length)
                    
            except FileExistsError:
                deny(cli_sock, "Cannot overwrite remote file")

        elif req_type == REQ_TYPES.LIST.value:
            send_listing(cli_sock)

        cli_sock.close()

def accept_file(socket: socket.socket, filename: str, content_length: int):
    allow(socket, "File upload approved")
    # Delete the file we just created to check its existence
    # TODO: probaly a better way to do this
    os.remove(filename)
    # Now we expect acknowledgement
    acknowledgement = get_response(socket)
    print(acknowledgement.get("message"))
    if acknowledgement.get("status_code") == "000":    
        receive_file(socket, filename, content_length)

if __name__ == "__main__":
    main()