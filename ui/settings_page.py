import ttkbootstrap as ttk
from tkinter import Frame, Label, filedialog
from utils.file_io import read_json, write_json

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
        
        # Add export button
        self.export_btn = ttk.Button(
            self.settings_frame,
            text="Export Tokens",
            command=self.export_tokens,
            width=20
        )
        self.export_btn.pack(fill="x", pady=10)
        
        # Bind configure event to update about button position
        self.bind("<Configure>", self.update_about_button_position)
        
    def go_back(self):
        """Go back to the main view"""
        # Clean up any pending callbacks in the app
        self.app.cleanup_after_callbacks()
        
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
        
    def export_tokens(self):
        """Export tokens to a custom location"""
        # Open file dialog to select save location
        file_path = filedialog.asksaveasfilename(
            title="Export Tokens",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Read current tokens
                tokens = read_json(self.app.tokens_path)
                
                # Write tokens to the selected location
                write_json(file_path, tokens)
                
                # Show success message
                from tkinter import messagebox
                messagebox.showinfo(
                    "Export Successful",
                    f"Tokens have been exported to {file_path}"
                )
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror(
                    "Export Error",
                    f"An error occurred while exporting tokens: {str(e)}"
                ) 