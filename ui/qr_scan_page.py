import ttkbootstrap as ttk
from tkinter import Frame, Label, filedialog

class QRScanPage(Frame):
    def __init__(self, parent, app_reference):
        super().__init__(parent)
        self.app = app_reference
        
        # Configure the frame to fill the available space
        self.pack(fill="both", expand=True)
        
        # Add title
        self.title_label = ttk.Label(self, text="Scan QR Code", font="Calibri 16 bold")
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
        
        # Instructions
        self.instructions_label = Label(
            self.content_frame, 
            text="Select a QR code image file to scan.\nSupported formats: PNG, JPG, JPEG, GIF, BMP",
            justify="center"
        )
        self.instructions_label.pack(pady=20)
        
        # Select image button
        self.select_btn = ttk.Button(
            self.content_frame,
            text="Select QR Code Image",
            command=self.select_qr_image,
            width=25
        )
        self.select_btn.pack(pady=10)
        
        # Status label
        self.status_label = Label(
            self.content_frame,
            text="",
            justify="center"
        )
        self.status_label.pack(pady=10)
        
    def select_qr_image(self):
        """Select a QR code image and process it"""
        # Open file dialog to select an image
        file_path = filedialog.askopenfilename(
            title="Select QR Code Image",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.status_label.config(text="Processing QR code...")
            # Pass the file path to the app's QR scanning method
            self.app.process_qr_image(file_path, self)
            
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