import socket
import json
import os
from enum import Enum

RECV_BUFFER = 1024

class REQ_TYPES(Enum):
    PUT = "put"
    GET = "get"
    LIST = "list"
    INFO = "info"

class STATUS_CODES(Enum):
    ALLOW = "000"
    DENY = "100"

def request_file(socket: socket.socket, filename: str):
    # Initiate GET request with server
    request = json.dumps({
                "type": REQ_TYPES.GET.value,
                "filename": filename
            })

    socket.sendall(request.encode())
    
    # We expect back a PUT packet with the file info
    message = get_response(socket)
    print(message)

    if message.get("type") == REQ_TYPES.PUT.value:
        content_length = message.get("content_length")

        # We send back approval of the file info
        allow(socket, "File info received. Continue to send file.")

        # First we expect an acknowledgement that the file will be sent
        message = get_response(socket)

        print(f"{message.get("status_code")}: {message.get("message")}")
        if message.get("status_code") == STATUS_CODES.ALLOW.value:
            # Now we are expecting the file data
            receive_file(socket, filename, content_length)
    
    socket.close()

def get_file_size(filename) -> int:
    try:
        with open(filename, "rb") as f:
            content_length = os.fstat(f.fileno()).st_size
        return content_length
    except FileNotFoundError:
        return 0

def send_file(socket: socket.socket, filename: str):
    content_length = get_file_size(filename)
    try:
        with open(filename, "rb") as f:

            request = json.dumps({
                "type": REQ_TYPES.PUT.value,
                "filename": filename,
                "content_length": content_length
            })
            socket.sendall(request.encode("utf-8"))

            message = get_response(socket)
            status_code = message.get("status_code")

            print(f"{status_code}: {message.get("message")}")

            if status_code == STATUS_CODES.ALLOW.value:
                # First we acknowledge that we are going to send the file
                allow(socket, "File approval acknowledged. Sending file...")
                print(f"Sending {filename}...")
                # Then we send the file
                file_content = f.read()
                socket.sendall(file_content)

                message = get_response(socket)
                status_code = message.get("status_code")

    except FileNotFoundError:
        print("File not found")
    finally:
        socket.close()
        print("--Closed connection--")

def receive_file(socket: socket.socket, filename: str, content_length):
    received = 0
    with open(filename, "wb") as f:

        print(f"Downloading {filename}...")

        while received < content_length:
            data = socket.recv(RECV_BUFFER)
            received += len(data)
            f.write(data)
            if not data:
                print("--Connection closed unexpectedly--")

    print("File transfer complete")

    # We tell the connection we have successfully received the file
    allow(socket, "File transfer complete")

    socket.close()
    print("--Closed connection--")

def get_listing(socket: socket.socket):
    request = json.dumps({
        "type": REQ_TYPES.LIST.value
    })
    socket.sendall(request.encode())
    
    response = get_response(socket)
    socket.close()
    if response.get("status_code") == STATUS_CODES.ALLOW.value:
        return response.get("files")
    else:
        return []

def send_listing(socket: socket.socket):
    files = os.listdir(".")
    response = json.dumps({
        "status_code": STATUS_CODES.ALLOW.value,
        "message": "File listing message",
        "files": files
    })
    socket.sendall(response.encode())
    socket.close()

def get_response(socket: socket.socket) -> dict:
    #TODO: add error handling
    response = socket.recv(RECV_BUFFER)
    message = json.loads(response)
    return message

def allow(socket: socket.socket, message: str):
    #TODO: add error handling
    approval = json.dumps({
            "status_code": STATUS_CODES.ALLOW.value,
            "message": message
        })
    socket.sendall(approval.encode())

def deny(socket: socket.socket, message: str):
    #TODO: add error handling
    rejection = json.dumps({
            "status_code": STATUS_CODES.DENY.value,
            "message": message
        })
    socket.sendall(rejection.encode())