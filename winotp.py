import ttkbootstrap as ttk
from tkinter import filedialog, Canvas, Toplevel, Label, Entry, Button, messagebox, PhotoImage
import json
import pyotp
from datetime import datetime
from PIL import Image, ImageTk
from pyzbar.pyzbar import decode
import re
from urllib.parse import unquote
import os
import tkinter.font as tkFont  # Add this import at the top
import sys  # Added import for checking command line arguments

class TOTPFrame(ttk.Frame):
    def __init__(self, master, issuer, secret, token_name, delete_token_callback):
        super().__init__(master, width=400, height=100)
        self.issuer = issuer
        self.secret = secret
        self.totp = pyotp.TOTP(self.secret)
        self.code = ttk.StringVar(value=self.totp.now())
        self.time_remaining = ttk.StringVar(value=self.get_time_remaining())

        # Update issuer label with a larger font
        self.issuer_label = ttk.Label(self, text=self.issuer, font="Calibri 16 bold")
        
        # Fix: The correct way to access the main window from TOTPFrame
        main_window = self.winfo_toplevel()
        
        # Store the original delete callback
        self.original_delete_callback = delete_token_callback
        
        # Update delete button to use icon if available
        if hasattr(main_window, 'delete_icon') and main_window.delete_icon:
            self.delete_btn = ttk.Button(
                self, 
                image=main_window.delete_icon, 
                command=self.confirm_delete,  # Changed to confirm_delete method
                bootstyle="primary"  # Changed from "light" to "primary" for blue color
            )
        else:
            self.delete_btn = ttk.Button(
                self, 
                text="×", 
                command=self.confirm_delete,  # Changed to confirm_delete method
                bootstyle="primary"  # Changed from "light" to "primary" for blue color
            )
        
        # Add hover bindings for the delete button
        self.delete_btn.bind("<Enter>", self.on_delete_hover_enter)
        self.delete_btn.bind("<Leave>", self.on_delete_hover_leave)

        # New: Add token name label with truncation and dark grey foreground
        self.full_name = token_name
        self.name_label = ttk.Label(self, text="", font="Calibri 12", foreground="#A9A9A9")
        self.name_font = tkFont.Font(family="Calibri", size=12)  # Create a Font object

        # Create a container frame for the code and copy button to ensure constant distance
        self.code_frame = ttk.Frame(self)
        self.code_label = ttk.Label(self.code_frame, textvariable=self.code, font="Calibri 24")
        self.code_label.pack(side="left", fill="x", expand=True)
        
        # Update copy button to use icon if available - also use main_window
        if hasattr(main_window, 'copy_icon') and main_window.copy_icon:
            # Use bootstyle instead of style for better color control
            self.copy_btn = ttk.Button(
                self.code_frame, 
                image=main_window.copy_icon, 
                command=self.copy_totp,
                bootstyle="primary"  # Change from "secondary" to "primary" for blue color
            )
            # Store the confirmation icon for later use
            self.copy_confirm_icon = main_window.copy_confirm_icon if hasattr(main_window, 'copy_confirm_icon') else None
            self.original_copy_icon = main_window.copy_icon
        else:
            self.copy_btn = ttk.Button(
                self.code_frame, 
                text="Copy", 
                command=self.copy_totp,
                bootstyle="primary"  # Change from "secondary" to "primary" for blue color
            )
        self.copy_btn.pack(side="left", padx=10)
        
        # Store original style and initialize after_id for animation
        self.original_style = "primary"  # Change from "secondary" to "primary" to match above
        self.after_id = None  # Use a single after_id instead of a list

        self.time_remaining_label = ttk.Label(self, textvariable=self.time_remaining, font="Calibri 16")
        
        # Update layout: row0 for issuer and delete; row1 for token name; row2 for totp data.
        self.issuer_label.grid(row=0, column=0, sticky='w', padx=20)
        self.delete_btn.grid(row=0, column=1, sticky='e', padx=20)
        self.name_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=20)
        self.code_frame.grid(row=2, column=0, sticky="ew", padx=20)
        self.time_remaining_label.grid(row=2, column=1, sticky='e', padx=20)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        # Bind to configure event to handle resizing
        self.bind('<Configure>', self.on_resize)
        self.update_name_truncation()

    def update(self):
        self.code.set(self.totp.now())
        self.time_remaining.set(self.get_time_remaining())

    def get_time_remaining(self):
        return int(self.totp.interval - datetime.now().timestamp() % self.totp.interval)

    def copy_totp(self):
        # First copy to clipboard
        self.master.master.clipboard_clear()
        self.master.master.clipboard_append(self.code.get())
        
        # Then show visual feedback
        self.animate_copy_confirmation()
    
    def animate_copy_confirmation(self):
        # Cancel any pending reset operations to avoid timing conflicts
        if hasattr(self, 'after_id') and self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        
        try:
            # Store the original command and temporarily prevent clicking by removing it
            self.original_command = self.copy_btn['command']
            self.copy_btn.configure(command=lambda: None)  # Empty command instead of disabling
            
            # Change to success style using bootstyle instead of style
            self.copy_btn.configure(bootstyle="success")
            
            # Change icon if available
            if hasattr(self, 'copy_confirm_icon') and self.copy_confirm_icon:
                self.copy_btn.configure(image=self.copy_confirm_icon)
            elif not hasattr(self, 'original_copy_icon'):  # If using text instead of icon
                self.copy_btn.configure(text="✓")
            
            # Store the after ID so we can cancel it if needed
            self.after_id = self.after(1500, self.reset_copy_button)
        except Exception as e:
            print(f"Animation error: {e}")
            # Ensure we reset the button even if animation fails
            self.reset_copy_button()
    
    def reset_copy_button(self):
        try:
            # Restore original style using bootstyle
            self.copy_btn.configure(bootstyle=self.original_style)
            
            # Restore original icon or text
            if hasattr(self, 'original_copy_icon') and self.original_copy_icon:
                self.copy_btn.configure(image=self.original_copy_icon)
            elif not hasattr(self, 'original_copy_icon'):  # If using text instead of icon
                self.copy_btn.configure(text="Copy")
            
            # Restore the original command
            if hasattr(self, 'original_command'):
                self.copy_btn.configure(command=self.original_command)
        except Exception as e:
            print(f"Reset button error: {e}")
        
        # Clear the after_id
        self.after_id = None

    def update_name_truncation(self):
        # Always set text content first to ensure it's displayed
        self.name_label.configure(text=self.full_name)
        
        # Make sure the widget is actually visible before trying truncation
        if not self.winfo_ismapped() or self.winfo_width() <= 1:
            # Schedule another attempt after initial layout
            self.after(200, self.update_name_truncation)
            return
        
        # Hard-code a simple truncation approach - show up to 30 chars + ellipsis
        if len(self.full_name) > 30:
            truncated = self.full_name[:30] + "..."
            self.name_label.configure(text=truncated)
        else:
            self.name_label.configure(text=self.full_name)

    def on_resize(self, event):
        self.after(50, self.update_name_truncation)  # Debounce the resize event

    def on_delete_hover_enter(self, event):
        """Change delete button style to red on hover"""
        self.delete_btn.configure(bootstyle="danger")
    
    def on_delete_hover_leave(self, event):
        """Restore delete button style when mouse leaves"""
        self.delete_btn.configure(bootstyle="primary")  # Changed from "light" to "primary"
    
    def confirm_delete(self):
        """Show a confirmation dialog before deleting the token"""
        issuer_name = self.issuer
        result = messagebox.askyesno(
            "Confirm Deletion", 
            f"Are you sure you want to delete the token for '{issuer_name}'?",
            icon=messagebox.WARNING
        )
        if result:
            # User confirmed deletion, proceed with original callback
            self.original_delete_callback()

