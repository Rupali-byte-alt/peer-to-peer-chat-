"""
Peer-to-Peer Chat Application (GUI version)
-------------------------------------------
Usage:
    python gui_chat.py listen  <your_name>
    python gui_chat.py connect <your_name> <peer_ip>

Start the 'listen' side first. Use 127.0.0.1 as <peer_ip> to test on one laptop.
"""

import socket
import threading
import queue
import sys
import datetime
import tkinter as tk
from tkinter import scrolledtext

PORT = 5002


class ChatApp:
    def __init__(self, root, mode, name, host):
        self.root = root
        self.name = name
        self.conn = None
        self.q = queue.Queue()  # thread-safe channel: network thread -> GUI

        root.title(f"P2P Chat - {name} ({mode})")

        # Message display area
        self.box = scrolledtext.ScrolledText(
            root, state="disabled", width=55, height=18, wrap="word"
        )
        self.box.pack(padx=10, pady=10)

        # Entry box + Send button
        frame = tk.Frame(root)
        frame.pack(padx=10, pady=(0, 10), fill="x")
        self.entry = tk.Entry(frame)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.send)
        tk.Button(frame, text="Send", command=self.send).pack(side="left", padx=(5, 0))

        if mode == "listen":
            self.show("System", f"Waiting for a peer on port {PORT}...")
        else:
            self.show("System", f"Connecting to {host}:{PORT}...")

        # Networking runs in a background thread so the window never freezes
        threading.Thread(target=self.network, args=(mode, host), daemon=True).start()
        self.poll()

    def show(self, sender, text):
        stamp = datetime.datetime.now().strftime("%H:%M")
        self.box.config(state="normal")
        self.box.insert("end", f"[{stamp}] {sender}: {text}\n")
        self.box.config(state="disabled")
        self.box.see("end")

    def poll(self):
        """Check the queue every 100 ms and display any new messages."""
        while not self.q.empty():
            sender, text = self.q.get()
            self.show(sender, text)
        self.root.after(100, self.poll)

    def network(self, mode, host):
        try:
            if mode == "listen":
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", PORT))
                s.listen(1)
                self.conn, addr = s.accept()
            else:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((host, PORT))

            # Exchange names first (one message per line)
            self.conn.sendall((self.name + "\n").encode())
            reader = self.conn.makefile("r", encoding="utf-8")
            peer = reader.readline().strip() or "Peer"
            self.q.put(("System", f"Connected to {peer}. Start chatting!"))

            for line in reader:
                self.q.put((peer, line.strip()))
            self.q.put(("System", f"{peer} disconnected."))
        except OSError as e:
            self.q.put(("System", f"Connection error: {e}"))

    def send(self, event=None):
        text = self.entry.get().strip()
        if not text or self.conn is None:
            return
        try:
            self.conn.sendall((text + "\n").encode())
            self.show("You", text)
            self.entry.delete(0, "end")
        except OSError:
            self.show("System", "Message not sent, no connection.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python gui_chat.py listen <your_name>")
        print("  python gui_chat.py connect <your_name> <peer_ip>")
        sys.exit()

    mode, name = sys.argv[1], sys.argv[2]
    host = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"

    root = tk.Tk()
    ChatApp(root, mode, name, host)
    root.mainloop()