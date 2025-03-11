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
        
        # Add back button at the top left
        self.back_button = ttk.Button(
            self,
            image=self.app.back_icon if hasattr(self.app, 'back_icon') else None,
            text="Back" if not hasattr(self.app, 'back_icon') else None,
            command=self.go_back,
            width=10 if not hasattr(self.app, 'back_icon') else None,
            style="primary.TButton"
        )
        self.back_button.place(x=20, y=20)
        
        # Add about button at the top right
        self.about_button = ttk.Button(
            self,
            image=self.app.question_icon if hasattr(self.app, 'question_icon') else None,
            text="About" if not hasattr(self.app, 'question_icon') else None,
            command=self.show_about,
            width=10 if not hasattr(self.app, 'question_icon') else None,
            style="primary.TButton"
        )
        self.about_button.place(x=self.winfo_width() - 50, y=20)
        
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
        
        # Bind configure event to update about button position
        self.bind("<Configure>", self.update_about_button_position)
        
    def go_back(self):
        """Go back to the main view"""
        # Cancel any pending after callbacks in the app
        if hasattr(self.app, 'after_id'):
            self.app.after_cancel(self.app.after_id)
            self.app.after_id = None
            
        # Make main container visible again
        self.app.main_container.pack(fill="both", expand=True)
        
        # Show the main view first
        self.app.show_main_view()
        
        # Then destroy this page
        self.pack_forget()
        self.destroy()
        
    def show_about(self):
        """Show the about page"""
        # Hide the settings page
        self.pack_forget()
        
        # Import the AboutPage class here to avoid circular imports
        from ui.about_page import AboutPage
        
        # Create and show about page
        self.about_page = AboutPage(self.app, self.app)
        
    def update_about_button_position(self, event=None):
        """Update the about button position when the window is resized"""
        # Place the about button 50 pixels from the right edge
        self.about_button.place(x=self.winfo_width() - 50, y=20) 