class SearchBar(ttk.Frame):
    def __init__(self, master, add_token_callback, search_callback, sort_callback):
        super().__init__(master, width=master.width)
        self.grid(row=0, column=0, pady=20, padx=20, sticky="ew")
        self.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)  # Added one more column for sort button

        # Create custom button style with padding - remove borderradius
        self.button_style = ttk.Style()
        self.button_style.configure("Custom.TButton", padding=6)
        # These are standard ttk style options that should work
        self.button_style.configure("Custom.TButton", relief="flat")

        self.search_input = ttk.Entry(self)
        self.search_input.grid(row=0, column=0, sticky='ew')
        self.search_input.bind("<KeyRelease>", lambda event: search_callback(self.search_input.get()))

        # Create search button with icon or fallback text
        if hasattr(master, 'search_icon') and master.search_icon:
            self.search_button = ttk.Button(
                self, 
                image=master.search_icon,
                command=lambda: search_callback(self.search_input.get()),
                style="Custom.TButton"  # Apply our custom style
            )
            self.search_button.image = master.search_icon  # Keep reference to prevent GC
        else:
            self.search_button = ttk.Button(
                self, 
                text="🔍",
                command=lambda: search_callback(self.search_input.get()),
                style="Custom.TButton"  # Apply our custom style
            )
        self.search_button.grid(row=0, column=1, sticky='w', padx=5)  # Add padding between buttons

        # Add sort button with icon support
        if hasattr(master, 'sort_asc_icon') and master.sort_asc_icon:
            self.sort_btn = ttk.Button(
                self, 
                image=master.sort_asc_icon,  # Start with ascending icon
                command=sort_callback,
                style="Custom.TButton"
            )
            # Store both icons as attributes for later switching
            self.sort_asc_image = master.sort_asc_icon
            self.sort_desc_image = master.sort_desc_icon
        else:
            self.sort_btn = ttk.Button(
                self, 
                text="↑↓",  # Default to up/down arrows as icon
                command=sort_callback,
                style="Custom.TButton"
            )
        self.sort_btn.grid(row=0, column=2, sticky='w', padx=5)
        
        # Create add button with icon or fallback text
        if hasattr(master, 'plus_icon') and master.plus_icon:
            self.add_btn = ttk.Button(
                self, 
                image=master.plus_icon,
                command=add_token_callback,
                style="Custom.TButton"  # Apply our custom style
            )
            self.add_btn.image = master.plus_icon  # Keep reference to prevent GC
        else:
            self.add_btn = ttk.Button(
                self, 
                text="+",
                command=add_token_callback,
                style="Custom.TButton"  # Apply our custom style
            )
        self.add_btn.grid(row=0, column=3, sticky='e', padx=5)  # Add padding between buttons

        # Create settings button with icon or fallback text
        if hasattr(master, 'settings_icon') and master.settings_icon:
            self.settings_btn = ttk.Button(
                self, 
                image=master.settings_icon,
                command=master.show_settings,  # Connect to the settings method
                style="Custom.TButton"  # Apply our custom style
            )
            self.settings_btn.image = master.settings_icon  # Keep reference to prevent GC
        else:
            self.settings_btn = ttk.Button(
                self, 
                text="⚙",
                command=master.show_settings,  # Connect to the settings method
                style="Custom.TButton"  # Apply our custom style
            )
        self.settings_btn.grid(row=0, column=4, sticky='e', padx=5)  # Changed column to 4

    # Update method to handle icon switching
    def update_sort_button(self, ascending):
        if hasattr(self, 'sort_asc_image') and hasattr(self, 'sort_desc_image'):
            self.sort_btn.configure(image=self.sort_asc_image if ascending else self.sort_desc_image)
        else:
            self.sort_btn.configure(text="A→Z" if ascending else "Z→A")

