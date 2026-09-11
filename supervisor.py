"""Visible status window and restart controller for the WorkBuddy gateway.

Commands (type and press Enter):
  r  restart the gateway
  s  stop the gateway
  c  clear the screen
  q  quit the window (stops the gateway first)
  ?  show help
"""

import atexit
import os
import queue
import socket
import subprocess
import sys
import threading
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8080"))
LOG_PATH = os.path.join(ROOT, "gateway.log")

cmd_queue = queue.Queue()
state = {"proc": None, "manual_stop": False}
lock = threading.Lock()


def port_open(host=HOST, port=PORT, timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def status_line():
    with lock:
        proc = state["proc"]
        alive = proc is not None and proc.poll() is None
    if alive:
        return f"[STATUS] RUNNING pid={proc.pid} port={PORT} open={port_open()}"
    return f"[STATUS] STOPPED port={PORT} open={port_open()} (press r to start)"


def spawn(force=False):
    busy = port_open()
    if busy and not force:
        print(
            f"[supervisor] port {PORT} already in use - another gateway is running; "
            "not starting a duplicate. Type r to force-restart this window's child."
        )
        return
    if busy and force:
        print(
            f"[supervisor] port {PORT} still in use after stop - not spawning a "
            "child that cannot bind. Stop the other gateway first."
        )
        return
    env = dict(os.environ)
    env.update(
        {
            "HOST": HOST,
            "PORT": str(PORT),
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    with lock:
        if state["proc"] is not None and state["proc"].poll() is None:
            state["proc"].terminate()
        state["proc"] = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        proc = state["proc"]
        state["manual_stop"] = False
    print(f"[supervisor] gateway started pid={proc.pid}")
    threading.Thread(target=tail, args=(proc,), daemon=True).start()


def open_log():
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 5 * 1024 * 1024:
        try:
            os.replace(LOG_PATH, LOG_PATH + ".1")
        except OSError:
            pass
    return open(LOG_PATH, "a", encoding="utf-8", errors="replace")


def tail(proc):
    log = open_log()
    try:
        for line in proc.stdout:
            print(f"[gw] {line}", end="")
            log.write(line)
            log.flush()
    finally:
        log.close()


def stop():
    with lock:
        proc = state.get("proc")
        state["manual_stop"] = True
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            print(f"[supervisor] gateway stopped pid={proc.pid}")
        state["proc"] = None


def restart():
    stop()
    for _ in range(50):
        if not port_open():
            break
        time.sleep(0.1)
    spawn(force=True)


def stdin_reader():
    while True:
        line = sys.stdin.readline()
        if not line:
            return
        cmd_queue.put(line.strip().lower())


def cleanup():
    with lock:
        proc = state.get("proc")
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass


atexit.register(cleanup)


def main():
    print("=" * 60)
    print("  WorkBuddy Gateway - status window")
    print(f"  endpoint   http://{HOST}:{PORT}")
    print("  commands   r=restart  s=stop  c=clear  q=quit  ?=help")
    print("=" * 60)

    threading.Thread(target=stdin_reader, daemon=True).start()
    spawn()

    last_status = 0.0
    try:
        while True:
            now = time.time()
            try:
                cmd = cmd_queue.get_nowait()
            except queue.Empty:
                cmd = None
            if cmd:
                if cmd == "r":
                    print("[supervisor] restarting...")
                    restart()
                elif cmd == "s":
                    stop()
                elif cmd == "c":
                    os.system("cls" if os.name == "nt" else "clear")
                elif cmd == "q":
                    stop()
                    print("[supervisor] quit")
                    return
                elif cmd in ("?", "h", "help"):
                    print("  r=restart  s=stop  c=clear  q=quit")
                else:
                    print(f"[supervisor] unknown command: {cmd}")
            with lock:
                proc = state.get("proc")
                if proc is not None and not state["manual_stop"]:
                    code = proc.poll()
                    if code is not None:
                        print(
                            f"[STATUS] gateway exited code={code} - press r to restart"
                        )
                        state["proc"] = None
            if now - last_status > 30:
                print(status_line())
                last_status = now
            time.sleep(0.2)
    except KeyboardInterrupt:
        stop()
        print("[supervisor] Ctrl+C - bye")


if __name__ == "__main__":
    main()