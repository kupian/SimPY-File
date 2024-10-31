import socket
import sys
from protocol_utils import RECV_BUFFER, send_file, request_file, REQ_TYPES, get_listing

cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

HOST,PORT,REQ_TYPE = sys.argv[1:4]
FILENAME = ""

if len(sys.argv) == 5:
    FILENAME = sys.argv[4]

cli_sock.connect((HOST, int(PORT)))
print(f"Connected to {HOST}:{PORT}")

if REQ_TYPE == REQ_TYPES.PUT.value:
    send_file(cli_sock, FILENAME)

elif REQ_TYPE == REQ_TYPES.GET.value:
    request_file(cli_sock, FILENAME)

elif REQ_TYPE == REQ_TYPES.LIST.value:
    files = get_listing(cli_sock)
    for file in files:
        print(file)