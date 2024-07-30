import ttkbootstrap as ttk
from tkinter import filedialog, Canvas, Scrollbar
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

x = (ws / 2) - (w / 2)
y = (hs / 2) - (h / 2)

root.geometry('%dx%d+%d+%d' % (w, h, x, y))
root.minsize(w, h)
root.maxsize(w, h)
# Create a canvas
canvas = Canvas(root, width=w)

canvas.grid(row=1, column=0, sticky="nsew")

# Add vertical scrollbar to the canvas
v_scrollbar = Scrollbar(root, orient="vertical", command=canvas.yview)
v_scrollbar.grid(row=1, column=1, sticky="ns")

# Configure the canvas to use the scrollbars
canvas.configure(yscrollcommand=v_scrollbar.set)
canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
# Create an inner frame to hold the widgets
scrollable_frame = ttk.Frame(canvas)
scrollable_frame.columnconfigure(0, weight=1)

canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def configure_scroll_region(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

def configure_window_size(event):
    canvas.itemconfig(canvas_window, width=event.width)

scrollable_frame.bind("<Configure>", configure_scroll_region)
canvas.bind("<Configure>", configure_window_size)

root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)

search_frame = ttk.Frame(master=scrollable_frame, width=w)
search_frame.grid(row=0, column=0, pady=20, padx=20, sticky="ew")
search_frame.grid_columnconfigure(0, weight=1)
search_frame.grid_columnconfigure(1, weight=1)
search_frame.grid_columnconfigure(2, weight=1)

search_input = ttk.Entry(master=search_frame)
search_input.grid(row=0, column=0, sticky='ew')

search_button = ttk.Button(master=search_frame, text="Search")
search_button.grid(row=0, column=1, sticky='w')

add_btn = ttk.Button(master=search_frame, command=lambda: add_token(), text="+")
add_btn.grid(row=0, column=2, sticky='e')

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
        frames[token]["frame"] = ttk.Frame(master=scrollable_frame, width=400, height=100)
        frames[token]["name"] = ttk.StringVar(value=token)
        frames[token]["time_remaining"] = ttk.StringVar(value=int(totp.interval - datetime.now().timestamp() % totp.interval))
        frames[token]["name_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["name"])
        frames[token]["code_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["code"], font="Calibri 24")
        frames[token]["time_remaining_label"] = ttk.Label(master=frames[token]["frame"], textvariable=frames[token]["time_remaining"], font="Calibri 16")
        frames[token]["copy_btn"] = ttk.Button(master=frames[token]["frame"], text="Copy", command=lambda n=frames[token]["name"], t=frames[token]["code_label"]: copy_totp(n, t, root))
    
    return frames

def copy_totp(name, totp, root):
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

def on_mouse_wheel(event):
    # Get the current position of the scrollbar
    current_view = canvas.yview()
    if (event.delta > 0 and current_view[0] <= 0) or (event.delta < 0 and current_view[1] >= 1):
        return  # Prevent scrolling if already at the top or bottom
    canvas.yview_scroll(-1 * int(event.delta / 120), "units")

def main():
    frames = init_frames()
    grid_frames(frames)

    update(frames, root)

    # Bind mouse wheel event to the canvas
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)
    canvas.bind_all("<Button-4>", on_mouse_wheel)
    canvas.bind_all("<Button-5>", on_mouse_wheel)

    root.mainloop()

if __name__ == "__main__":
    main()
