import ttkbootstrap as ttk
from tkinter import Frame

class AddTokenPage(Frame):
    def __init__(self, parent, app_reference):
        super().__init__(parent)
        self.app = app_reference
        
        # Configure the frame to fill the available space
        self.pack(fill="both", expand=True)
        
        # Add title
        self.title_label = ttk.Label(self, text="Add New Token", font="Calibri 16 bold")
        self.title_label.pack(pady=20)
        
        # Add back button at the top
        self.back_button = ttk.Button(
            self,
            text="← Back",
            command=self.go_back,
            width=10,
            style="primary.TButton"
        )
        self.back_button.place(x=20, y=20)
        
        # Add buttons for different methods
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Manual entry button
        self.manual_btn = ttk.Button(
            self.button_frame,
            text="Manual Entry",
            command=self.app.add_token_manually,
            width=20
        )
        self.manual_btn.pack(pady=10)
        
        # QR code button
        self.qr_btn = ttk.Button(
            self.button_frame,
            text="Scan QR Code",
            command=self.app.add_token_from_qr,
            width=20
        )
        self.qr_btn.pack(pady=10)
        
        # Import from file button
        self.import_btn = ttk.Button(
            self.button_frame,
            text="Import from File",
            command=self.app.bulk_import_tokens,
            width=20
        )
        self.import_btn.pack(pady=10)
        
    def go_back(self):
        """Go back to the main view"""
        # Destroy this page
        self.pack_forget()
        self.destroy()
        
        # Show the main view
        self.app.show_main_view() 