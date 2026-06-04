import socket

def resolve_host(host: str):

    try:

       return socket.gethostbyname(host)

    except Exception:

     return None