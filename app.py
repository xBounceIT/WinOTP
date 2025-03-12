import ttkbootstrap as ttk
from tkinter import filedialog, Canvas, Toplevel, Label, Entry, Button, messagebox, PhotoImage, TclError
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
        # Initialize with dark theme
        super().__init__(themename="darkly")
        
        # Withdraw the window temporarily while setting up
        self.withdraw()
        
        self.title("WinOTP")
        # Set fixed window dimensions (width x height)
        self.geometry("500x600")
        # Prevent the window from being resized
        self.resizable(False, False)
        self.tokens_path = tokens_path
        
        # Initialize variables
        self.frames = {}  # Store token frames by ID
        self.filtered_frames = {}  # Store filtered token frames
        self.sort_ascending = True  # Default sort order
        self.after_ids = set()  # Track all after callbacks
        
        # Load icons first
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
        
        # Center window on screen
        self.center_window()
        
        # Load tokens from file before initializing frames
        tokens = read_json(self.tokens_path)
        print(f"Loaded {len(tokens)} tokens from {self.tokens_path}")
        
        # Determine if we need to show tokens or welcome message
        if tokens:
            # Initialize token frames if we have tokens
            self.init_frames()
            print(f"Initialized {len(self.frames)} token frames")
        else:
            # Create empty frames dict
            self.frames = {}
            self.filtered_frames = {}
            print("No tokens found, will show welcome message")
            
            # Hide the canvas frame since we don't need it for the welcome message
            if hasattr(self, 'canvas_frame'):
                self.canvas_frame.pack_forget()
                
            # Show welcome message
            self.show_welcome_message()
            
            # Special hint for verification that welcome message should be visible
            print("*** WELCOME MESSAGE SHOULD NOW BE VISIBLE ***")
            
        # Start updating frames
        self.update_frames()
        
        # Finally, show the window
        self.deiconify()
        
        # Set the app icon for both title bar and taskbar
        if hasattr(self, 'app_icon') and self.app_icon:
            self.iconphoto(True, self.app_icon)

    def load_icons(self):
        """Load all icons used in the application"""
        try:
            # Define icon paths and sizes
            icon_data = [
                ("app_icon", "icons/app.png", 32),  # App icon with larger size for better quality
                ("copy_icon", "icons/copy.png", 20),
                ("copy_confirm_icon", "icons/copy_confirm.png", 20),
                ("delete_icon", "icons/delete.png", 20),
                ("plus_icon", "icons/plus.png", 20),
                ("search_icon", "icons/search.png", 20),
                ("settings_icon", "icons/settings.png", 20),
                ("sort_asc_icon", "icons/sort_asc.png", 20),
                ("sort_desc_icon", "icons/sort_desc.png", 20),
                ("back_icon", "icons/back_arrow.png", 16),
                ("empty_icon", "icons/drawer-empty.png", 20),
                ("question_icon", "icons/question.png", 16),
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
        # Use fixed dimensions (500x600)
        width = 500
        height = 600
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def configure_scroll_region(self, event=None):
        """Update the scroll region when the canvas is resized"""
        if not hasattr(self, 'canvas') or not self.canvas.winfo_exists():
            return
            
        # Get canvas width, either from event or current width
        canvas_width = event.width if event else self.canvas.winfo_width()
        print(f"Configuring scroll region, width: {canvas_width}")
        
        # Update the scrollable frame width
        if hasattr(self, 'scrollable_frame') and self.scrollable_frame.winfo_exists():
            self.scrollable_frame.configure(width=canvas_width - 20)  # Account for padding
            
        # Update the scroll region to encompass all content
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Update scrollbar visibility
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
                
        # Load tokens from file
        tokens = read_json(self.tokens_path)
        print(f"init_frames: Loaded {len(tokens)} tokens")
        
        # If no tokens, we'll still update scroll regions and visibility
        if not tokens:
            # Update scrollbar visibility
            self.update_scrollbar_visibility()
            return
        
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
        
        # Force the scrollable frame to use the full width of the canvas
        # This is crucial for ensuring child frames fill the entire width
        self.scrollable_frame.configure(width=canvas_width - 20)  # Subtract padding
        
        # Update all existing token frames to match the new width
        if hasattr(self, 'frames'):
            current_frames = self.filtered_frames if self.filtered_frames else self.frames
            for frame in current_frames.values():
                frame.configure(width=canvas_width - 60)  # Account for padding

    def show_welcome_message(self):
        """Show a welcome message when no tokens are present"""
        from tkinter import CENTER, TOP
        
        print("Attempting to show welcome message")
        
        # Safely check if canvas frame exists and is mapped
        try:
            if hasattr(self, 'canvas_frame') and self.canvas_frame.winfo_exists():
                print(f"Canvas frame exists and visibility: {self.canvas_frame.winfo_ismapped()}")
            else:
                print("Canvas frame doesn't exist or has been destroyed")
        except (AttributeError, TclError) as e:
            print(f"Error checking canvas frame: {e}")
            # If canvas_frame is causing errors, remove the reference
            if hasattr(self, 'canvas_frame'):
                delattr(self, 'canvas_frame')
        
        # APPROACH: Create a completely new welcome frame in the main container
        # This bypasses potential issues with the canvas and scrollable frame
        
        # First, clear any previous welcome message
        for widget in self.main_container.winfo_children():
            if widget != self.search_bar and widget != self.canvas_frame:
                if hasattr(widget, 'welcome_tag') and widget.welcome_tag:
                    print("Removing previous welcome message")
                    widget.destroy()
        
        # Create a prominent welcome frame directly in the main container, below search bar
        welcome_container = ttk.Frame(self.main_container)
        welcome_container.welcome_tag = True  # Mark this as a welcome message for later identification
        welcome_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create an inner frame with transparent background
        welcome_frame = ttk.Frame(welcome_container, width=500, height=300)
        welcome_frame.pack(pady=50)
        welcome_frame.pack_propagate(False)  # Keep fixed size
        
        # Welcome title with default styling
        title_label = ttk.Label(
            welcome_frame,
            text="Welcome to WinOTP!",
            font="Calibri 24 bold",
            justify=CENTER,
            anchor=CENTER
        )
        title_label.pack(fill="x", pady=(30, 20))
        
        # Welcome message
        message_label = ttk.Label(
            welcome_frame,
            text="Add your first TOTP token to get started.",
            font="Calibri 14",
            wraplength=460,
            justify=CENTER,
            anchor=CENTER
        )
        message_label.pack(fill="x", pady=(0, 30))
        
        # Add token button - using standard primary style to match other buttons
        if hasattr(self, 'plus_icon') and self.plus_icon:
            add_btn = ttk.Button(
                welcome_frame,
                text="Add Token",
                image=self.plus_icon,
                compound="left",
                command=self.add_token,
                bootstyle="primary",
                width=15
            )
        else:
            add_btn = ttk.Button(
                welcome_frame,
                text="Add Token",
                command=self.add_token,
                bootstyle="primary",
                width=15
            )
        
        # Center the button
        add_btn.pack(pady=(0, 30))
        
        print("Welcome message created as direct child of main container")
        
        # Force update to ensure visibility
        welcome_container.update()
        welcome_frame.update()

    def update_frames(self):
        """Update all token frames efficiently"""
        try:
            # Get the current frames to update (either filtered or all)
            current_frames = self.filtered_frames if self.filtered_frames else self.frames
            
            # Update each frame
            for frame in current_frames.values():
                frame.update()
            
            # Schedule the next update with a longer interval
            # We'll update every 100ms for smooth progress bar updates
            after_id = self.after(100, self.update_frames)
            self.after_ids.add(after_id)
            
        except Exception as e:
            print(f"Error updating frames: {e}")
            # Ensure we keep updating even if there's an error
            after_id = self.after(100, self.update_frames)
            self.after_ids.add(after_id)

    def cleanup_after_callbacks(self):
        """Clean up all pending after callbacks"""
        for after_id in self.after_ids:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self.after_ids.clear()

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
            # Configure the frame to use the full width available
            current_width = self.scrollable_frame.winfo_width()
            if current_width > 1:  # Only set if we have a valid width
                frame.configure(width=current_width - 20)  # Account for padding
            # Pack with fill="x" and expand=True to use full width
            frame.pack(fill="x", expand=True, padx=10, pady=10)

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
        print("Adding token - transitioning to add token page")
        
        # Clean up any pending callbacks
        self.cleanup_after_callbacks()
        
        # Clear ALL content from the main container except the search bar
        for widget in self.main_container.winfo_children():
            if widget != self.search_bar:
                print(f"Removing widget: {widget}")
                widget.pack_forget()  # First unpack it
                widget.destroy()      # Then destroy it
        
        # Hide canvas frame if it exists
        if hasattr(self, 'canvas_frame') and self.canvas_frame.winfo_exists():
            self.canvas_frame.pack_forget()
            self.canvas_frame.destroy()  # Also destroy the canvas frame
        
        # Also check for any remaining welcome containers and remove them
        for widget in self.main_container.winfo_children():
            if widget != self.search_bar:
                if hasattr(widget, 'welcome_tag') and widget.welcome_tag:
                    print(f"Removing welcome container: {widget}")
                    widget.pack_forget()
                    widget.destroy()
        
        # Hide search bar functionality (but keep the frame)
        self.search_bar.container.pack_forget()
        
        # Clear frame references
        self.frames = {}
        self.filtered_frames = {}
        
        # Explicitly update the UI before adding the new page
        self.main_container.update()
        
        # Create and show the add token page
        self.add_token_page = AddTokenPage(self.main_container, self)
        
        # Make sure it fills the available space
        self.add_token_page.pack(fill="both", expand=True)

    def setup_main_view(self):
        """Set up the main view components"""
        # Create canvas with scrollbar for tokens
        self.canvas_frame = ttk.Frame(self.main_container)
        self.canvas_frame.pack(fill="both", expand=True)
        
        # Create canvas with proper background and no highlight
        self.canvas = Canvas(
            self.canvas_frame,
            bg="#212529",
            highlightthickness=0
        )
        
        # Create scrollbar with primary theme color for visibility
        self.scrollbar = ttk.Scrollbar(
            self.canvas_frame,
            orient="vertical",
            command=self.canvas.yview,
            bootstyle="primary"  # Remove rounded corners
        )
        
        # Create the frame that will hold the tokens
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure the canvas scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y", padx=(2, 4))  # Add more padding
        
        # Create the window in the canvas that will hold the frame
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw",
            width=self.canvas.winfo_width() - 4  # Account for scrollbar width
        )
        
        # Bind frame configuration to update scroll region
        def _on_frame_configure(event):
            # Update the scroll region to encompass the inner frame
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Update the frame width to match canvas
            self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width())
        
        self.scrollable_frame.bind("<Configure>", _on_frame_configure)
        
        # Bind canvas resize to update frame width
        def _on_canvas_configure(event):
            # Update the frame width when canvas changes size
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        
        self.canvas.bind("<Configure>", _on_canvas_configure)
        
        # Bind mousewheel for scrolling
        def _on_mousewheel(event):
            # Windows standard: Negative delta = scroll down, Positive delta = scroll up
            if event.delta < 0:
                self.canvas.yview_scroll(1, "units")  # Scroll down
            else:
                self.canvas.yview_scroll(-1, "units")  # Scroll up
        
        # Bind mousewheel to both canvas and scrollable frame
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def show_main_view(self):
        """Show the main view with tokens"""
        print("Showing main view")
        
        # Clean up any pending callbacks first
        self.cleanup_after_callbacks()
        
        # Clear current views except the search bar
        try:
            for widget in self.main_container.winfo_children():
                if widget != self.search_bar:  # Keep the search bar
                    print(f"Removing widget from main view: {widget}")
                    try:
                        widget.pack_forget()  # First unpack
                        widget.destroy()      # Then destroy
                    except Exception as e:
                        print(f"Error removing widget: {e}")
        except Exception as e:
            print(f"Error cleaning main container: {e}")
        
        # Make sure search bar is visible and its container is repacked
        try:
            self.search_bar.pack(fill="x", padx=20, pady=20)
            self.search_bar.container.pack(fill="x")
        except Exception as e:
            print(f"Error showing search bar: {e}")
        
        # Explicitly update the UI
        self.main_container.update()
        
        # Ensure the search bar is properly configured
        if hasattr(self.search_bar, 'update_buttons_with_icons'):
            self.search_bar.update_buttons_with_icons()
        
        # Load tokens to check if we have any
        tokens = read_json(self.tokens_path)
        print(f"show_main_view: Found {len(tokens)} tokens")
        
        # Reset canvas frame reference if it doesn't exist
        if hasattr(self, 'canvas_frame') and not hasattr(self.canvas_frame, 'winfo_exists'):
            delattr(self, 'canvas_frame')
            
        if tokens:
            # Set up main view components for tokens display
            if not hasattr(self, 'canvas_frame') or not self.canvas_frame.winfo_exists():
                print("Setting up new main view for tokens")
                self.setup_main_view()
            else:
                # Make sure canvas frame is visible
                try:
                    self.canvas_frame.pack(fill="both", expand=True)
                    
                    # Make sure canvas and scrollbar are packed correctly
                    if hasattr(self, 'canvas') and hasattr(self, 'scrollbar'):
                        self.canvas.pack(side="left", fill="both", expand=True)
                        self.scrollbar.pack(side="right", fill="y")
                except Exception as e:
                    print(f"Error showing canvas frame: {e}")
                    # If failed, recreate the main view
                    self.setup_main_view()
            
            # Reinitialize the token frames
            self.init_frames()
            
            # Start updating frames
            self.update_frames()
        else:
            # No tokens, show welcome message directly
            print("No tokens found in show_main_view, showing welcome message")
            self.frames = {}
            self.filtered_frames = {}
            
            # Make sure we have no leftover canvas frame
            if hasattr(self, 'canvas_frame') and self.canvas_frame.winfo_exists():
                try:
                    self.canvas_frame.pack_forget()
                except Exception as e:
                    print(f"Error hiding canvas frame: {e}")
            
            # Show the welcome message
            self.show_welcome_message()

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
                # If successful, show confirmation and go to main view
                if success:
                    messagebox.showinfo(
                        "Token Added",
                        f"Token for {issuer} ({name}) was successfully added."
                    )
                    # Destroy the QR scan page
                    page.pack_forget()
                    page.destroy()
                    # Show the main view directly
                    self.show_main_view()
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
        """Add a token manually with the given details"""
        # If we came from the manual entry page, destroy it and go to main view first
        if hasattr(self, 'manual_entry_page'):
            self.manual_entry_page.pack_forget()
            self.show_main_view()
            
        # Validate the secret
        if not Token.validate_base32_secret(secret):
            messagebox.showerror(
                "Invalid Secret",
                "The secret key must be a valid Base32 encoded string."
            )
            return False
        
        # Add the token
        success = self.add_new_token(issuer, secret, name)
        
        if success:
            # Show confirmation message
            messagebox.showinfo(
                "Token Added",
                f"Token for {issuer} ({name}) was successfully added."
            )
            
            # Update the UI - let the canvas update itself first
            self.update_frames()
            self.update()  # Process any pending events
            self.configure_scroll_region()  # Now update scroll region without event
            
        return success

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

    def update_scrollbar_visibility(self):
        """Show or hide scrollbar based on content height"""
        if not hasattr(self, 'scrollable_frame') or not hasattr(self, 'canvas'):
            return
            
        # Get the height of all content
        content_height = self.scrollable_frame.winfo_reqheight()
        
        # Get the height of the canvas
        canvas_height = self.canvas.winfo_height()
        
        # Show or hide scrollbar and enable/disable scrolling
        if content_height > canvas_height:
            self.scrollbar.pack(side="right", fill="y", padx=(2, 4))  # Add more padding
            self.canvas.configure(yscrollcommand=self.scrollbar.set)
            # Update the canvas window width to account for scrollbar
            self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width() - 4)
        else:
            self.scrollbar.pack_forget()
            self.canvas.configure(yscrollcommand=None)
            # Restore full width when scrollbar is hidden
            self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width())

    def show_settings(self):
        """Navigate to settings page"""
        # Hide the main container
        self.main_container.pack_forget()
        
        # Create and show settings page
        self.settings_page = SettingsPage(self, self)
        
        # Position settings page
        self.settings_page.pack(fill="both", expand=True)

    def show_about(self):
        """Navigate to about page"""
        # Import the AboutPage class here to avoid circular imports
        from ui.about_page import AboutPage
        
        # Create and show about page
        self.about_page = AboutPage(self, self)
        
        # Position about page
        self.about_page.pack(fill="both", expand=True)

    def bulk_import_tokens(self):
        """Import multiple tokens from a JSON file"""
        # Open file dialog to select an image
        file_path = filedialog.askopenfilename(
            title="Select Tokens JSON File",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            # If cancelled, just return (stay on current page)
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
                
        except Exception as e:
            messagebox.showerror(
                "Import Error",
                f"An error occurred while importing tokens: {str(e)}"
            ) 