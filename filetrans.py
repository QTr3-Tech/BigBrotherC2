import socket
import hashlib
import struct
import os

def recv_exact(sock, num_bytes):
    """
    Receive exact number of bytes from socket.
    
    Args:
        sock: Socket object
        num_bytes: Number of bytes to receive
    
    Returns:
        Bytes received
    """
    data = b''
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            raise ConnectionError("Connection closed unexpectedly")
        data += chunk
    return data


def send_files(sock, filepaths):
    """
    Send multiple files through a socket connection.
    
    Args:
        sock: Connected socket object
        filepaths: List of file paths to send
    
    Returns:
        Number of successfully sent files
    """
    try:
        # Send number of files
        num_files = len(filepaths)
        sock.sendall(struct.pack('!I', num_files))
        print(f"Sending {num_files} file(s)...")
        
        success_count = 0
        
        for i, filepath in enumerate(filepaths, 1):
            print(f"\n[{i}/{num_files}] Sending: {os.path.basename(filepath)}")
            
            if send_single_file(sock, filepath):
                success_count += 1
            else:
                print(f"Failed to send: {filepath}")
        
        print(f"\nTotal: {success_count}/{num_files} files sent successfully")
        return success_count
        
    except Exception as e:
        print(f"Error sending files: {e}")
        return 0


def send_single_file(sock, filepath):
    """
    Send a single file with the 3-step protocol:
    1. Send hash
    2. Send total size
    3. Send bytes
    
    Args:
        sock: Connected socket object
        filepath: Path to the file to send
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read file and calculate hash
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        filesize = len(file_data)
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Send filename
        filename = os.path.basename(filepath)
        filename_bytes = filename.encode('utf-8')
        sock.sendall(struct.pack('!I', len(filename_bytes)))
        sock.sendall(filename_bytes)
        
        # Step 1: Send hash
        print(f"  Step 1: Sending hash...")
        sock.sendall(file_hash.encode('utf-8'))
        
        # Step 2: Send total size
        print(f"  Step 2: Sending size ({round(filesize / 1024 / 1024, 2)} MB)...")
        sock.sendall(struct.pack('!Q', filesize))
        
        # Step 3: Send bytes
        print(f"  Step 3: Sending file data...")
        chunk_size = 4096
        sent = 0
        
        with open(filepath, 'rb') as f:
            try:
                while sent < filesize:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    sent += len(chunk)
            except Exception as e:
                print(e)
                return False
        print(f"  ✓ Sent {round(sent / 1024 / 1024, 2)} MB")
        return True
        
    except Exception as e:
        print(f"  ✗ Error sending file: {e}")
        return False


def receive_files(sock, save_dir='.'):
    """
    Receive multiple files through a socket connection.
    
    Args:
        sock: Connected socket object
        save_dir: Directory to save the received files
    
    Returns:
        List of successfully received file paths
    """
    try:
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Receive number of files
        num_files = struct.unpack('!I', recv_exact(sock, 4))[0]
        print(f"Expecting {num_files} file(s)...\n")
        
        received_files = []
        
        for i in range(1, num_files + 1):
            print(f"[{i}/{num_files}] Receiving file...")
            
            filepath = receive_single_file(sock, save_dir)
            
            if filepath:
                received_files.append(filepath)
                print(f"  ✓ Saved: {filepath}")
            else:
                print(f"  ✗ Failed to receive file {i}")
        
        print(f"\nTotal: {len(received_files)}/{num_files} files received successfully")
        return received_files
        
    except Exception as e:
        print(f"Error receiving files: {e}")
        return []


def receive_single_file(sock, save_dir):
    """
    Receive a single file with the 3-step protocol:
    1. Receive hash
    2. Receive total size
    3. Receive bytes
    
    Args:
        sock: Connected socket object
        save_dir: Directory to save the file
    
    Returns:
        Path to saved file if successful, None otherwise
    """
    try:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        # Receive filename
        filename_len = struct.unpack('!I', recv_exact(sock, 4))[0]
        filename = recv_exact(sock, filename_len).decode('utf-8')
        print(f"  Filename: {filename}")
        
        # Step 1: Receive hash
        print(f"  Step 1: Receiving hash...")
        expected_hash = recv_exact(sock, 64).decode('utf-8')
        
        # Step 2: Receive total size
        print(f"  Step 2: Receiving size...")
        filesize = struct.unpack('!Q', recv_exact(sock, 8))[0]
        print(f"  Size: {round(filesize / 1024 / 1024, 2)} MB")
        
        # Step 3: Receive bytes
        print(f"  Step 3: Receiving file data...")
        filepath = os.path.join(save_dir, filename)
        received = 0
        
        with open(filepath, 'wb') as f:
            try:
                while received < filesize:
                    chunk_size = min(4096, filesize - received)
                    chunk = recv_exact(sock, chunk_size)
                    f.write(chunk)
                    received += len(chunk)
            except Exception as e:
                print(e)
                return None
        # Verify integrity
        with open(filepath, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        if file_hash == expected_hash:
            print(f"  ✓ Integrity verified")
            return filepath
        else:
            print(f"  ✗ Integrity check failed!")
            os.remove(filepath)
            return None

    except Exception as e:
        print(f"  ✗ Error receiving file: {e}")
        return None


# Example usage:
if __name__ == "__main__":
    # Server example
    def run_server(port=5000):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', port))
        server.listen(1)
        print(f"Server listening on port {port}")
        
        conn, addr = server.accept()
        print(f"Connection from {addr}\n")
        
        # Receive files
        received_files = receive_files(conn, save_dir='./received')
        print(f"\nReceived files: {received_files}")
        
        conn.close()
        server.close()
    
    # Client example
    def run_client(host='localhost', port=5000, filepaths=['test.txt']):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))
        
        # Send files
        send_files(client, filepaths)
        
        client.close()
    
    # Uncomment to test:
    # run_server()
    # run_client(filepaths=['file1.txt', 'file2.pdf', 'file3.jpg'])