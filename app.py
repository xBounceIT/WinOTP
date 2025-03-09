import ttkbootstrap as ttk
from tkinter import filedialog, Canvas, Toplevel, Label, Entry, Button, messagebox, PhotoImage
import json
import os
import sys
import uuid
from PIL import Image, ImageTk

from ui.totp_frame import TOTPFrame
from ui.search_bar import SearchBar
from ui.add_token_page import AddTokenPage
from ui.settings_page import SettingsPage
from ui.manual_entry_page import ManualEntryPage
from ui.qr_scan_page import QRScanPage
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
            
            # Remove focus outline when button is clicked
            instance.bind("<FocusIn>", lambda event: instance.focus_set())
            instance.configure(takefocus=0)
        
        # Apply the wrapper
        ttk.Button.__init__ = button_init_wrapper
        
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Create search bar
        self.search_bar = SearchBar(
            self.main_container,
            self.add_token,
            self.search_tokens,
            self.sort_tokens,
            app=self  # Pass the app instance
        )
        
        # Set up initial main view components
        self.setup_main_view()
        
        # Initialize token frames
        self.init_frames()
        
        # Center window on screen
        self.center_window()
        
        # Show welcome message if no tokens
        if not self.frames:
            self.show_welcome_message()
        
        # Start updating frames
        self.update_frames()

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
        # Clear all existing frames
        self.frames = {}
        self.filtered_frames = {}
        
        # Clear existing frame widgets
        if hasattr(self, 'scrollable_frame'):
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
        else:
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
            
            # Create the window anchored at the top-center (north)
            self.canvas_window = self.canvas.create_window(
                (200, 0),  # Initial x position (will be updated in update_scrollable_frame_width)
                window=self.scrollable_frame,
                anchor="n"  # Critical change: north anchor for centering
            )
            
            # Update the canvas window when the canvas is resized
            self.canvas.bind("<Configure>", self.update_scrollable_frame_width)
            
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            
            # Pack canvas and scrollbar
            self.canvas.pack(side="left", fill="both", expand=True)
            self.scrollbar.pack(side="right", fill="y")
            
            # Bind mousewheel for scrolling
            self.bind_all("<MouseWheel>", self.on_mouse_wheel)
        
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

    def update_scrollable_frame_width(self, event):
        """Update the scrollable frame width to match the canvas width"""
        canvas_width = event.width
        
        # Position the window horizontally at the center of the canvas
        self.canvas.coords(self.canvas_window, canvas_width / 2, 0)
        
        # Update the width of the scrollable frame window
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def show_welcome_message(self):
        """Show a welcome message when no tokens are present"""
        from tkinter import CENTER, TOP
        
        # Clear any existing children first
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Create a single frame for the welcome message with a fixed width
        welcome_frame = ttk.Frame(self.scrollable_frame)
        welcome_frame.pack(fill="x", padx=20, pady=20)
        
        # Welcome title - center-aligned label
        title_label = ttk.Label(
            welcome_frame,
            text="Welcome to WinOTP!",
            font="Calibri 24 bold",
            justify=CENTER,
            anchor=CENTER
        )
        title_label.pack(fill="x", pady=(0, 10))
        
        # Welcome message - center-aligned label
        message_label = ttk.Label(
            welcome_frame,
            text="Add your first TOTP token to get started.",
            font="Calibri 14",
            wraplength=400,
            justify=CENTER,
            anchor=CENTER
        )
        message_label.pack(fill="x", pady=(0, 20))
        
        # Add token button
        button_frame = ttk.Frame(welcome_frame)
        button_frame.pack(fill="x")
        
        if hasattr(self, 'plus_icon') and self.plus_icon:
            add_btn = ttk.Button(
                button_frame,
                text="Add Token",
                image=self.plus_icon,
                compound="left",
                command=self.add_token,
                bootstyle="primary"
            )
        else:
            add_btn = ttk.Button(
                button_frame,
                text="Add Token",
                command=self.add_token,
                bootstyle="primary"
            )
        
        # Center the button
        add_btn.pack(anchor=CENTER)

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
        """Switch to add token page instead of showing a popup"""
        # Hide main view components but keep the search bar
        if hasattr(self, 'canvas_frame') and self.canvas_frame.winfo_exists():
            self.canvas_frame.pack_forget()
            
        # Hide search bar functionality (but keep the frame)
        self.search_bar.container.pack_forget()
        
        # Create and show the add token page
        self.add_token_page = AddTokenPage(self.main_container, self)

    def setup_main_view(self):
        """Set up the main view components"""
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
        
        # Bind canvas configure event to update scroll region
        self.canvas.bind("<Configure>", self.configure_scroll_region)

    def show_main_view(self):
        """Show the main view with tokens"""
        # Clear current views except the search bar
        for widget in self.main_container.winfo_children():
            if widget != self.search_bar:  # Keep the search bar
                widget.destroy()
        
        # Make sure search bar is visible and its container is repacked
        self.search_bar.pack(fill="x", padx=20, pady=20)
        self.search_bar.container.pack(fill="x")
        
        # Ensure the search bar is properly configured
        if hasattr(self.search_bar, 'update_buttons_with_icons'):
            self.search_bar.update_buttons_with_icons()
        
        # Set up main view components if they don't exist or were hidden
        if not hasattr(self, 'canvas_frame') or not self.canvas_frame.winfo_exists():
            self.setup_main_view()
        else:
            # Make sure canvas frame is visible
            self.canvas_frame.pack(fill="both", expand=True)
            
            # Make sure canvas and scrollbar are packed correctly
            if hasattr(self, 'canvas') and hasattr(self, 'scrollbar'):
                self.canvas.pack(side="left", fill="both", expand=True)
                self.scrollbar.pack(side="right", fill="y")
        
        # Reinitialize the main UI components
        self.init_frames()
        
        # Show welcome message if no tokens
        if not self.frames:
            self.show_welcome_message()
        
        # Start updating frames
        self.update_frames()

    def add_token_manually(self):
        """Show the manual entry page"""
        # Hide the add token page if it exists
        if hasattr(self, 'add_token_page'):
            self.add_token_page.pack_forget()
            self.add_token_page.destroy()
        
        # Create and show manual entry page
        self.manual_entry_page = ManualEntryPage(self, self)

    def add_token_from_qr(self):
        """Show the QR code scanning page"""
        # Hide the add token page if it exists
        if hasattr(self, 'add_token_page'):
            self.add_token_page.pack_forget()
            self.add_token_page.destroy()
        
        # Create and show QR scan page
        self.qr_scan_page = QRScanPage(self, self)

    def process_qr_image(self, file_path, page):
        """Process a QR code image from the QR scan page"""
        if not file_path:
            return
        
        # Scan the QR code
        result = scan_qr_image(file_path)
        
        if result:
            issuer, secret, name = result
            # Validate the secret
            if Token.validate_base32_secret(secret):
                # Add the token
                success = self.add_new_token(issuer, secret, name)
                # Go back to the main view only if successful
                if success:
                    page.go_back()
            else:
                messagebox.showerror(
                    "Invalid Secret",
                    "The QR code contains an invalid secret key."
                )
                # Update status label
                page.status_label.config(text="Error: Invalid secret key")
        else:
            messagebox.showerror(
                "Invalid QR Code",
                "Could not find a valid TOTP QR code in the image."
            )
            # Update status label
            page.status_label.config(text="Error: Invalid QR code")

    def add_manual_token(self, manual_window, issuer, secret, name):
        """Add a token with manually entered information"""
        # Close the manual window if it exists
        if manual_window:
            manual_window.destroy()
        
        # Check that all fields are filled
        if not issuer or not secret or not name:
            messagebox.showerror(
                "Missing Information",
                "Please fill in all fields."
            )
            return False
        
        # Validate the secret
        if not Token.validate_base32_secret(secret):
            messagebox.showerror(
                "Invalid Secret",
                "The secret key must be a valid Base32 encoded string."
            )
            return False
        
        # Add the token
        self.add_new_token(issuer, secret, name)
        return True

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
                return False
        
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
        
        return True

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
        """Navigate to settings page"""
        # Hide the main container
        self.main_container.pack_forget()
        
        # Create and show settings page
        self.settings_page = SettingsPage(self, self)
        
        # Position settings page
        self.settings_page.pack(fill="both", expand=True)

    def bulk_import_tokens(self):
        """Import multiple tokens from a JSON file"""
        # Hide the add token page if it exists
        if hasattr(self, 'add_token_page'):
            self.add_token_page.pack_forget()
            
        # Open file dialog to select an image
        file_path = filedialog.askopenfilename(
            title="Select Tokens JSON File",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            # If cancelled, show the add token page again
            self.add_token()
            return
        
        try:
            # Read the import file
            with open(file_path, 'r') as file:
                import_data = json.load(file)
            
            # Validate the import data
            if not isinstance(import_data, dict):
                messagebox.showerror(
                    "Invalid Format",
                    "The import file should contain a JSON object with token IDs as keys."
                )
                self.add_token()
                return
            
            # Load existing tokens
            tokens = read_json(self.tokens_path)
            
            # Count successful imports
            import_count = 0
            
            # Process each token
            for token_id, token_data in import_data.items():
                # Validate the token data
                if not isinstance(token_data, dict):
                    continue
                
                issuer = token_data.get("issuer", "").strip()
                secret = token_data.get("secret", "").strip().upper()
                name = token_data.get("name", "").strip()
                
                # Skip invalid tokens
                if not issuer or not secret:
                    continue
                
                # Validate the secret
                if not Token.validate_base32_secret(secret):
                    continue
                
                # Check for duplicate secrets
                duplicate = False
                for existing_token in tokens.values():
                    if existing_token.get("secret") == secret:
                        duplicate = True
                        break
                
                if duplicate:
                    continue
                
                # Generate a new unique ID for the token
                new_id = f"token_{uuid.uuid4().hex[:8]}"
                
                # Add the token
                tokens[new_id] = {
                    "issuer": issuer,
                    "secret": secret,
                    "name": name
                }
                
                import_count += 1
            
            # Save tokens
            if import_count > 0:
                write_json(self.tokens_path, tokens)
                
                # Show success message
                messagebox.showinfo(
                    "Import Successful",
                    f"Successfully imported {import_count} tokens."
                )
                
                # Refresh the UI
                self.show_main_view()
            else:
                messagebox.showwarning(
                    "No Tokens Imported",
                    "No valid tokens were found in the import file."
                )
                self.add_token()
                
        except Exception as e:
            messagebox.showerror(
                "Import Error",
                f"An error occurred while importing tokens: {str(e)}"
            )
            self.add_token() 