import ttkbootstrap as ttk
from tkinter import filedialog, Canvas, Toplevel, Label, Entry, Button, messagebox, PhotoImage
import json
import os
import sys
import uuid
from PIL import Image, ImageTk

from ui.totp_frame import TOTPFrame
from ui.search_bar import SearchBar
from utils.file_io import read_json, write_json
from utils.qr_scanner import scan_qr_image
from models.token import Token

class WinOTP(ttk.Window):
    def __init__(self, tokens_path):
        # Set dark mode theme.
        super().__init__(themename="darkly")
        
        self.title("WinOTP")
        self.minsize(500, 400)
        self.tokens_path = tokens_path
        
        # Initialize variables
        self.frames = {}  # Store token frames by ID
        self.filtered_frames = {}  # Store filtered token frames
        self.sort_ascending = True  # Default sort order
        
        # Load icons
        self.load_icons()
        
        # Override button initialization to add hand cursor
        original_button_init = ttk.Button.__init__
        
        def button_init_wrapper(instance, master=None, **kw):
            # Add hand cursor for all buttons
            original_button_init(instance, master, **kw)
            instance.configure(cursor="hand2")
        
        # Apply the wrapper
        ttk.Button.__init__ = button_init_wrapper
        
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Create search bar (moved to top)
        self.search_bar = SearchBar(
            self.main_container,
            self.add_token,
            self.search_tokens,
            self.sort_tokens,
            app=self  # Pass the app instance
        )
        
        # Create canvas with scrollbar for tokens
        self.canvas_frame = ttk.Frame(self.main_container)
        self.canvas_frame.pack(fill="both", expand=True)
        
        self.canvas = Canvas(self.canvas_frame, bg="#212529", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel for scrolling
        self.bind_all("<MouseWheel>", self.on_mouse_wheel)
        
        # Initialize token frames
        self.init_frames()
        
        # Center window on screen
        self.center_window()
        
        # Bind canvas configure event to update scroll region
        self.canvas.bind("<Configure>", self.configure_scroll_region)
        
        # Show welcome message if no tokens
        if not self.frames:
            self.show_welcome_message()

    def load_icons(self):
        """Load all icons used in the application"""
        try:
            # Define icon paths and sizes
            icon_data = [
                ("copy_icon", "icons/copy.png", 20),
                ("copy_confirm_icon", "icons/copy_confirm.png", 20),
                ("delete_icon", "icons/delete.png", 20),
                ("plus_icon", "icons/plus.png", 20),
                ("search_icon", "icons/search.png", 20),
                ("settings_icon", "icons/settings.png", 20),
                ("sort_asc_icon", "icons/sort_asc.png", 20),
                ("sort_desc_icon", "icons/sort_desc.png", 20),
                ("back_icon", "icons/back_arrow.png", 20),
                ("empty_icon", "icons/drawer-empty.png", 20),
            ]
            
            # Create icons directory if it doesn't exist
            if not os.path.exists("icons"):
                os.makedirs("icons")
                print("Created icons directory")
            
            # Initialize all icon attributes to None first
            for attr_name, _, _ in icon_data:
                setattr(self, attr_name, None)
                
            # Try to load each icon, but continue if some are missing
            for attr_name, path, size in icon_data:
                try:
                    icon = self.load_icon(path, size)
                    if icon:
                        setattr(self, attr_name, icon)
                        print(f"Successfully loaded icon: {path}")
                    else:
                        print(f"Icon not found: {path}")
                except Exception as e:
                    print(f"Failed to load icon {path}: {e}")
                    # Icon will remain None
                    
        except Exception as e:
            print(f"Error loading icons: {e}")
            # Continue without icons

    def load_icon(self, path, size):
        """Load an icon from file and resize it"""
        try:
            if os.path.exists(path):
                img = Image.open(path)
                img = img.resize((size, size), Image.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                return photo_img
            else:
                print(f"Icon file not found: {path}")
                return None
        except Exception as e:
            print(f"Error loading icon {path}: {e}")
            return None

    def center_window(self):
        """Center the window on the screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def configure_scroll_region(self, event):
        """Update the scroll region when the canvas is resized"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # Also update scrollbar visibility
        self.update_scrollbar_visibility()

    def init_frames(self):
        """Initialize token frames from the tokens file"""
        # Clear existing frames
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Load tokens from file
        tokens = read_json(self.tokens_path)
        
        # Create a frame for each token
        for token_id, token_data in tokens.items():
            # Create a callback that captures the current token_id
            delete_callback = lambda tid=token_id: self.delete_token(tid)
            
            # Create the frame
            frame = TOTPFrame(
                self.scrollable_frame,
                token_data.get("issuer", "Unknown"),
                token_data.get("secret", ""),
                token_data.get("name", ""),
                delete_callback
            )
            
            # Store the frame
            self.frames[token_id] = frame
        
        # Apply current sorting
        self._apply_current_sorting()
        
        # Update scrollbar visibility
        self.update_scrollbar_visibility()

    def show_welcome_message(self):
        """Show a welcome message when no tokens are present"""
        # Use a container frame for centering
        container_frame = ttk.Frame(self.scrollable_frame)
        container_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create a welcome frame inside the container
        welcome_frame = ttk.Frame(container_frame, width=400)
        welcome_frame.pack(fill="none", expand=True, anchor="center")
        
        # Welcome title
        title_label = ttk.Label(
            welcome_frame, 
            text="Welcome to WinOTP!", 
            font="Calibri 24 bold"
        )
        title_label.pack(pady=(0, 10), anchor="center")
        
        # Welcome message
        message_label = ttk.Label(
            welcome_frame,
            text="Add your first TOTP token to get started.",
            font="Calibri 14",
            wraplength=400
        )
        message_label.pack(pady=(0, 20), anchor="center")
        
        # Add token button
        if hasattr(self, 'plus_icon') and self.plus_icon:
            add_btn = ttk.Button(
                welcome_frame,
                text="Add Token",
                image=self.plus_icon,
                compound="left",
                command=self.add_token,
                bootstyle="primary"
            )
        else:
            add_btn = ttk.Button(
                welcome_frame,
                text="Add Token",
                command=self.add_token,
                bootstyle="primary"
            )
        add_btn.pack(pady=10, anchor="center")

    def update_frames(self):
        """Update all token frames"""
        for frame in self.frames.values():
            frame.update()
        
        # Schedule the next update
        self.after(1000, self.update_frames)

    def sort_tokens(self):
        """Toggle sort order and apply sorting"""
        self.sort_ascending = not self.sort_ascending
        self._apply_current_sorting()
        
        # Update sort button in search bar
        self.search_bar.update_sort_button(self.sort_ascending)

    def _apply_current_sorting(self):
        """Apply the current sorting order to the frames"""
        # Get the current frames to sort (either all or filtered)
        current_frames = self.filtered_frames if self.filtered_frames else self.frames
        
        # Sort frames by issuer
        sorted_items = sorted(
            current_frames.items(),
            key=lambda x: x[1].issuer.lower(),
            reverse=not self.sort_ascending
        )
        
        # Unpack all frames
        for frame in current_frames.values():
            frame.pack_forget()
        
        # Pack frames in sorted order
        for token_id, frame in sorted_items:
            frame.pack(fill="x", padx=10, pady=5)

    def search_tokens(self, query):
        """Filter tokens based on search query"""
        query = query.lower()
        
        # Clear filtered frames
        self.filtered_frames = {}
        
        # Hide all frames
        for frame in self.frames.values():
            frame.pack_forget()
        
        # Filter frames
        for token_id, frame in self.frames.items():
            if query in frame.issuer.lower() or query in frame.full_name.lower():
                self.filtered_frames[token_id] = frame
        
        # Apply sorting to filtered frames
        self._apply_current_sorting()

    def add_token(self):
        """Show dialog to add a new token"""
        # Create a new toplevel window
        add_window = Toplevel(self)
        add_window.title("Add Token")
        add_window.geometry("400x300")
        add_window.resizable(False, False)
        add_window.transient(self)  # Make it a transient window
        add_window.grab_set()  # Make it modal
        
        # Center the window
        add_window.update_idletasks()
        width = add_window.winfo_width()
        height = add_window.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        add_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add title
        title_label = Label(add_window, text="Add New Token", font="Calibri 16 bold")
        title_label.pack(pady=20)
        
        # Add buttons for different methods
        button_frame = ttk.Frame(add_window)
        button_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Manual entry button
        manual_btn = ttk.Button(
            button_frame,
            text="Manual Entry",
            command=lambda: [add_window.destroy(), self.add_token_manually()],
            width=20
        )
        manual_btn.pack(pady=10)
        
        # QR code button
        qr_btn = ttk.Button(
            button_frame,
            text="Scan QR Code",
            command=lambda: [add_window.destroy(), self.add_token_from_qr()],
            width=20
        )
        qr_btn.pack(pady=10)
        
        # Import from file button
        import_btn = ttk.Button(
            button_frame,
            text="Import from File",
            command=lambda: [add_window.destroy(), self.bulk_import_tokens()],
            width=20
        )
        import_btn.pack(pady=10)

    def show_main_view(self):
        """Show the main view with tokens"""
        # Clear welcome message if present
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Initialize frames
        self.init_frames()
        
        # Start updating frames
        self.update_frames()

    def add_token_manually(self):
        """Show dialog to add a token manually"""
        # Create a new toplevel window
        manual_window = Toplevel(self)
        manual_window.title("Add Token Manually")
        manual_window.geometry("400x300")
        manual_window.resizable(False, False)
        manual_window.transient(self)  # Make it a transient window
        manual_window.grab_set()  # Make it modal
        
        # Center the window
        manual_window.update_idletasks()
        width = manual_window.winfo_width()
        height = manual_window.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        manual_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add title
        title_label = Label(manual_window, text="Add Token Manually", font="Calibri 16 bold")
        title_label.pack(pady=10)
        
        # Create form
        form_frame = ttk.Frame(manual_window)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Issuer field
        issuer_label = Label(form_frame, text="Issuer (e.g. Google, GitHub):")
        issuer_label.pack(anchor="w")
        issuer_entry = Entry(form_frame, width=40)
        issuer_entry.pack(fill="x", pady=(0, 10))
        
        # Account name field
        name_label = Label(form_frame, text="Account Name (e.g. username, email):")
        name_label.pack(anchor="w")
        name_entry = Entry(form_frame, width=40)
        name_entry.pack(fill="x", pady=(0, 10))
        
        # Secret field
        secret_label = Label(form_frame, text="Secret Key (Base32 encoded):")
        secret_label.pack(anchor="w")
        secret_entry = Entry(form_frame, width=40)
        secret_entry.pack(fill="x", pady=(0, 10))
        
        # Add button with a lambda that captures the current entries
        add_btn = ttk.Button(
            form_frame,
            text="Add Token",
            command=lambda: self.add_manual_token(
                manual_window,
                issuer_entry.get(),
                secret_entry.get(),
                name_entry.get()
            )
        )
        add_btn.pack(pady=10)

    def add_token_from_qr(self):
        """Add a token by scanning a QR code image"""
        # Open file dialog to select an image
        file_path = filedialog.askopenfilename(
            title="Select QR Code Image",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        # Scan the QR code
        result = scan_qr_image(file_path)
        
        if result:
            issuer, secret, name = result
            # Validate the secret
            if Token.validate_base32_secret(secret):
                # Add the token
                self.add_new_token(issuer, secret, name)
            else:
                messagebox.showerror(
                    "Invalid Secret",
                    "The QR code contains an invalid secret key."
                )
        else:
            messagebox.showerror(
                "Invalid QR Code",
                "Could not find a valid TOTP QR code in the image."
            )

    def add_manual_token(self, manual_window, issuer, secret, name):
        """Add a token from manual entry form"""
        issuer = issuer.strip()
        secret = secret.strip().upper().replace(" ", "")
        name = name.strip()
        
        # Validate inputs
        if not issuer:
            messagebox.showerror("Error", "Issuer name is required")
            return
        
        if not secret:
            messagebox.showerror("Error", "Secret key is required")
            return
        
        # Validate the secret
        if not Token.validate_base32_secret(secret):
            messagebox.showerror(
                "Invalid Secret",
                "The secret key is not a valid Base32 encoded string.\n"
                "It should only contain letters A-Z and numbers 2-7."
            )
            return
        
        # Close the window
        manual_window.destroy()
        
        # Add the token
        self.add_new_token(issuer, secret, name)

    def add_new_token(self, issuer, secret, name):
        """Add a new token to the database and UI"""
        # Generate a unique ID for the token
        token_id = f"token_{uuid.uuid4().hex[:8]}"
        
        # Load existing tokens
        tokens = read_json(self.tokens_path)
        
        # Check for duplicate secrets
        for existing_token in tokens.values():
            if existing_token.get("secret") == secret:
                messagebox.showerror(
                    "Duplicate Token",
                    "A token with this secret already exists."
                )
                return
        
        # Add the new token
        tokens[token_id] = {
            "issuer": issuer,
            "secret": secret,
            "name": name
        }
        
        # Save tokens
        write_json(self.tokens_path, tokens)
        
        # Create a callback that captures the current token_id
        delete_callback = lambda: self.delete_token(token_id)
        
        # Create the frame
        frame = TOTPFrame(
            self.scrollable_frame,
            issuer,
            secret,
            name,
            delete_callback
        )
        
        # Store the frame
        self.frames[token_id] = frame
        
        # Apply current sorting
        self._apply_current_sorting()
        
        # Start updating frames if this is the first token
        if len(self.frames) == 1:
            self.show_main_view()
        
        # Update scrollbar visibility
        self.update_scrollbar_visibility()

    def delete_token(self, token_id):
        """Delete a token from the database and UI"""
        # Get the frame from our data structure
        frame = self.frames.get(token_id)
        if not frame:
            return
        
        # Remove the frame from UI
        frame.destroy()
        
        # Remove from our data structures
        del self.frames[token_id]
        if token_id in self.filtered_frames:
            del self.filtered_frames[token_id]
        
        # Load tokens from file
        tokens = read_json(self.tokens_path)
        
        # Remove the token
        if token_id in tokens:
            del tokens[token_id]
        
        # Save tokens
        write_json(self.tokens_path, tokens)
        
        # Show welcome message if no tokens left
        if not self.frames:
            self.show_welcome_message()
        
        # Update scrollbar visibility
        self.update_scrollbar_visibility()

    def on_mouse_wheel(self, event):
        """Handle different mouse wheel event formats across platforms"""
        # Handle different mouse wheel event formats across platforms
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def update_scrollbar_visibility(self):
        """Show or hide scrollbar based on content height"""
        # Get the height of all content
        content_height = self.scrollable_frame.winfo_reqheight()
        
        # Get the height of the canvas
        canvas_height = self.canvas.winfo_height()
        
        # Show or hide scrollbar
        if content_height > canvas_height:
            self.scrollbar.pack(side="right", fill="y")
        else:
            self.scrollbar.pack_forget()

    def show_settings(self):
        """Show settings dialog"""
        # Create a new toplevel window
        settings_window = Toplevel(self)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        settings_window.transient(self)  # Make it a transient window
        settings_window.grab_set()  # Make it modal
        
        # Center the window
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        settings_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add title
        title_label = Label(settings_window, text="Settings", font="Calibri 16 bold")
        title_label.pack(pady=10)
        
        # Create settings frame
        settings_frame = ttk.Frame(settings_window)
        settings_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Add import/export buttons
        import_btn = ttk.Button(
            settings_frame,
            text="Import Tokens",
            command=lambda: [settings_window.destroy(), self.bulk_import_tokens()]
        )
        import_btn.pack(fill="x", pady=5)
        
        # Add about section
        about_frame = ttk.LabelFrame(settings_frame, text="About")
        about_frame.pack(fill="both", expand=True, pady=10)
        
        about_text = Label(
            about_frame,
            text="WinOTP - A Windows TOTP Authenticator\n"
                 "Version 1.0.0\n\n"
                 "Created by Your Name\n"
                 "Icons by Feather Icons",
            justify="left"
        )
        about_text.pack(padx=10, pady=10, anchor="w")

    def bulk_import_tokens(self):
        """Import multiple tokens from a JSON file"""
        filename = filedialog.askopenfilename(
            title="Select JSON file with TOTP tokens",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            # Read the import file
            with open(filename, 'r') as file:
                import_data = json.load(file)
            
            if not import_data:
                messagebox.showerror("Error", "The selected file doesn't contain any tokens.")
                return
            
            # Get current tokens
            current_tokens = read_json(self.tokens_path)
            
            # Track import statistics
            imported_count = 0
            duplicate_count = 0
            
            # Process each token in the import file
            for token_id, data in import_data.items():
                # Verify required fields
                if not all(key in data for key in ["issuer", "name", "secret"]):
                    continue
                
                # Check for duplicate secrets
                is_duplicate = False
                for existing_token in current_tokens.values():
                    if existing_token.get("secret") == data["secret"]:
                        duplicate_count += 1
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    continue
                
                # Create a new unique token ID
                new_token_id = f"token_{uuid.uuid4().hex[:8]}"
                
                # Add to current tokens
                current_tokens[new_token_id] = {
                    "issuer": data["issuer"],
                    "name": data["name"],
                    "secret": data["secret"]
                }
                imported_count += 1
            
            # Save updated tokens
            write_json(self.tokens_path, current_tokens)
            
            # Show success message
            messagebox.showinfo(
                "Import Complete", 
                f"Successfully imported {imported_count} tokens.\n"
                f"Skipped {duplicate_count} duplicate tokens."
            )
            
            # Refresh the main view
            self.show_main_view()
            
            # Reinitialize frames with the new tokens
            self.frames = {}
            self.filtered_frames = {}
            self.init_frames()
            
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON file format.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import tokens: {str(e)}") 