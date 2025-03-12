import ttkbootstrap as ttk
from tkinter import messagebox
import tkinter.font as tkFont
import pyotp
from datetime import datetime
from models.token import Token
from PIL import Image, ImageTk
import os

class TOTPFrame(ttk.Frame):
    def __init__(self, master, issuer, secret, token_name, delete_token_callback):
        # Use normal Frame without height constraint
        super().__init__(master)
        
        # Make sure the frame spans the full width of its container
        self.configure(width=480)
        
        # Add a dark gray border with rounded corners
        self.configure(bootstyle="primary-borderless", padding=4)
        self["borderwidth"] = 0
        
        # Apply rounded corners and dark gray border using custom styling
        style = ttk.Style()
        frame_style = f"CustomTOTP{str(id(self))}.TFrame"
        style.configure(frame_style, corner_radius=15)
        self.configure(style=frame_style)
        
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
        
        # Load the remove icon directly from the icons folder
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icons", "remove.png")
            if os.path.exists(icon_path):
                remove_image = Image.open(icon_path)
                # Resize the image to 16x16 pixels
                remove_image = remove_image.resize((16, 16), Image.LANCZOS)
                self.remove_icon = ImageTk.PhotoImage(remove_image)
                
                # Create a style for a fixed-size button with dark grey color
                btn_style_name = f"DeleteBtn{str(id(self))}"
                self.btn_style = f"{btn_style_name}.TButton"
                style.configure(self.btn_style, width=18, height=18, padding=2)
                # Configure hover state to prevent default hover effects
                style.map(self.btn_style,
                    background=[('active', '#555555')],  # Default state
                    relief=[('active', 'flat')],
                    borderwidth=[('active', '0')]
                )
                
                # Create button without bootstyle to avoid conflicts
                self.delete_btn = ttk.Button(
                    self, 
                    image=self.remove_icon, 
                    command=self.confirm_delete,
                    style=self.btn_style
                )
                
                # Apply dark grey color to the button (after creation to avoid conflicts)
                style.configure(self.btn_style, background="#555555", borderwidth=0, relief="flat")
            else:
                # Fallback if image not found
                # Create a style for a fixed-size button with dark grey color
                btn_style_name = f"DeleteBtn{str(id(self))}"
                self.btn_style = f"{btn_style_name}.TButton"
                style.configure(self.btn_style, width=18, height=18, padding=2)
                
                # Create button without bootstyle to avoid conflicts
                self.delete_btn = ttk.Button(
                    self, 
                    text="×", 
                    command=self.confirm_delete,
                    style=self.btn_style
                )
                
                # Apply dark grey color to the button (after creation to avoid conflicts)
                style.configure(self.btn_style, background="#555555", borderwidth=0, relief="flat")
        except Exception as e:
            print(f"Error loading remove icon: {e}")
            # Fallback to text if any error occurs
            # Use a unique style name for this button too
            btn_style_name = f"DeleteBtn{str(id(self))}"
            self.btn_style = f"{btn_style_name}.TButton"
            style.configure(self.btn_style, width=18, height=18, padding=2, background="#555555", borderwidth=0, relief="flat")
            
            self.delete_btn = ttk.Button(
                self, 
                text="×", 
                command=self.confirm_delete,
                style=self.btn_style
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
        self.code_label = ttk.Label(self.code_frame, textvariable=self.code, font="Calibri 24 bold", width=8)  # Reduced font size from 30 to 24
        self.code_label.pack(side="left", fill="x", expand=True)
        
        # Update copy button to use icon if available - also use main_window
        if hasattr(main_window, 'copy_icon') and main_window.copy_icon:
            # Use bootstyle instead of style for better color control
            self.copy_btn = ttk.Button(
                self.code_frame, 
                image=main_window.copy_icon, 
                command=self.copy_totp,
                bootstyle="primary"
            )
            # Store the confirmation icon for later use
            self.copy_confirm_icon = main_window.copy_confirm_icon if hasattr(main_window, 'copy_confirm_icon') else None
            self.original_copy_icon = main_window.copy_icon
        else:
            self.copy_btn = ttk.Button(
                self.code_frame, 
                text="Copy", 
                command=self.copy_totp,
                bootstyle="primary"
            )
        self.copy_btn.pack(side="left", padx=10)
        
        # Store original style and initialize after_id for animation
        self.original_style = "primary"
        self.after_id = None  # Use a single after_id instead of a list

        # Create progress bar for countdown
        self.progress_bar = ttk.Progressbar(
            self,
            bootstyle="primary",
            orient="horizontal",
            mode="determinate",
            length=480,  # Will be adjusted to match frame width
            value=100    # Start at 100%
        )
        
        # Create a custom style for the progress bar with minimal height
        progress_style_name = f"CustomProgress{str(id(self))}.Horizontal.TProgressbar"
        style = ttk.Style()
        style.configure(progress_style_name, thickness=2)  # Set very small thickness
        style.layout(progress_style_name, [
            ('Horizontal.Progressbar.trough', {
                'sticky': 'nswe',
                'children': [('Horizontal.Progressbar.pbar', {'sticky': 'nswe'})],
            })
        ])
        self.progress_bar.configure(style=progress_style_name)

        self.time_remaining_label = ttk.Label(self, textvariable=self.time_remaining, font="Calibri 16")
        
        # COMPLETELY REDESIGNED LAYOUT
        # Use a 3-column grid for maximum width utilization
        # Column 0: Main content (issuer, name, code) - expandable
        # Column 1: Center spacer - expandable
        # Column 2: Right content (delete button, countdown) - fixed width
        
        # Row 0: Issuer and delete button
        self.issuer_label.grid(row=0, column=0, columnspan=2, sticky='w', padx=(5, 0), pady=(10, 0))
        
        # Position delete button in the absolute top right corner with no padding
        self.delete_btn.grid(row=0, column=2, sticky='ne', padx=0, pady=0)
        
        # Row 1: Name label
        self.name_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=(5, 0), pady=(0, 5))
        
        # Row 2: TOTP code
        self.code_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=(5, 0), pady=(5, 10))
        
        # Row 3: Progress bar at the bottom, spanning all columns
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky="sew", padx=0, pady=0)
        
        # Configure columns for proper expansion
        # First column contains all content, no minimum width constraint
        self.columnconfigure(0, weight=0)
        # Middle column takes all extra space
        self.columnconfigure(1, weight=1)
        # Right column only for delete button
        self.columnconfigure(2, weight=0, minsize=30)
        
        # Disable grid propagation to ensure the frame maintains its size
        self.grid_propagate(False)
        
        # Set a minimum height
        self.configure(height=140)  # Increased from 130 to 140 to accommodate the progress bar

        # Bind to configure event to handle resizing
        self.bind('<Configure>', self.on_resize)
        self.update_name_truncation()
        
        # Start progress bar update
        self.update_progress_bar()

    def update(self):
        self.code.set(self.totp.now())
        self.time_remaining.set(self.get_time_remaining())
        self.update_progress_bar()

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
        # Also update frame width to match parent
        self.update_frame_width()

    def update_frame_width(self):
        """Update frame width to match parent container width"""
        if self.master and self.master.winfo_exists():
            parent_width = self.master.winfo_width()
            if parent_width > 10:  # Only adjust if parent has a meaningful width
                # Set width while preserving other dimensions
                self.configure(width=parent_width - 20)  # Account for padx
                # Also update progress bar length to match frame width
                self.progress_bar.configure(length=parent_width - 20)

    def on_delete_hover_enter(self, event):
        """Change delete button style to red on hover"""
        style = ttk.Style()
        style.configure(self.btn_style, background="#FF0000")
        style.map(self.btn_style,
            background=[('active', '#FF0000')],  # Keep red on active state
            relief=[('active', 'flat')],
            borderwidth=[('active', '0')]
        )
    
    def on_delete_hover_leave(self, event):
        """Restore delete button style when mouse leaves"""
        style = ttk.Style()
        style.configure(self.btn_style, background="#555555")
        style.map(self.btn_style,
            background=[('active', '#555555')],  # Restore grey on active state
            relief=[('active', 'flat')],
            borderwidth=[('active', '0')]
        )
    
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

    def update_progress_bar(self):
        """Update the progress bar based on remaining time"""
        remaining_seconds = self.get_time_remaining()
        percentage = (remaining_seconds / self.totp.interval) * 100
        
        # Update progress bar value
        self.progress_bar["value"] = percentage
        
        # Change color to red when less than 5 seconds remain
        if remaining_seconds <= 5:
            self.progress_bar.configure(bootstyle="danger")
        else:
            self.progress_bar.configure(bootstyle="primary")
            
        # Schedule next update
        self.after(100, self.update_progress_bar) 