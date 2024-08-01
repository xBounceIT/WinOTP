import ttkbootstrap as ttk
from tkinter import filedialog, Canvas, Scrollbar
import json
import pyotp
from datetime import datetime
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
import re

class TOTPFrame(ttk.Frame):
    def __init__(self, master, name, secret):
        super().__init__(master, width=400, height=100)
        self.name = name
        self.secret = secret
        self.totp = pyotp.TOTP(self.secret)
        self.code = ttk.StringVar(value=self.totp.now())
        self.time_remaining = ttk.StringVar(value=self.get_time_remaining())

        self.name_label = ttk.Label(self, text=self.name)
        self.code_label = ttk.Label(self, textvariable=self.code, font="Calibri 24")
        self.time_remaining_label = ttk.Label(self, textvariable=self.time_remaining, font="Calibri 16")
        self.copy_btn = ttk.Button(self, text="Copy", command=self.copy_totp)

        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.name_label.grid(row=0, column=0, sticky='w')
        self.code_label.grid(row=1, column=0, sticky='ew')
        self.copy_btn.grid(row=1, column=1, sticky='w')
        self.time_remaining_label.grid(row=1, column=2, sticky='e', padx=20)

    def update(self):
        self.code.set(self.totp.now())
        self.time_remaining.set(self.get_time_remaining())

    def get_time_remaining(self):
        return int(self.totp.interval - datetime.now().timestamp() % self.totp.interval)

    def copy_totp(self):
        self.master.master.clipboard_clear()
        self.master.master.clipboard_append(self.code.get())

class SearchBar(ttk.Frame):
    def __init__(self, master, add_token_callback):
        super().__init__(master, width=master.width)
        self.grid(row=0, column=0, pady=20, padx=20, sticky="ew")
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.search_input = ttk.Entry(self)
        self.search_input.grid(row=0, column=0, sticky='ew')

        search_button_icon = ImageTk.PhotoImage(Image.open(r"C:\Users\dange\Desktop\Projects\WinOTP\static\images\search.png").resize((16,16), Image.LANCZOS))
        self.search_button = ttk.Button(self, image=search_button_icon, compound=ttk.CENTER)
        self.search_button.image = search_button_icon
        self.search_button.grid(row=0, column=1, sticky='w')

        self.add_btn = ttk.Button(self, command=add_token_callback, text="+")
        self.add_btn.grid(row=0, column=2, sticky='e')

        self.settings_btn = ttk.Button(self, text="S")
        self.settings_btn.grid(row=0, column=3, sticky='e')

class WinOTP(ttk.Window):
    def __init__(self):
        super().__init__(themename='journal')
        self.title("WinOTP")
        self.width = 500
        self.height = 600
        self.center_window()
        self.resizable(False, False)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.search_bar = SearchBar(self, self.add_token)
        self.canvas = Canvas(self, width=self.width)
        self.canvas.grid(row=1, column=0, sticky="nsew")

        self.v_scrollbar = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.v_scrollbar.grid(row=1, column=1, sticky="ns")

        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.columnconfigure(0, weight=1)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self.configure_scroll_region)
        self.canvas.itemconfig(self.canvas_window, width=self.width)

        self.frames = {}
        self.init_frames()

        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)

        self.after(1000, self.update_frames)

    def center_window(self):
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws / 2) - (self.width / 2)
        y = (hs / 2) - (self.height / 2)
        self.geometry('%dx%d+%d+%d' % (self.width, self.height, x, y))

    def configure_scroll_region(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def init_frames(self):
        config = self.read_json("config.json")
        for token, data in config.items():
            self.frames[token] = TOTPFrame(self.scrollable_frame, token, data["secret"])
            self.frames[token].grid(row=len(self.frames), column=0, pady=20, padx=20, sticky='ew')

    def update_frames(self):
        for frame in self.frames.values():
            frame.update()
        self.after(1000, self.update_frames)

    def add_token(self):
        filename = filedialog.askopenfilename()
        if filename:
            qr_data = decode(Image.open(filename))
            uri = qr_data[0].data.decode("utf-8")
            pattern = r'otpauth://totp/(?P<name>[^?]+)\?secret=(?P<secret>[^&]+)'
            match = re.search(pattern, uri)
            
            if match:
                name = match.group('name').replace('%20', ' ')
                secret = match.group('secret')
                config = self.read_json("config.json")
                config[name] = {"secret": secret}
                self.write_json("config.json", config)
                
                new_frame = TOTPFrame(self.scrollable_frame, name, secret)
                new_frame.grid(row=len(self.frames), column=0, pady=20, padx=20, sticky='ew')
                self.frames[name] = new_frame

    @staticmethod
    def read_json(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    @staticmethod
    def write_json(file_path, data):
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

    def on_mouse_wheel(self, event):
        current_view = self.canvas.yview()
        if (event.delta > 0 and current_view[0] <= 0) or (event.delta < 0 and current_view[1] >= 1):
            return
        self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

if __name__ == "__main__":
    app = WinOTP()
    app.mainloop()