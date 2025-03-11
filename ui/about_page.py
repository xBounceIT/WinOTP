import ttkbootstrap as ttk
from tkinter import Frame, Label

class AboutPage(Frame):
    def __init__(self, parent, app_reference):
        super().__init__(parent)
        self.app = app_reference
        
        # Configure the frame to fill the available space
        self.pack(fill="both", expand=True)
        
        # Add title
        self.title_label = ttk.Label(self, text="About WinOTP", font="Calibri 16 bold")
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
        
        # Create content frame
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # App title and version
        self.app_title = ttk.Label(
            self.content_frame,
            text="WinOTP",
            font="Calibri 24 bold"
        )
        self.app_title.pack(anchor="w", pady=(0, 5))
        
        self.version = ttk.Label(
            self.content_frame,
            text="Version 1.0.0",
            font="Calibri 12"
        )
        self.version.pack(anchor="w", pady=(0, 20))
        
        # Description
        self.description = ttk.Label(
            self.content_frame,
            text="WinOTP is a Windows TOTP Authenticator that provides secure two-factor authentication "
                 "code generation. It supports manual token entry, QR code scanning, and bulk import/export "
                 "of tokens.",
            wraplength=400,
            justify="left"
        )
        self.description.pack(anchor="w", pady=(0, 20))
        
        # Features
        self.features_title = ttk.Label(
            self.content_frame,
            text="Key Features:",
            font="Calibri 12 bold"
        )
        self.features_title.pack(anchor="w", pady=(0, 5))
        
        features_text = (
            "• Secure TOTP code generation\n"
            "• QR code scanning support\n"
            "• Manual token entry\n"
            "• Bulk import/export functionality\n"
            "• Search and sort capabilities\n"
            "• Modern and intuitive interface"
        )
        self.features = ttk.Label(
            self.content_frame,
            text=features_text,
            justify="left"
        )
        self.features.pack(anchor="w", pady=(0, 20))
        
        # Credits
        self.credits_title = ttk.Label(
            self.content_frame,
            text="Credits:",
            font="Calibri 12 bold"
        )
        self.credits_title.pack(anchor="w", pady=(0, 5))
        
        credits_text = (
            "Created by Daniel D'Angeli\n"
            "Icons by Feather Icons"
        )
        self.credits = ttk.Label(
            self.content_frame,
            text=credits_text,
            justify="left"
        )
        self.credits.pack(anchor="w", pady=(0, 20))
        
    def go_back(self):
        """Go back to the settings page"""
        # Cancel any pending after callbacks in the app
        if hasattr(self.app, 'after_id'):
            self.app.after_cancel(self.app.after_id)
            self.app.after_id = None
            
        # Show the settings page again
        self.app.show_settings()
        
        # Then destroy this page
        self.pack_forget()
        self.destroy() 