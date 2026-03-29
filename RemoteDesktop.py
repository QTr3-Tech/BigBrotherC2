import tkinter
from tkinter import ttk, filedialog
import socket
import struct
import threading
import io
import os
import time
import tempfile
import datetime

from PIL import Image, ImageTk
UDP_MAX          = 60000
HEADER_FMT       = "!IHHH"
HEADER_SIZE      = struct.calcsize(HEADER_FMT)
CTRL_PORT_OFFSET = 1
"""
remote_desktop_agent.py
Usage:
    rd = RemoteDesktopAgent(server_ip="192.168.1.5", udp_port=55100)
    rd.start()   # begins streaming silently in background
    rd.stop()    # stops streaming
"""

import socket
import struct
import threading
import io
import time

import numpy as np
import dxcam
from PIL import Image

import win32api
import win32con
import win32gui
import win32ui

UDP_MAX          = 60000
HEADER_FMT       = "!IHHH"
HEADER_SIZE      = struct.calcsize(HEADER_FMT)
CTRL_PORT_OFFSET = 1


class RDC:
    def __init__(self, server_ip: str, udp_port: int=57908):
        self.server_ip  = server_ip
        self.udp_port   = udp_port
        self.ctrl_port  = udp_port + CTRL_PORT_OFFSET

        self._running = False
        self._quality = 50
        self._fps     = 15
        self._lock    = threading.Lock()

        # dxcam instance — one per agent, created at init
        self._camera = dxcam.create(output_color="BGR")

    # ── public ────────────────────────────────────────────────────────────────

    def start(self):
        """Start streaming. Returns immediately. Safe to call from any thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._quality = 50
            self._fps     = 15

        threading.Thread(target=self._stream_loop, daemon=True, name="rd-stream").start()
        threading.Thread(target=self._ctrl_listener, daemon=True, name="rd-ctrl").start()

    def stop(self):
        """Stop streaming."""
        with self._lock:
            self._running = False

    # ── cursor ────────────────────────────────────────────────────────────────

    def _get_cursor(self):
        """Returns (rgba_array, hot_x, hot_y, cur_x, cur_y) or None."""
        try:
            flags, hcursor, (cx, cy) = win32gui.GetCursorInfo()
            if flags == 0 or hcursor == 0:
                return None

            _, hot_x, hot_y, _, _ = win32gui.GetIconInfo(hcursor)

            hdc_screen = win32gui.GetDC(0)
            hdc_mem    = win32ui.CreateDCFromHandle(hdc_screen)
            hdc_bmp    = hdc_mem.CreateCompatibleDC()

            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(hdc_mem, 32, 32)
            hdc_bmp.SelectObject(bmp)
            hdc_bmp.FillSolidRect((0, 0, 32, 32), win32api.RGB(255, 0, 255))
            win32gui.DrawIconEx(hdc_bmp.GetHandleOutput(), 0, 0,
                                hcursor, 32, 32, 0, None, win32con.DI_NORMAL)

            info = bmp.GetInfo()
            data = bmp.GetBitmapBits(True)

            win32gui.DeleteObject(bmp.GetHandle())
            hdc_bmp.DeleteDC()
            hdc_mem.DeleteDC()
            win32gui.ReleaseDC(0, hdc_screen)

            arr  = np.frombuffer(data, dtype=np.uint8).reshape(info["bmHeight"], info["bmWidth"], 4)
            rgba = arr[:, :, [2, 1, 0, 3]].copy()
            magenta = (rgba[:, :, 0] == 255) & (rgba[:, :, 1] == 0) & (rgba[:, :, 2] == 255)
            rgba[magenta, 3] = 0

            return rgba, hot_x, hot_y, cx, cy
        except Exception:
            return None

    def _draw_cursor(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Alpha-blends the Windows cursor onto the BGR frame."""
        result = self._get_cursor()
        if result is None:
            return frame_bgr

        cursor_rgba, hot_x, hot_y, cx, cy = result
        fh, fw = frame_bgr.shape[:2]
        ch, cw = cursor_rgba.shape[:2]

        x0 = cx - hot_x;  y0 = cy - hot_y
        x1 = x0 + cw;     y1 = y0 + ch

        fx0 = max(x0, 0);  fy0 = max(y0, 0)
        fx1 = min(x1, fw); fy1 = min(y1, fh)
        if fx0 >= fx1 or fy0 >= fy1:
            return frame_bgr

        cx0 = fx0 - x0;  cy0 = fy0 - y0
        cx1 = cx0 + (fx1 - fx0)
        cy1 = cy0 + (fy1 - fy0)

        crop  = cursor_rgba[cy0:cy1, cx0:cx1]
        alpha = crop[:, :, 3:4].astype(np.float32) / 255.0
        dst   = frame_bgr[fy0:fy1, fx0:fx1].astype(np.float32)
        src   = crop[:, :, [2, 1, 0]].astype(np.float32)

        frame_bgr[fy0:fy1, fx0:fx1] = (src * alpha + dst * (1.0 - alpha)).astype(np.uint8)
        return frame_bgr

    # ── capture ───────────────────────────────────────────────────────────────

    def _capture_jpeg(self, quality: int) -> bytes:
        frame = self._camera.grab()
        if frame is None:
            return b""
        frame = self._draw_cursor(frame)
        img   = Image.fromarray(frame[:, :, ::-1])   # BGR → RGB
        buf   = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=False)
        return buf.getvalue()

    # ── UDP send ──────────────────────────────────────────────────────────────

    def _send_frame(self, sock: socket.socket, dest: tuple, frame_id: int, jpeg: bytes):
        chunks = [jpeg[i: i + UDP_MAX] for i in range(0, len(jpeg), UDP_MAX)]
        for idx, chunk in enumerate(chunks):
            header = struct.pack(HEADER_FMT, frame_id, idx, len(chunks), len(chunk))
            try:
                sock.sendto(header + chunk, dest)
            except Exception:
                pass

    # ── stream loop thread ────────────────────────────────────────────────────

    def _stream_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
        dest     = (self.server_ip, self.udp_port)
        frame_id = 0

        while True:
            with self._lock:
                if not self._running:
                    break
                quality = self._quality
                fps     = self._fps

            t = time.monotonic()
            try:
                jpeg = self._capture_jpeg(quality)
                if jpeg:
                    self._send_frame(sock, dest, frame_id & 0xFFFFFFFF, jpeg)
                    frame_id += 1
            except Exception:
                pass

            time.sleep(max(0.0, (1.0 / fps) - (time.monotonic() - t)))

        sock.close()

    # ── ctrl listener thread ──────────────────────────────────────────────────

    def _ctrl_listener(self):
        while True:
            with self._lock:
                if not self._running:
                    return
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.settimeout(3.0)
                conn.connect((self.server_ip, self.ctrl_port))
                conn.settimeout(2.0)
                buf = ""
                while True:
                    with self._lock:
                        if not self._running:
                            conn.close()
                            return
                    try:
                        chunk = conn.recv(256).decode("utf-8", errors="ignore")
                        if not chunk:
                            break
                        buf += chunk
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            line = line.strip()
                            if line.startswith("RDCONF:"):
                                try:
                                    _, q, f = line.split(":")
                                    with self._lock:
                                        self._quality = max(1, min(95, int(q)))
                                        self._fps     = max(1, min(30, int(f)))
                                except Exception:
                                    pass
                            elif line == "RDSTOP":
                                self.stop()
                                conn.close()
                                return
                    except socket.timeout:
                        continue
                    except Exception:
                        break
                conn.close()
            except Exception:
                pass
            time.sleep(2)

