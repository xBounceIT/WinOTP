import ttkbootstrap as ttk
import json
import pyotp
from datetime import datetime

root = ttk.Window(themename='journal')
root.title("WinOTP")
w = 500
h = 600

ws = root.winfo_screenwidth()
hs = root.winfo_screenheight()

x = (ws/2) - (w/2)
y = (hs/2) - (h/2)

root.geometry('%dx%d+%d+%d' % (w, h, x, y))
root.minsize(500,600)
root.maxsize(500,600)

def init_frames(data):
    frames = {}
    for token in data:
        totp = pyotp.TOTP(data[token]["seed"])
        frames[token] = data[token]
        frames[token]["seed"] = data[token]["seed"]
        frames[token]["code"] = ttk.StringVar(value=totp.now())
        frames[token]["frame"] = ttk.Frame(master=root, width=400, height=100)
        frames[token]["name"] = ttk.StringVar(value=token)
        frames[token]["time_remaining"] = ttk.StringVar(value=int(totp.interval - datetime.now().timestamp() % totp.interval))
        frames[token]["name_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["name"])
        frames[token]["code_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["code"], font="Calibri 24")
        frames[token]["time_remaining_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["time_remaining"], font="Calibri 16")
        frames[token]["name_label"].pack()
        frames[token]["code_label"].pack()
        frames[token]["time_remaining_label"].pack()
        frames[token]["frame"].pack(pady = 20, padx = 20)
        copy_btn = ttk.Button(master=frames[token]["frame"], text="Copy", command=lambda n=frames[token]["name"], t=frames[token]["code_label"]: copy_totp(n, t, root))
        copy_btn.pack()
    
    return frames

def copy_totp(name, totp, root):
    root.clipboard_clear()
    root.clipboard_append(totp["text"])

def update(frames, root):

    for token in frames:
        totp = pyotp.TOTP(frames[token]["seed"])
        time_remaining = int(totp.interval - datetime.now().timestamp() % totp.interval)
        frames[token]["code"].set(totp.now())
        frames[token]["time_remaining"].set(time_remaining)
    
    root.after(1000, update, frames, root)

def main():

    search_frame = ttk.Frame(master=root, width=400)
    search_input = ttk.Entry(master=search_frame)
    search_button = ttk.Button(master=search_frame, text="Search")
    search_input.pack(side="left")
    search_button.pack(side="left")
    search_frame.pack(pady = 20, padx = 20)

    with open("config.json", "r") as f:
        data = json.load(f)
   
    frames = init_frames(data)

    update(frames, root)

    root.mainloop()

if __name__ == "__main__":
    main()