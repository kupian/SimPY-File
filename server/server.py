import socket
import os
import sys
from protocol_utils import send_file, receive_file, REQ_TYPES, allow, reject, get_response, send_listing

HOST = "0.0.0.0"
PORT = sys.argv[1]
FILENAME_MAX_LENGTH = 32

def main():

    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.bind(("", int(sys.argv[1])))

    print(f"{HOST}:{PORT}")
    print("Server up and running")

    srv_sock.listen(5)

    while True:
        cli_sock, cli_addr = srv_sock.accept()
        print(f"Connection from {cli_addr}")

        request = get_response(cli_sock)
        req_type = request.get("type")

        if req_type == REQ_TYPES.GET.value:
            filename = request.get("filename")
            print(f"{cli_addr} wants to download {filename}")
            send_file(cli_sock, filename)

        elif req_type == REQ_TYPES.PUT.value:
            filename = request.get("filename")
            content_length = request.get("content_length")
            if len(filename) > FILENAME_MAX_LENGTH or content_length <= 0:
                reject(cli_sock, "Filename exceeds max length")
            print(f"{cli_addr} wants to upload {filename}")
            try:
                with open(filename, "xb") as f:
                    accept_file(cli_sock, filename, content_length)     
            except FileExistsError:
                print("Error: file already exists, cannot overwrite")
                reject(cli_sock, "Cannot overwrite remote file")

        elif req_type == REQ_TYPES.LIST.value:
            print(f"{cli_addr} wants directory listing")
            send_listing(cli_sock)

        cli_sock.close()


def accept_file(sock: socket.socket, filename: str, content_length: int):
    """Accept a file upload request

    Args:
        sock (socket.socket): Socket to accept file from
        filename (str): Name of the file to accept
        content_length (int): Size in bytes of the file
    """
    
    print("File upload approved")
    allow(sock, "File upload approved")
    
    # Delete the file we just created to check its existence
    os.remove(filename)
    
    # Now we expect acknowledgement
    acknowledgement = get_response(sock)
    if acknowledgement.get("status_code") == "000":    
        receive_file(sock, filename, content_length)

if __name__ == "__main__":
    main()