class RDS:
    def __init__(self, host: str="0.0.0.0", udp_port: int=57908):
        self.host      = host
        self.udp_port  = udp_port
        self.ctrl_port = udp_port + CTRL_PORT_OFFSET

        self._running    = False
        self._ctrl_sock  = None
        self._ctrl_ready = False
        self._frame      = None
        self._photo      = None
        self._rx_fps     = 0
        self._send_after = None

        self._win    = None
        self._canvas = None

    # ── public ────────────────────────────────────────────────────────────────

    def start(self):
        """Opens the viewer window. Call from the tkinter main thread."""
        self._running = True
        self._build_ui()
        threading.Thread(target=self._udp_receiver, daemon=True).start()
        threading.Thread(target=self._ctrl_listener, daemon=True).start()
        self._win.after(100, self._update_canvas)

    def stop(self):
        """Closes the viewer and tells the agent to stop."""
        self._running    = False
        self._ctrl_ready = False
        if self._ctrl_sock:
            try:
                self._ctrl_sock.sendall(b"RDSTOP\n")
                self._ctrl_sock.close()
            except Exception:
                pass
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._win = tkinter.Toplevel()
        self._win.title(f"Remote Desktop — {self.host}:{self.udp_port}")
        self._win.configure(bg="#1a1a1a")
        self._win.resizable(True, True)
        self._win.protocol("WM_DELETE_WINDOW", self.stop)

        self._canvas = tkinter.Canvas(self._win, bg="black", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)

        ctrl_frame = ttk.Frame(self._win)
        ctrl_frame.pack(fill="x", side="bottom", padx=8, pady=4)

        # quality slider
        ttk.Label(ctrl_frame, text="Quality:").pack(side="left")
        self._quality_var = tkinter.IntVar(value=50)
        ttk.Scale(ctrl_frame, from_=1, to=95, orient="horizontal", length=150,
                  variable=self._quality_var,
                  command=self._on_slider_change).pack(side="left", padx=(2, 8))
        self._quality_label = ttk.Label(ctrl_frame, text="50%")
        self._quality_label.pack(side="left", padx=(0, 16))

        # fps slider
        ttk.Label(ctrl_frame, text="FPS:").pack(side="left")
        self._fps_var = tkinter.IntVar(value=15)
        ttk.Scale(ctrl_frame, from_=1, to=30, orient="horizontal", length=120,
                  variable=self._fps_var,
                  command=self._on_slider_change).pack(side="left", padx=(2, 8))
        self._fps_label = ttk.Label(ctrl_frame, text="15 fps")
        self._fps_label.pack(side="left", padx=(0, 16))

        self._status_label = ttk.Label(ctrl_frame, text="Waiting for agent...")
        self._status_label.pack(side="right")

    # ── slider ────────────────────────────────────────────────────────────────

    def _on_slider_change(self, *_):
        """Debounce: wait 150 ms of silence then send."""
        if self._send_after is not None:
            self._win.after_cancel(self._send_after)
        self._send_after = self._win.after(150, self._send_config)

    def _send_config(self):
        """Runs on main thread. Pushes current slider values to agent."""
        self._send_after = None
        q = int(self._quality_var.get())
        f = int(self._fps_var.get())
        self._quality_label.configure(text=f"{q}%")
        self._fps_label.configure(text=f"{f} fps")
        if self._ctrl_sock and self._ctrl_ready:
            try:
                self._ctrl_sock.sendall(f"RDCONF:{q}:{f}\n".encode())
            except Exception as e:
                print(f"[RD] ctrl send error: {e}")
                self._ctrl_ready = False

    # ── UDP receiver thread ───────────────────────────────────────────────────

    def _udp_receiver(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        sock.bind(("0.0.0.0", self.udp_port))
        sock.settimeout(1.0)

        buffer        = {}
        last_complete = -1
        frame_times   = []

        while self._running:
            try:
                packet, _ = sock.recvfrom(UDP_MAX + HEADER_SIZE + 64)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[RD] udp recv error: {e}")
                break

            if len(packet) < HEADER_SIZE:
                continue

            frame_id, chunk_idx, total_chunks, chunk_len = struct.unpack_from(
                HEADER_FMT, packet, 0
            )
            payload = packet[HEADER_SIZE: HEADER_SIZE + chunk_len]

            if frame_id < last_complete:
                continue

            if frame_id not in buffer:
                buffer = {k: v for k, v in buffer.items() if k >= frame_id - 5}
                buffer[frame_id] = {}

            buffer[frame_id][chunk_idx] = payload

            if len(buffer[frame_id]) == total_chunks:
                chunks     = buffer.pop(frame_id)
                jpeg_bytes = b"".join(chunks[i] for i in range(total_chunks))
                try:
                    img = Image.open(io.BytesIO(jpeg_bytes))
                    img.load()
                    self._frame = img
                    last_complete = frame_id
                    now = time.monotonic()
                    frame_times.append(now)
                    frame_times   = [t for t in frame_times if now - t <= 1.0]
                    self._rx_fps  = len(frame_times)
                except Exception:
                    pass

        sock.close()

    # ── TCP ctrl listener ─────────────────────────────────────────────────────

    def _ctrl_listener(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.ctrl_port))
        srv.listen(1)
        srv.settimeout(2.0)
        print(f"[RD] ctrl listening on :{self.ctrl_port}")

        while self._running:
            try:
                conn, addr = srv.accept()
                self._ctrl_sock  = conn
                self._ctrl_ready = True
                print(f"[RD] agent connected from {addr}")
                self._win.after(0, self._send_config)
                break
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[RD] ctrl listen error: {e}")
                break
        srv.close()

    # ── canvas refresh ────────────────────────────────────────────────────────

    def _update_canvas(self):
        if not self._running:
            return
        if self._frame is not None:
            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
            img = self._frame.resize((cw, ch), Image.LANCZOS) if cw > 1 and ch > 1 else self._frame
            photo = ImageTk.PhotoImage(img)
            self._photo = photo
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=photo)
            w, h = self._frame.size
            dot = "● " if self._ctrl_ready else "○ "
            self._status_label.configure(text=f"{dot}{w}×{h}  |  {self._rx_fps} fps rx")
        self._win.after(33, self._update_canvas)
