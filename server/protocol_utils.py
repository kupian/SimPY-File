import socket
import json
import os
from progress.bar import ChargingBar
from enum import Enum

RECV_BUFFER = 1024

class REQ_TYPES(Enum):
    PUT = "put"
    GET = "get"
    LIST = "list"

class STATUS_CODES(Enum):
    ALLOW = "000"
    DENY = "100"

def request_file(sock: socket.socket, filename: str):
    '''
    Requests and downloads a file from the server
    '''
    # Initiate GET request with server
    try:
        print(f"Requesting {filename}")
        request = json.dumps({
                    "type": REQ_TYPES.GET.value,
                    "filename": filename
                })

        sock.sendall(request.encode())
    except socket.error:
        print("Error sending file request")
        sock.close()
        print("--Closed connection--")
        return
    
    # We expect back a PUT packet with the file info
    message = get_response(sock)
    if message.get("type") == REQ_TYPES.PUT.value:
        content_length = message.get("content_length", None)
        if content_length is None:
            print("Unknown file size")
            sock.close()
            print("--Closed connection--")
            return

        # We send back approval of the file info
        allow(sock, "File info received. Continue to send file.")

        # First we expect an acknowledgement that the file will be sent
        message = get_response(sock)
        if message.get("status_code") == STATUS_CODES.ALLOW.value:
            # Now we are expecting the file data
            receive_file(sock, filename, content_length)
            return
        else:
            print(f"Server rejected file transfer: {message.get("message")}")
    else:
        print(f"Server error: {message.get("message")}")

    sock.close()
    print("--Closed connection--")

def get_file_size(filename) -> int:
    '''
    Get the size in bytes of a local file
    '''
    try:
        with open(filename, "rb") as f:
            content_length = os.fstat(f.fileno()).st_size
        return content_length
    except FileNotFoundError:
        print("Error: file not found")
        return -1

def send_file(sock: socket.socket, filename: str):
    content_length = get_file_size(filename)
    if content_length < 1:
        reject(sock, "File does not exist")
        return

    try:
        print(f"Requesting to send {filename}")
        with open(filename, "rb") as f:
            request = json.dumps({
                "type": REQ_TYPES.PUT.value,
                "filename": filename,
                "content_length": content_length
            })
            sock.sendall(request.encode("utf-8"))

            message = get_response(sock)
            status_code = message.get("status_code")

            if status_code == STATUS_CODES.ALLOW.value:
                # First we acknowledge that we are going to send the file
                allow(sock, "File approval acknowledged. Sending file...")
                print(f"Sending {filename}...")
                # Then we send the file
                file_content = f.read()
                sock.sendall(file_content)

                message = get_response(sock)
                status_code = message.get("status_code")

                if status_code == STATUS_CODES.ALLOW.value:
                    print("File sent successfully")
                else:
                    print(f"Error sending file: {message.get("message")}")
            else:
                print(f"Remote error: {message.get("message")}")
    except FileNotFoundError:
        print("File not found")
    except socket.error:
        print("Error sending packet")
    finally:
        sock.close()
        print("--Closed connection--")

def receive_file(socket: socket.socket, filename: str, content_length):
    bytes_received = 0
    # Using 'wb' as opposed to 'xb' as this function is shared by server
    # and client, and the client should be allowed to overwrite existing files.
    
    # Overwrite checking for the server is moved to the initial request
    # handling in server.py
    with open(filename, "wb") as f:

        with ChargingBar("Downloading", max=content_length/RECV_BUFFER) as bar:

            while bytes_received < content_length:
                data = socket.recv(RECV_BUFFER)
                try:
                    if not data:
                        print("--Connection closed unexpectedly--")
                        raise IOError

                    bytes_received += len(data)
                    f.write(data)
                except IOError:
                    print("Error writing data to file")
                    os.remove(filename)
                bar.next()
            bar.finish()

    print("File transfer complete")

    # We tell the connection we have successfully received the file
    allow(socket, "File transfer complete")

    socket.close()
    print("--Closed connection--")

def get_listing(sock: socket.socket) -> list[str]:
    '''
    Requests a directory listing
    '''
    try:
        print("Requesting directory listing")
        request = json.dumps({
            "type": REQ_TYPES.LIST.value
        })
        sock.sendall(request.encode())
    except socket.error:
        print("Error requesting directory listing")
        return []
    
    response = get_response(sock)
    sock.close()

    if response.get("status_code") == STATUS_CODES.ALLOW.value:
        print("Directory listing from server:")
        return response.get("files")
    else:
        return []

def send_listing(sock: socket.socket):
    '''
    Sends a directory listing
    '''
    files = os.listdir(".")
    try:
        print("Sending directory listing")
        response = json.dumps({
            "status_code": STATUS_CODES.ALLOW.value,
            "message": "File listing message",
            "files": files
        })
        sock.sendall(response.encode())
    except socket.error:
        print("Error sending directory listing")
    else:
        print("Successfully sent directory listing")
    finally:
        sock.close()
        print("--Closed connection--")

def get_response(sock: socket.socket) -> dict:
    '''
    Receive a socket message and load the JSON
    '''
    response = sock.recv(RECV_BUFFER)
    try:
        message = json.loads(response)
        return message
    except json.JSONDecodeError:
        print("Error decoding response")
        return {}

def allow(sock: socket.socket, message="Approved"):
    '''
    Sends an approval packet with a given message
    '''
    try:
        approval = json.dumps({
                "status_code": STATUS_CODES.ALLOW.value,
                "message": message
            })
        sock.sendall(approval.encode())
    except socket.error:
        print("Error sending approval packet")
        sock.close()
        print("--Closed connection--")

def reject(sock: socket.socket, message="Rejected"):
    '''
    Sends a rejection packet and closes the socket
    '''
    try:
        rejection = json.dumps({
                "status_code": STATUS_CODES.DENY.value,
                "message": message
            })
        sock.sendall(rejection.encode())
    except socket.error:
        print("Error sending rejection packet")
    finally:
        sock.close()
        print("--Closed connection--")