from pathlib import Path
import os

def serialize(dir):
    string = ""
    target_dir = Path(dir)
    for i in list(target_dir.iterdir()):
        string += f"{i.name};;{i.absolute()}@@{i.is_dir()}<>{os.path.getsize(i.absolute())}~~"
    return string

dir_content = serialize(".")

def deserialize(string):
    deser_dir = {}
    for i in string.split("~~"):
        try:
            file_name, attr = i.split(";;")
            full_path, is_dir = attr.split("@@")
            is_dir, size = is_dir.split("<>")
            deser_dir[file_name] = (full_path, size, is_dir)
        except:pass
    return deser_dir
