import ttkbootstrap as ttk
from tkinter import Frame, Label

class SettingsPage(Frame):
    def __init__(self, parent, app_reference):
        super().__init__(parent)
        self.app = app_reference
        
        # Configure the frame to fill the available space
        self.pack(fill="both", expand=True)
        
        # Add title
        self.title_label = ttk.Label(self, text="Settings", font="Calibri 16 bold")
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
        
        # Add settings content
        self.settings_frame = ttk.Frame(self)
        self.settings_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Add import/export buttons
        self.import_btn = ttk.Button(
            self.settings_frame,
            text="Import Tokens",
            command=self.app.bulk_import_tokens,
            width=20
        )
        self.import_btn.pack(fill="x", pady=10)
        
        # Add about section
        self.about_frame = ttk.LabelFrame(self.settings_frame, text="About")
        self.about_frame.pack(fill="both", expand=True, pady=20)
        
        self.about_text = Label(
            self.about_frame,
            text="WinOTP - A Windows TOTP Authenticator\n"
                 "Version 1.0.0\n\n"
                 "Created by Daniel D'Angeli\n"
                 "Icons by Feather Icons",
            justify="left"
        )
        self.about_text.pack(padx=10, pady=10, anchor="w")
        
    def go_back(self):
        """Go back to the main view"""
        # Destroy this page
        self.pack_forget()
        self.destroy()
        
        # Make main container visible again
        self.app.main_container.pack(fill="both", expand=True)
        
        # Show the main view
        self.app.show_main_view() 