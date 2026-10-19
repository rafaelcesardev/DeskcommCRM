import socket,sys,time
ocioso=float(sys.argv[1])
s=socket.create_connection(("127.0.0.1",3999))
req=b"GET /login HTTP/1.1\r\nHost: x\r\nConnection: keep-alive\r\n\r\n"
def resp():
    data=b""; s.settimeout(10)
    while b"\r\n\r\n" not in data:
        c=s.recv(65536)
        if not c: return None
        data+=c
    head,_,body=data.partition(b"\r\n\r\n")
    h=dict(l.split(b": ",1) for l in head.split(b"\r\n")[1:] if b": " in l)
    if b"Content-Length" in h or b"content-length" in h:
        n=int(h.get(b"Content-Length",h.get(b"content-length")))
        while len(body)<n: body+=s.recv(65536)
    else:
        while not body.endswith(b"0\r\n\r\n"): body+=s.recv(65536)
    return head.split(b"\r\n")[0].decode()
s.sendall(req); a=resp()
time.sleep(ocioso)
try:
    s.sendall(req); b=resp()
except Exception as e: b=f"falhou: {e!r}"
print(f"1ª={a} | após {ocioso:.0f}s ocioso, 2ª no MESMO socket={b}")