class WinOTP(ttk.Window):
    def __init__(self, tokens_path):
        # Set dark mode theme.
        super().__init__(themename='darkly')
        
        # Remove the problematic line that was causing the error
        # style = ttk.Style()
        # style.configure("Round.TButton", borderradius=20)
        
        self.title("WinOTP")
        self.width = 500
        self.height = 600
        self.center_window()
        self.resizable(False, False)
        self.tokens_path = tokens_path
        
        # Add sort order state variable
        self.sort_ascending = True
        
        # Load Icons
        self.load_icons()

        # Configure focus highlighting to be invisible
        style = ttk.Style()
        style.configure('TButton', focuscolor=style.configure('TFrame', 'background'))
        style.configure('TEntry', highlightthickness=0, bd=0)
        style.map('TButton', 
                  relief=[('focus', 'flat')],
                  borderwidth=[('focus', 0)],
                  highlightthickness=[('focus', 0)])
                  
        # Add takefocus=0 option to all button creation methods and set cursor to hand2
        self.original_button_init = ttk.Button.__init__
        
        def button_init_wrapper(instance, master=None, **kw):
            # Add hand cursor for all buttons
            if 'cursor' not in kw:
                kw['cursor'] = 'hand2'
            # Prevent focus outline
            if 'takefocus' not in kw:
                kw['takefocus'] = 0
            self.original_button_init(instance, master, **kw)
            
        ttk.Button.__init__ = button_init_wrapper

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.search_bar = SearchBar(self, self.add_token, self.search_tokens, self.sort_tokens)
        self.canvas = Canvas(self, width=self.width)
        self.canvas.grid(row=1, column=0, sticky="nsew")

        self.v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        # Don't grid the scrollbar here - we'll manage it with update_scrollbar_visibility()
        
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.columnconfigure(0, weight=1)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", self.configure_scroll_region)
        self.canvas.itemconfig(self.canvas_window, width=self.width)

        self.frames = {}
        self.filtered_frames = {} #keep track of the filtered frames
        
        # Initialize welcome_frame as None
        self.welcome_frame = None
        
        self.init_frames()
        
        # Update sort button text
        self.search_bar.update_sort_button(self.sort_ascending)
        
        # Check if scrollbar is needed
        self.update_scrollbar_visibility()

        self.canvas.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self.on_mouse_wheel)

        self.after(1000, self.update_frames)
    
    def load_icons(self):
        """Loads icons for the application."""
        icon_dir = "static/images/"
        
        # Check if the directory exists
        if not os.path.exists(icon_dir):
            os.makedirs(icon_dir)
            print(f"Directory '{icon_dir}' created.")

        # Load all needed icons
        icons = {
            "qr_icon": "qr_code.png", 
            "manual_icon": "manual_entry.png",
            "back_icon": "back_arrow.png", 
            "plus_icon": "plus.png",
            "settings_icon": "settings.png", 
            "search_icon": "search.png",
            # Add new icons for sort, copy, and delete buttons
            "copy_icon": "copy.png",
            "copy_confirm_icon": "copy_confirm.png",  # Add the new confirmation icon
            "delete_icon": "delete.png",
            "sort_asc_icon": "sort_asc.png",
            "sort_desc_icon": "sort_desc.png",
            # Add empty drawer icon
            "empty_drawer_icon": "drawer-empty.png"
        }
        
        # Define icon sizes
        sizes = {
            "qr_icon": (32, 32),
            "manual_icon": (32, 32),
            "back_icon": (24, 24),
            "plus_icon": (16, 16),
            "settings_icon": (16, 16),
            "search_icon": (16, 16),
            # Define sizes for new icons
            "copy_icon": (16, 16),
            "copy_confirm_icon": (16, 16),  # Add size for the new icon
            "delete_icon": (16, 16),
            "sort_asc_icon": (16, 16),
            "sort_desc_icon": (16, 16),
            # Define size for empty drawer icon
            "empty_drawer_icon": (128, 128)
        }
        
        # Load each icon
        for icon_name, file_name in icons.items():
            full_path = os.path.join(icon_dir, file_name)
            setattr(self, icon_name, self.load_icon(full_path, sizes[icon_name]))
            if getattr(self, icon_name) is None:
                print(f"Failed to load {icon_name} from {full_path}")

    def load_icon(self, path, size):
        """Loads an icon from the given path and resizes it."""
        try:
            # Check if file exists
            if not os.path.isfile(path):
                print(f"Icon file not found: {path}")
                return None

            # Open and process the image
            img = Image.open(path)
            
            # Convert to RGBA mode to ensure transparency support
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Resize with high-quality resampling
            img = img.resize(size, Image.LANCZOS)
            
            # Create PhotoImage from the processed image
            photo = ImageTk.PhotoImage(img)
            return photo
        
        except FileNotFoundError:
            print(f"Icon not found: {path}")
            return None
        except Exception as e:
            print(f"Error loading icon {path}: {str(e)}")
            return None

    def center_window(self):
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws / 2) - (self.width / 2)
        y = (hs / 2) - (self.height / 2)
        self.geometry('%dx%d+%d+%d' % (self.width, self.height, x, y))

    def configure_scroll_region(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # Check scrollbar visibility after scroll region is configured
        self.update_scrollbar_visibility()

    def init_frames(self):
        config = self.read_json(self.tokens_path)
        
        # Check if there are any tokens
        if not config:
            # Show welcome message when no tokens exist
            self.show_welcome_message()
            return
        
        # Create frames but don't add them to grid yet
        for token_id, data in config.items():
            # Make sure we have the required fields, handle old format gracefully
            if "issuer" not in data:
                # Handle old format where issuer was the key
                issuer = token_id
            else:
                issuer = data["issuer"]
                
            secret = data["secret"]
            name = data["name"]
            
            # Create a frame
            frame = TOTPFrame(self.scrollable_frame, issuer, secret, name, lambda i=token_id: self.delete_token(i))
            self.frames[token_id] = {"frame": frame, "issuer": issuer}
            self.filtered_frames[token_id] = {"frame": frame, "issuer": issuer}
        
        # Sort by issuer and add frames to the grid
        self._apply_current_sorting()
        
        # Hide welcome message if it exists
        if self.welcome_frame:
            self.welcome_frame.grid_forget()
            
        # Update scrollbar visibility after adding frames
        self.after(100, self.update_scrollbar_visibility)
        
        # Print loaded tokens for debugging
        print(f"Loaded {len(self.frames)} tokens:")
        for token_id, data in self.frames.items():
            frame = data["frame"]
            print(f"  {frame.issuer}: {frame.secret[:3]}...{frame.secret[-3:]} ({token_id})")
    
    def show_welcome_message(self):
        """Show a welcome message when no tokens exist"""
        # If welcome frame exists, remove it first
        if self.welcome_frame:
            self.welcome_frame.grid_forget()
            
        # Create a new welcome frame
        self.welcome_frame = ttk.Frame(self.scrollable_frame)
        self.welcome_frame.grid(row=0, column=0, sticky='nsew', padx=20, pady=20)
        
        # Center the content within the welcome frame
        self.welcome_frame.columnconfigure(0, weight=1)
        
        # Create a container for the welcome message
        welcome_container = ttk.Frame(self.welcome_frame)
        welcome_container.grid(row=0, column=0, pady=80)
        welcome_container.columnconfigure(0, weight=1)
        
        # Add empty drawer image
        if hasattr(self, 'empty_drawer_icon') and self.empty_drawer_icon:
            image_label = ttk.Label(welcome_container, image=self.empty_drawer_icon)
            image_label.grid(row=0, column=0, pady=10)
        
        # Add welcome message
        ttk.Label(
            welcome_container, 
            text="No TOTP tokens found", 
            font="Calibri 16 bold"
        ).grid(row=1, column=0, pady=10)
        
        ttk.Label(
            welcome_container, 
            text="Click the + button in the top bar to add your first token", 
            font="Calibri 12", 
            wraplength=350
        ).grid(row=2, column=0, pady=5)
        
        # Add text about bulk import instead of Add Token button
        ttk.Label(
            welcome_container,
            text="If you have a compatible export from another app, you can use the ⚙ Settings menu to bulk import your tokens.",
            font="Calibri 12 italic",
            foreground="#A9A9A9",  # Dark gray for secondary information
            wraplength=350,
            justify="center"
        ).grid(row=3, column=0, pady=20)

    def update_frames(self):
        for data in self.frames.values():
            data["frame"].update()
        self.after(1000, self.update_frames)

    def sort_tokens(self):
        """Sort tokens by issuer name and toggle between ascending and descending order"""
        self.sort_ascending = not self.sort_ascending
        self.search_bar.update_sort_button(self.sort_ascending)
        
        # Apply the new sorting order
        self._apply_current_sorting()
    
    def _apply_current_sorting(self):
        """Apply the current sorting order to the filtered frames"""
        # Get issuers from filtered frames
        sorted_tokens = sorted(
            self.filtered_frames.items(),
            key=lambda item: item[1]["issuer"],
            reverse=not self.sort_ascending
        )
        
        # Update the UI - hide all frames first
        for data in self.frames.values():
            data["frame"].grid_forget()
        
        # Show them in the sorted order
        for i, (token_id, data) in enumerate(sorted_tokens):
            data["frame"].grid(row=i, column=0, pady=20, padx=20, sticky='ew')
        
        # Update scrollbar visibility after re-arranging frames
        self.update_scrollbar_visibility()
    
    def search_tokens(self, query):
        query = query.lower()
        self.filtered_frames = {}  # Clear the current filtered frames
        
        # Filter frames by search query
        for token_id, data in self.frames.items():
            if query in data["issuer"].lower():
                self.filtered_frames[token_id] = data
        
        # Apply sort order to the filtered results
        self._apply_current_sorting()

    def add_token(self):
        for widget in self.winfo_children():
            widget.grid_forget()

        self.add_token_frame = ttk.Frame(self)
        self.add_token_frame.grid(row=0, column=0, pady=20, padx=20, sticky="nsew")
        self.add_token_frame.columnconfigure(0, weight=1)

        # Add back button at the top left
        if self.back_icon:
            back_btn = ttk.Button(self.add_token_frame, image=self.back_icon, compound=ttk.LEFT, command=self.show_main_view, style='Link.TButton')
        else:
            back_btn = ttk.Button(self.add_token_frame, text="←", command=self.show_main_view, style='Link.TButton')
        back_btn.grid(row=0, column=0, sticky="nw", pady=5)

        ttk.Label(self.add_token_frame, text="Add Token", font="Calibri 16 bold").grid(row=1, column=0, pady=10)

        if self.qr_icon:
            ttk.Button(self.add_token_frame, text="Add from QR Code", image=self.qr_icon, compound=ttk.LEFT, command=self.add_token_from_qr).grid(row=2, column=0, pady=10, padx=20, sticky="ew")
        else:
            ttk.Button(self.add_token_frame, text="Add from QR Code", command=self.add_token_from_qr).grid(row=2, column=0, pady=10, padx=20, sticky="ew")

        if self.manual_icon:
            ttk.Button(self.add_token_frame, text="Add Manually", image=self.manual_icon, compound=ttk.LEFT, command=self.add_token_manually).grid(row=3, column=0, pady=10, padx=20, sticky="ew")
        else:
            ttk.Button(self.add_token_frame, text="Add Manually", command=self.add_token_manually).grid(row=3, column=0, pady=10, padx=20, sticky="ew")

        # The old back button at row 3 has been removed

    def show_main_view(self):
        for widget in self.winfo_children():
            widget.grid_forget()
        self.search_bar.grid(row=0, column=0, pady=20, padx=20, sticky="ew")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        # Don't grid the scrollbar here, let update_scrollbar_visibility handle it
        
        self.search_tokens(self.search_bar.search_input.get())
        # Update sort button text when returning to main view
        self.search_bar.update_sort_button(self.sort_ascending)
        
        # Update scrollbar visibility will be called by search_tokens > _apply_current_sorting

    def add_token_manually(self):
        for widget in self.add_token_frame.winfo_children():
            widget.grid_forget()

        ttk.Label(self.add_token_frame, text="Add Token Manually", font="Calibri 16 bold").grid(row=0, column=0, pady=10)

        ttk.Label(self.add_token_frame, text="Issuer:").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.issuer_entry = ttk.Entry(self.add_token_frame)
        self.issuer_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        ttk.Label(self.add_token_frame, text="Secret Key:").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.secret_entry = ttk.Entry(self.add_token_frame)
        self.secret_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        ttk.Label(self.add_token_frame, text="Name:").grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.name_entry = ttk.Entry(self.add_token_frame)
        self.name_entry.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        ttk.Button(self.add_token_frame, text="Add", command=self.add_manual_token).grid(row=4, column=0, columnspan=2, pady=20, padx=20, sticky="ew")
        
        # Also update this back button to match the style of the main add token page
        if hasattr(self, 'back_icon') and self.back_icon:
            back_btn = ttk.Button(self.add_token_frame, text="Back", image=self.back_icon, compound=ttk.LEFT, command=self.add_token)
        else:
            back_btn = ttk.Button(self.add_token_frame, text="← Back", command=self.add_token)
        back_btn.grid(row=5, column=0, columnspan=2, pady=10, padx=20, sticky="ew")
        
        self.add_token_frame.columnconfigure(1, weight=1)

    def add_token_from_qr(self):
        filename = filedialog.askopenfilename()
        if filename:
            qr_data = decode(Image.open(filename))
            if not qr_data:
                messagebox.showerror("Error", "No QR code found in the image.")
                return
            uri = qr_data[0].data.decode("utf-8")
            pattern = r'otpauth://totp/(?P<name>[^?]+)\?secret=(?P<secret>[^&]+)&issuer=(?P<issuer>[^&]+)'
            match = re.search(pattern, uri)
            if match:
                name = unquote(match.group('name'))
                secret = match.group('secret')
                issuer = unquote(match.group('issuer'))
                self.add_new_token(issuer, secret, name)
            else:
                 messagebox.showerror("Error", "Invalid QR code format.")
    
    def add_manual_token(self):
        issuer = self.issuer_entry.get().strip()
        secret = self.secret_entry.get().strip().replace(" ", "").upper()
        name = self.name_entry.get().strip()

        # Validate fields
        if not issuer:
            messagebox.showerror("Error", "Please enter an issuer name.")
            return
            
        if not name:
            messagebox.showerror("Error", "Please enter an account name.")
            return
        
        # Validate secret - must be valid base32 for TOTP
        if not secret:
            messagebox.showerror("Error", "Please enter a secret key.")
            return
            
        if not self.validate_base32_secret(secret):
            messagebox.showerror(
                "Invalid Secret", 
                "The secret key must be a valid base32 string containing only A-Z, 2-7 characters."
            )
            return
            
        try:
            # Attempt to create a TOTP object to validate the secret works
            test_totp = pyotp.TOTP(secret)
            test_totp.now()  # This will fail if the secret is invalid
        except Exception as e:
            messagebox.showerror("Invalid Secret", f"The secret key is not valid: {str(e)}")
            return
        
        self.add_new_token(issuer, secret, name)

        self.add_token_frame.grid_forget()
        self.show_main_view()
    
    def validate_base32_secret(self, secret):
        """Validate if the provided string is a valid base32 secret"""
        # Base32 alphabet: A-Z and 2-7
        import re
        
        # Remove any padding characters
        secret = secret.rstrip("=")
        
        # Check if the string only contains valid base32 characters
        if not re.match(r'^[A-Z2-7]+$', secret):
            return False
            
        # Base32 encoded data should have a length that's a multiple of 8
        # But for TOTP secrets, we're slightly more lenient
        return len(secret) >= 16  # Most TOTP secrets are at least 16 chars

    def add_new_token(self, issuer, secret, name):
        config = self.read_json(self.tokens_path)
        
        # Check for duplicate secrets
        for token_id, data in config.items():
            # Handle both old and new format
            token_secret = data["secret"]
            if token_secret == secret:
                messagebox.showerror("Error", "Token with the same secret already exists")
                return
        
        # Create a new unique token ID
        import uuid
        token_id = f"token_{uuid.uuid4().hex[:8]}"
        
        # Store in new format
        config[token_id] = {
            "issuer": issuer,
            "name": name,
            "secret": secret
        }
        
        self.write_json(self.tokens_path, config)
        
        # Create the new frame
        new_frame = TOTPFrame(self.scrollable_frame, issuer, secret, name, lambda i=token_id: self.delete_token(i))
        self.frames[token_id] = {"frame": new_frame, "issuer": issuer}
        self.filtered_frames[token_id] = {"frame": new_frame, "issuer": issuer} 
        
        # Hide welcome message if it was shown
        if self.welcome_frame:
            self.welcome_frame.grid_forget()
        
        # Apply sorting after adding a new token
        self.search_tokens(self.search_bar.search_input.get())
        
        if hasattr(self, 'add_token_window'):
            self.add_token_window.destroy()

    def delete_token(self, token_id):
        # Get the frame from our data structure
        if token_id in self.frames:
            self.frames[token_id]["frame"].grid_forget()
            self.frames.pop(token_id)
            
        if token_id in self.filtered_frames:
            self.filtered_frames.pop(token_id)
        
        # Remove from config file
        config = self.read_json(self.tokens_path)
        if token_id in config:
            config.pop(token_id)
            self.write_json(self.tokens_path, config)
        
        # Update the search/display
        self.search_tokens(self.search_bar.search_input.get())
        
        # Show welcome message if all tokens have been deleted
        if not self.frames:
            self.show_welcome_message()

    @staticmethod
    def read_json(file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                print(f"Successfully loaded {len(data)} tokens from {file_path}")
                return data
        except FileNotFoundError:
            print(f"File not found: {file_path}, creating empty token storage")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {file_path}: {e}")
            return {}

    @staticmethod
    def write_json(file_path, data):
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

    def on_mouse_wheel(self, event):
        # Handle different mouse wheel event formats across platforms
        delta = 0
        
        # Windows mouse wheel (event.delta)
        if hasattr(event, 'delta'):
            delta = event.delta
        # Linux (Button-4/Button-5)
        elif event.num == 4:
            delta = 120
        elif event.num == 5:
            delta = -120
        # macOS (event.x, event.y)
        elif hasattr(event, 'x') and hasattr(event, 'y'):
            delta = event.y * 10
            
        # Check if we've hit the top or bottom of the scrollable area
        current_view = self.canvas.yview()
        if (delta > 0 and current_view[0] <= 0) or (delta < 0 and current_view[1] >= 1):
            return
            
        # Adjust the scroll amount (units vs pixels may need tuning per platform)
        self.canvas.yview_scroll(int(-1 * (delta / 120)), "units")
    
    def update_scrollbar_visibility(self):
        """Show or hide scrollbar depending on if it's needed"""
        # Get the height of the scrollable content
        self.update_idletasks()  # Ensure geometry is updated
        content_height = self.scrollable_frame.winfo_reqheight()
        canvas_height = self.canvas.winfo_height()
        
        # Show scrollbar only if content height exceeds the canvas height
        if content_height > canvas_height:
            self.v_scrollbar.grid(row=1, column=1, sticky="ns")
        else:
            self.v_scrollbar.grid_forget()

    def show_settings(self):
        """Show the settings page"""
        for widget in self.winfo_children():
            widget.grid_forget()

        # Create settings frame
        self.settings_frame = ttk.Frame(self)
        self.settings_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.settings_frame.columnconfigure(0, weight=1)

        # Add back button at the top left
        if hasattr(self, 'back_icon') and self.back_icon:
            back_btn = ttk.Button(
                self.settings_frame, 
                image=self.back_icon, 
                compound=ttk.LEFT, 
                command=self.show_main_view, 
                style='Link.TButton'
            )
        else:
            back_btn = ttk.Button(
                self.settings_frame, 
                text="←", 
                command=self.show_main_view, 
                style='Link.TButton'
            )
        back_btn.grid(row=0, column=0, sticky="nw", pady=5)

        # Add settings title
        ttk.Label(
            self.settings_frame, 
            text="Settings", 
            font="Calibri 16 bold"
        ).grid(row=1, column=0, pady=10, sticky="w")
        
        # Bulk import section
        ttk.Label(
            self.settings_frame, 
            text="Bulk Import", 
            font="Calibri 14 bold"
        ).grid(row=2, column=0, pady=(20, 10), sticky="w")
        
        ttk.Label(
            self.settings_frame, 
            text="Import multiple TOTP tokens from a JSON file", 
            wraplength=450
        ).grid(row=3, column=0, pady=5, sticky="w")
        
        ttk.Button(
            self.settings_frame, 
            text="Import from JSON", 
            command=self.bulk_import_tokens, 
            bootstyle="primary"
        ).grid(row=4, column=0, pady=10, sticky="w")
        
        # JSON format help
        ttk.Label(
            self.settings_frame,
            text="Expected JSON Format:",
            font="Calibri 12 bold"
        ).grid(row=5, column=0, pady=(20, 5), sticky="w")
        
        format_text = """{
    "token_1": {
        "issuer": "Service Name",
        "name": "username@example.com",
        "secret": "BASE32SECRET"
    },
    "token_2": {
        "issuer": "Another Service",
        "name": "username",
        "secret": "ANOTHERBASE32SECRET"
    }
}"""
        
        format_label = ttk.Label(
            self.settings_frame,
            text=format_text,
            font="Courier 10",
            justify="left",
            wraplength=450
        )
        format_label.grid(row=6, column=0, pady=5, sticky="w")

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
            current_tokens = self.read_json(self.tokens_path)
            
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
                import uuid
                new_token_id = f"token_{uuid.uuid4().hex[:8]}"
                
                # Add to current tokens
                current_tokens[new_token_id] = {
                    "issuer": data["issuer"],
                    "name": data["name"],
                    "secret": data["secret"]
                }
                imported_count += 1
            
            # Save updated tokens
            self.write_json(self.tokens_path, current_tokens)
            
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

if __name__ == "__main__":
    # Check if debug mode is enabled via command line arguments
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    # Select the appropriate tokens file
    if debug_mode:
        tokens_path = "tokens.json.dev"
        print("Running in DEBUG mode with tokens.json.dev")
    else:
        tokens_path = "tokens.json"
        print("Running in PRODUCTION mode with tokens.json")
    
    app = WinOTP(tokens_path)
    app.mainloop()
