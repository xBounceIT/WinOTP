import ttkbootstrap as ttk
from tkinter import Frame, Label, Entry

class ManualEntryPage(Frame):
    def __init__(self, parent, app_reference):
        super().__init__(parent)
        self.app = app_reference
        
        # Configure the frame to fill the available space
        self.pack(fill="both", expand=True)
        
        # Add title
        self.title_label = ttk.Label(self, text="Add Token Manually", font="Calibri 16 bold")
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
        
        # Create form
        self.form_frame = ttk.Frame(self)
        self.form_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Issuer field
        self.issuer_label = Label(self.form_frame, text="Issuer (e.g. Google, GitHub):")
        self.issuer_label.pack(anchor="w")
        self.issuer_entry = Entry(self.form_frame, width=40)
        self.issuer_entry.pack(fill="x", pady=(0, 10))
        
        # Account name field
        self.name_label = Label(self.form_frame, text="Account Name (e.g. username, email):")
        self.name_label.pack(anchor="w")
        self.name_entry = Entry(self.form_frame, width=40)
        self.name_entry.pack(fill="x", pady=(0, 10))
        
        # Secret field
        self.secret_label = Label(self.form_frame, text="Secret Key (Base32 encoded):")
        self.secret_label.pack(anchor="w")
        self.secret_entry = Entry(self.form_frame, width=40)
        self.secret_entry.pack(fill="x", pady=(0, 10))
        
        # Add button
        self.add_btn = ttk.Button(
            self.form_frame,
            text="Add Token",
            command=self.add_token
        )
        self.add_btn.pack(pady=10)
        
    def add_token(self):
        """Add the token with the entered information"""
        self.app.add_manual_token(
            None,  # No window to destroy
            self.issuer_entry.get(),
            self.secret_entry.get(),
            self.name_entry.get()
        )
        # Go back to the add token page after adding
        self.go_back()
        
    def go_back(self):
        """Go back to the add token page"""
        # Destroy this page
        self.pack_forget()
        self.destroy()
        
        # Show the add token page
        self.app.add_token() 