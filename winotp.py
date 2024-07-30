import ttkbootstrap as ttk
from tkinter import filedialog
import json
import pyotp
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode
import re
from ttkbootstrap.icons import Icon

root = ttk.Window(themename='journal')
root.title("WinOTP")
w = 400
h = 600

ws = root.winfo_screenwidth()
hs = root.winfo_screenheight()

x = (ws/2) - (w/2)
y = (hs/2) - (h/2)

root.geometry('%dx%d+%d+%d' % (w, h, x, y))
root.minsize(w, h)
root.maxsize(w, h)

root.columnconfigure(0, weight=100)

frames = {}

def delete_frames(frames):
    for token in frames:
        frames[token]["name_label"].grid_forget()
        frames[token]["code_label"].grid_forget()
        frames[token]["time_remaining_label"].grid_forget()
        frames[token]["frame"].grid_forget()
        frames[token]["copy_btn"].grid_forget()

def grid_frames(frames):
    row = 1
    for token in frames:
        frames[token]["frame"].grid(row=row, column=0, columnspan=4, pady=20, padx=20, sticky='ew')
        frames[token]["frame"].grid_columnconfigure(0, weight=1)
        frames[token]["frame"].grid_columnconfigure(1, weight=1)
        frames[token]["frame"].grid_columnconfigure(2, weight=1)
        
        frames[token]["name_label"].grid(row=0, column=0, sticky='w')
        frames[token]["code_label"].grid(row=1, column=0, sticky='ew')
        frames[token]["copy_btn"].grid(row=1, column=1, sticky='w')
        frames[token]["time_remaining_label"].grid(row=1, column=2, sticky='e')

        row += 1

def init_frames():
    with open("config.json", "r") as f:
        data = json.load(f)

    for token in data:
        totp = pyotp.TOTP(data[token]["secret"])
        frames[token] = data[token]
        frames[token]["secret"] = data[token]["secret"]
        frames[token]["code"] = ttk.StringVar(value=totp.now())
        frames[token]["frame"] = ttk.Frame(master=root, width=400, height=100)
        frames[token]["name"] = ttk.StringVar(value=token)
        frames[token]["time_remaining"] = ttk.StringVar(value=int(totp.interval - datetime.now().timestamp() % totp.interval))
        frames[token]["name_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["name"])
        frames[token]["code_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["code"], font="Calibri 24")
        frames[token]["time_remaining_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["time_remaining"], font="Calibri 16")
        frames[token]["copy_btn"] = ttk.Button(master=frames[token]["frame"], text="Copy", command=lambda n=frames[token]["name"], t=frames[token]["code_label"]: copy_totp(n, t, root))
    
    return frames

def copy_totp(name, totp, root):
    # TODO: Aggiungere popup
    root.clipboard_clear()
    root.clipboard_append(totp["text"])

def update(frames, root):
    for token in frames:
        totp = pyotp.TOTP(frames[token]["secret"])
        time_remaining = int(totp.interval - datetime.now().timestamp() % totp.interval)
        frames[token]["code"].set(totp.now())
        frames[token]["time_remaining"].set(time_remaining)
    
    root.after(1000, update, frames, root)

def add_token():
    filename = filedialog.askopenfilename()
    qr_data = decode(Image.open(filename))
    uri = qr_data[0].data.decode("utf-8")
    print(uri)
    pattern = r'otpauth://totp/(?P<name>[^?]+)\?secret=(?P<secret>[^&]+)'
    match = re.search(pattern, uri)
    
    if match:
        name = match.group('name').replace('%20', ' ')
        secret = match.group('secret')
    token = {name: {"secret": secret}}
    config = read_json("config.json")
    config.update(token)
    write_json("config.json", config)
    frames = init_frames()
    delete_frames(frames)
    grid_frames(frames)

def read_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def write_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def main():
    search_frame = ttk.Frame(master=root, width=w)
    search_frame.grid(row=0, column=0, pady=20, padx=20, sticky="we")
    search_frame.grid_columnconfigure(0, weight=1)
    search_frame.grid_columnconfigure(1, weight=1)
    search_frame.grid_columnconfigure(2, weight=1)

    search_input = ttk.Entry(master=search_frame)
    search_input.grid(row=0, column=0, sticky='ew')

    search_button = ttk.Button(master=search_frame, text="Search")
    search_button.grid(row=0, column=1, sticky='w')
    
    #add_icon = Icon(name="plus-circle")
    add_btn = ttk.Button(master=search_frame, command=lambda: add_token(), text="+")
    add_btn.grid(row=0, column=2, sticky='e')

    

    frames = init_frames()
    grid_frames(frames)

    update(frames, root)

    root.mainloop()

if __name__ == "__main__":
    main()
