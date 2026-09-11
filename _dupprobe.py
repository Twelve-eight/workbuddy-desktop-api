"""Count duplicate request bodies through relay to 8317."""
import socket, threading, json, hashlib, time

GATEWAY = ("127.0.0.1", 8317)
LOG = r"G:\omp works\workbuddy-desktop-api\_dup.log"
lock = threading.Lock()
counts = {}

def handle(client):
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(4096)
            if not chunk:
                return
            data += chunk
        head, _, rest = data.partition(b"\r\n\r\n")
        lines = head.decode("latin1").split("\r\n")
        headers = {}
        for ln in lines[1:]:
            if ":" in ln:
                k, v = ln.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        clen = int(headers.get("content-length", 0))
        while len(rest) < clen:
            chunk = client.recv(4096)
            if not chunk:
                break
            rest += chunk
        body = rest[:clen]
        h = hashlib.md5(body).hexdigest()[:12]
        try:
            obj = json.loads(body)
            msgs = len(obj.get("messages") or [])
            model = obj.get("model", "")
            effort = obj.get("reasoning_effort", "")
            is_stream = obj.get("stream")
        except Exception as e:
            model, msgs, effort, is_stream = "?", -1, "?", "?"
        with lock:
            counts[h] = counts.get(h, 0) + 1
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] #{counts[h]} model={model} msgs={msgs} effort={effort} stream={is_stream} md5={h}", flush=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {json.dumps({'model': model, 'msgs': msgs, 'effort': effort, 'stream': is_stream, 'md5': h, 'count': counts[h]}, ensure_ascii=False)}\n")
        gw = socket.create_connection(GATEWAY, timeout=300)
        gw.sendall(head + b"\r\n\r\n" + body)
        while True:
            chunk = gw.recv(65536)
            if not chunk:
                break
            client.sendall(chunk)
        gw.close()
    except Exception as e:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"ERR {e}\n")
    finally:
        client.close()

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 8320))
srv.listen(8)
while True:
    c, _ = srv.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()