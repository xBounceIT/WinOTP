import ttkbootstrap as ttk
from tkinter import Frame

class ImportTokensPage(Frame):
    def __init__(self, parent, app_reference):
        super().__init__(parent)
        self.app = app_reference
        
        # Configure the frame to fill the available space
        self.pack(fill="both", expand=True)
        
        # Add title
        self.title_label = ttk.Label(self, text="Import Tokens", font="Calibri 16 bold")
        self.title_label.pack(pady=20)
        
        # Add back button at the top
        self.back_button = ttk.Button(
            self,
            image=self.app.back_icon if hasattr(self.app, 'back_icon') else None,
            text="Back" if not hasattr(self.app, 'back_icon') else None,
            command=self.go_back,
            width=10 if not hasattr(self.app, 'back_icon') else None,
            style="primary.TButton"
        )
        self.back_button.place(x=20, y=20)
        
        # Add buttons for different import methods
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Import from WinOTP JSON file button
        self.winotp_btn = ttk.Button(
            self.button_frame,
            text="Import from WinOTP",
            command=self.app.bulk_import_tokens,
            width=20
        )
        self.winotp_btn.pack(pady=10)
        
    def go_back(self):
        """Go back to the add token page"""
        # Cancel any pending after callbacks in the app
        if hasattr(self.app, 'after_id'):
            self.app.after_cancel(self.app.after_id)
            self.app.after_id = None
            
        # Show the add token page first
        self.app.add_token()
        
        # Then destroy this page
        self.pack_forget()
        self.destroy() 