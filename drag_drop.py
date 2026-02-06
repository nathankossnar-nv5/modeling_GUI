import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
import yaml
from pathlib import Path
import subprocess
import sys
import threading
import glob
import os
import shutil
from datetime import datetime
from PIL import Image
import random
import json

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent
    
    return base_path / relative_path


def get_writable_path(relative_path):
    """Get path for writable files (configs, history). 
    When running as exe, use user's AppData folder instead of temp _MEIPASS"""
    try:
        # Check if running as PyInstaller bundle
        _ = sys._MEIPASS
        # Use user's AppData folder for writable files
        app_data = Path(os.environ.get('APPDATA', os.path.expanduser('~')))
        writable_dir = app_data / 'ModelingGUI'
        writable_dir.mkdir(parents=True, exist_ok=True)
        return writable_dir / relative_path
    except Exception:
        # Running as script, use normal path
        base_path = Path(__file__).parent
        return base_path / relative_path


class App(TkinterDnD.Tk):   # IMPORTANT: use TkinterDnD root
    def __init__(self):
        super().__init__()

        self.title("Drag and Drop File Path")
        self.geometry("700x1120")

        # Font configuration
        self.label_font = ("Segoe UI", 14)
        self.entry_font = ("Segoe UI", 13)
        self.button_font = ("Segoe UI", 13, "bold")
        self.title_font = ("Segoe UI", 22, "bold")

        # CustomTkinter frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Title with logo
        title_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        title_frame.pack(pady=(15, 20))
        
        # Load and display logo
        logo_path = get_resource_path("img") / "logo-nv5-white-no-tagline.png"
        if logo_path.exists():
            try:
                logo_image = Image.open(logo_path)
                # Resize logo to fit title (height ~40 pixels)
                aspect_ratio = logo_image.width / logo_image.height
                new_height = 40
                new_width = int(new_height * aspect_ratio)
                logo_image = logo_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logo_ctk = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(new_width, new_height))
                
                logo_label = ctk.CTkLabel(title_frame, image=logo_ctk, text="")
                logo_label.pack(side="left", padx=(0, 10))
            except Exception as e:
                print(f"Could not load logo: {e}")
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="Land Cover Script Interface",
            font=self.title_font
        )
        title_label.pack(side="left")

        # Script selector dropdown at top
        self.script_label = ctk.CTkLabel(self.main_frame, text="Select Script:", font=self.label_font)
        self.script_label.pack(pady=(10, 5))
        
        # Get all Python files in the current directory
        script_dir = get_resource_path(".")
        python_files = [f.name for f in script_dir.glob('*.py') if f.name != 'drag_drop.py']
        
        self.script_dropdown = ctk.CTkComboBox(
            self.main_frame,
            values=python_files if python_files else ["No scripts found"],
            width=400,
            height=40,
            command=self.on_script_selected,
            font=self.entry_font
        )
        if python_files:
            self.script_dropdown.set(python_files[0])
        self.script_dropdown.pack(pady=5)

        # Conda environment selector
        self.env_label = ctk.CTkLabel(self.main_frame, text="Conda Environment:", font=self.label_font)
        self.env_label.pack(pady=(10, 5))
        
        # Get conda environments
        conda_envs = self.get_conda_environments()
        
        self.env_dropdown = ctk.CTkComboBox(
            self.main_frame,
            values=conda_envs if conda_envs else ["No conda environments found"],
            width=400,
            height=40,
            font=self.entry_font
        )
        if conda_envs:
            # Try to set to 'base' or first environment
            if 'base' in conda_envs:
                self.env_dropdown.set('base')
            else:
                self.env_dropdown.set(conda_envs[0])
        self.env_dropdown.pack(pady=5)

        # View documentation button
        self.doc_button = ctk.CTkButton(
            self.main_frame,
            text="📄 View Documentation",
            command=self.show_documentation_window,
            width=200,
            height=35,
            font=self.entry_font
        )
        self.doc_button.pack(pady=10)

        # Scrollable frame for dynamic fields
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_frame,
            width=600,
            height=300
        )
        self.scroll_frame.pack(pady=10, fill="both", expand=True)

        # Dictionary to store field widgets
        self.field_entries = {}
        
        # Current config file (determined by script selection)
        self.current_config_file = None
        
        # Script execution state
        self.script_is_running = False
        
        # History file path
        self.history_file = get_writable_path("run_history.json")
        self._ensure_history_file()

        # Button frame for Save and Clear buttons
        button_frame = ctk.CTkFrame(self.main_frame)
        button_frame.pack(pady=10)

        # Save button
        self.save_button = ctk.CTkButton(
            button_frame,
            text="Save Configuration",
            command=self.save_config,
            width=200,
            height=40,
            font=self.button_font
        )
        self.save_button.pack(side="left", padx=5)

        # Clear button
        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear",
            command=self.clear_fields,
            width=100,
            height=40,
            font=self.button_font
        )
        self.clear_button.pack(side="left", padx=5)
        
        # History button
        self.history_button = ctk.CTkButton(
            button_frame,
            text="📜 History",
            command=self.show_history_browser,
            width=120,
            height=40,
            font=self.button_font,
            fg_color=["#9C27B0", "#7B1FA2"],  # Purple color
            hover_color=["#BA68C8", "#9C27B0"]
        )
        self.history_button.pack(side="left", padx=5)

        # Run/Stop button frame
        run_button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        run_button_frame.pack(pady=10)

        # Run script button
        self.wait_button = ctk.CTkButton(
            run_button_frame,
            text=f"Run {self.script_dropdown.get()}",
            command=self.run_wait_script,
            width=200,
            height=40,
            font=self.button_font
        )
        self.wait_button.pack(side="left", padx=5)

        # Stop button
        self.stop_button = ctk.CTkButton(
            run_button_frame,
            text="⏹ Stop",
            command=self.stop_script,
            width=100,
            height=40,
            font=self.button_font,
            fg_color=["#D32F2F", "#B71C1C"],  # Red color
            hover_color=["#F44336", "#D32F2F"]
        )
        # Don't pack initially - will show when script runs

        # Output section label
        self.output_label = ctk.CTkLabel(self.main_frame, text="Script Output:", font=self.label_font)
        self.output_label.pack(pady=(10, 5))
        
        self.output_textbox = ctk.CTkTextbox(
            self.main_frame,
            width=400,
            height=150,
            font=self.entry_font
        )
        self.output_textbox.pack(pady=(5, 5))
        
        # Expand button below output box
        self.expand_output_button = ctk.CTkButton(
            self.main_frame,
            text="🔍 Expand Output",
            command=self.show_expanded_output,
            width=150,
            height=30,
            font=("Segoe UI", 10),
            fg_color=["#9E9E9E", "#616161"],  # Gray color
            hover_color=["#BDBDBD", "#757575"]  # Lighter gray hover
        )
        self.expand_output_button.pack(pady=(5, 20))

        # Hover area for Pet Tax button at bottom (invisible frame)
        self.random_button_hover_area = ctk.CTkFrame(
            self.main_frame,
            width=140,
            height=35,
            fg_color="transparent"
        )
        self.random_button_hover_area.pack(pady=(10, 10))
        
        # Random image button (hidden until hover)
        self.random_img_button = ctk.CTkButton(
            self.random_button_hover_area,
            text="Pet Tax!",
            command=self.open_random_image,
            width=140,
            height=35,
            font=("Segoe UI", 11, "bold"),
            fg_color=["#F9F9FA", "#2B2B2B"],  # Match background
            text_color=["#F9F9FA", "#2B2B2B"],  # Match background
            border_width=0
        )
        self.random_img_button.place(relx=0.5, rely=0.5, anchor="center")  # Always visible
        
        # Bind hover events to both hover area and button
        self.random_button_hover_area.bind("<Enter>", self._show_random_button)
        self.random_button_hover_area.bind("<Leave>", self._hide_random_button)
        self.random_img_button.bind("<Enter>", self._show_random_button)
        self.random_img_button.bind("<Leave>", self._hide_random_button)

        # Load initial config based on first script (after all widgets created)
        if python_files:
            self.on_script_selected(python_files[0])

    def get_conda_environments(self):
        """Get list of available conda environments"""
        try:
            # Try different conda commands for Windows
            conda_commands = ['conda', 'conda.exe']
            
            for conda_cmd in conda_commands:
                try:
                    result = subprocess.run(
                        [conda_cmd, 'env', 'list'],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=True  # Use shell on Windows
                    )
                    
                    if result.returncode == 0:
                        envs = []
                        for line in result.stdout.split('\n'):
                            # Skip comments and empty lines
                            if line.strip() and not line.startswith('#'):
                                # Extract environment name (first word)
                                parts = line.split()
                                if parts:
                                    env_name = parts[0]
                                    if env_name and env_name != 'conda':
                                        envs.append(env_name)
                        if envs:
                            return envs
                except FileNotFoundError:
                    continue
                    
        except Exception as e:
            print(f"Error getting conda environments: {e}")
        
        return []

    def open_random_image(self):
        """Open a random image from the img/pets folder"""
        img_dir = get_resource_path("img") / "pets"
        if not img_dir.exists():
            print("img/pets folder not found")
            return
        
        # Get all image files
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.tiff']
        image_files = []
        for ext in image_extensions:
            image_files.extend(img_dir.glob(ext))
            image_files.extend(img_dir.glob(ext.upper()))
        
        if not image_files:
            print("No images found in img folder")
            return
        
        # Select random image
        random_image = random.choice(image_files)
        
        # Open in default image viewer
        try:
            os.startfile(str(random_image))
        except Exception as e:
            print(f"Error opening image: {e}")
    
    def _show_random_button(self, event):
        """Show the random image button on hover"""
        self.random_img_button.configure(
            fg_color=["#4CAF50", "#388E3C"],  # Green
            text_color=["white", "white"]
        )
    
    def _hide_random_button(self, event):
        """Hide the random image button when not hovering"""
        self.random_img_button.configure(
            fg_color=["#F9F9FA", "#2B2B2B"],  # Match background
            text_color=["#F9F9FA", "#2B2B2B"]  # Match background
        )
    
    def get_script_docstring(self, script_name):
        """Extract the module-level docstring from a Python script"""
        script_path = get_resource_path(script_name)
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to extract docstring using ast module for reliable parsing
            import ast
            try:
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)
                if docstring:
                    return docstring.strip()
            except:
                pass
            
            return "No documentation available for this script."
        except Exception as e:
            return f"Error reading script documentation: {e}"

    def show_documentation_window(self):
        """Display script documentation in an overlay within the main window"""
        script_name = self.script_dropdown.get()
        if script_name == "No scripts found":
            return
        
        docstring = self.get_script_docstring(script_name)
        
        # Create overlay frame (semi-transparent background)
        self.doc_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.doc_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.doc_overlay.bind("<Button-1>", lambda e: self.close_documentation())
        
        # Create documentation frame (centered)
        doc_frame = ctk.CTkFrame(
            self.doc_overlay,
            width=600,
            height=450,
            corner_radius=10
        )
        doc_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on doc_frame from closing the overlay
        doc_frame.bind("<Button-1>", lambda e: "break")
        
        # Add title label
        title_label = ctk.CTkLabel(
            doc_frame,
            text=f"Documentation for {script_name}",
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=15)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add textbox with docstring
        doc_textbox = ctk.CTkTextbox(
            doc_frame,
            width=560,
            height=330,
            font=("Segoe UI", 12)
        )
        doc_textbox.pack(pady=10, padx=20)
        doc_textbox.insert("1.0", docstring)
        doc_textbox.configure(state="disabled")  # Make read-only
        doc_textbox.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            doc_frame,
            text="Close",
            command=self.close_documentation,
            width=100,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        close_button.pack(pady=10)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def close_documentation(self):
        """Close the documentation overlay"""
        if hasattr(self, 'doc_overlay'):
            self.doc_overlay.destroy()
            del self.doc_overlay
    
    def show_expanded_output(self):
        """Show output in an expanded pop-out window"""
        output_content = self.output_textbox.get("1.0", "end-1c")
        if not output_content.strip():
            output_content = "(No output yet)"
        
        # Create separate window instead of overlay
        output_window = ctk.CTkToplevel(self)
        output_window.title("Script Output (Expanded)")
        output_window.geometry("800x600")
        
        # Position window to the right of main window
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        
        # Place popup to the right of main window with 20px gap
        new_x = main_x + main_width + 20
        new_y = main_y
        output_window.geometry(f"800x600+{new_x}+{new_y}")
        
        # Store reference to window so we can detect when it's closed
        self.expanded_output_window = output_window
        output_window.protocol("WM_DELETE_WINDOW", self._on_expanded_output_close)
        
        # Add title label
        title_label = ctk.CTkLabel(
            output_window,
            text="Script Output (Expanded)",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=15)
        
        # Add textbox with output
        output_textbox = ctk.CTkTextbox(
            output_window,
            width=760,
            height=480,
            font=("Consolas", 11)
        )
        output_textbox.pack(pady=10, padx=20)
        output_textbox.insert("1.0", output_content)
        
        # Store reference to expanded textbox for live updates
        self.expanded_output_textbox = output_textbox
        
        # Store output for copying
        self.current_expanded_output = output_content
        
        # Button frame
        button_frame = ctk.CTkFrame(output_window, fg_color="transparent")
        button_frame.pack(pady=15)
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy Output",
            command=self._copy_expanded_output,
            width=150,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        copy_button.pack(side="left", padx=5)
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._on_expanded_output_close,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        close_button.pack(side="left", padx=5)
    
    def _on_expanded_output_close(self):
        """Handle closing of expanded output window"""
        if hasattr(self, 'expanded_output_window'):
            self.expanded_output_window.destroy()
            del self.expanded_output_window
        if hasattr(self, 'expanded_output_textbox'):
            del self.expanded_output_textbox
    
    def _copy_expanded_output(self):
        """Copy the expanded output to clipboard"""
        if hasattr(self, 'current_expanded_output'):
            self.clipboard_clear()
            self.clipboard_append(self.current_expanded_output)
            self.update()
            print("Output copied to clipboard")

    def get_config_filename(self, script_name):
        """Determine config filename from script name"""
        # Remove .py extension and add _config.yml
        base_name = script_name.rsplit('.py', 1)[0]
        config_filename = f"{base_name}_config.yml"
        return config_filename

    def on_script_selected(self, script_name):
        """Handle script selection - load corresponding config and update button"""
        # Update button text if button exists
        if hasattr(self, 'wait_button'):
            self.wait_button.configure(text=f"Run {script_name}")
        
        # Determine config file
        config_filename = self.get_config_filename(script_name)
        config_path = get_writable_path(config_filename)
        
        # Create config file if it doesn't exist
        if not config_path.exists():
            # First try to copy from bundled resources (if running as exe)
            bundled_config = get_resource_path(config_filename)
            if bundled_config.exists() and bundled_config != config_path:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bundled_config, config_path)
            else:
                # Create default config
                default_data = {'folder': None, 'model_path': None, 'out_dir': None}
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    yaml.dump(default_data, f, default_flow_style=False)
        
        # Store current config file
        self.current_config_file = config_filename
        
        # Load the config
        self.load_config_and_rebuild(config_filename)

    def load_config_and_rebuild(self, config_filename):
        """Load config file and rebuild the drag/drop fields dynamically"""
        config_path = get_writable_path(config_filename)
        
        # Clear existing fields
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.field_entries.clear()
        
        # Load config
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config: {e}")
            config_data = {}
        
        # Create fields dynamically based on config keys
        for key, value in config_data.items():
            # Create label
            label = ctk.CTkLabel(self.scroll_frame, text=f"{key.replace('_', ' ').title()}:", font=self.label_font)
            label.pack(pady=(10, 5))
            
            # Create entry
            entry = ctk.CTkEntry(
                self.scroll_frame,
                placeholder_text=f"Drag {key} here",
                height=40,
                font=self.entry_font
            )
            entry.pack(pady=5, fill="x", padx=10)
            
            # Set existing value if any
            if value:
                entry.insert(0, str(value))
            
            # Enable drag and drop
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind("<<Drop>>", lambda e, k=key: self.drop(e, k))
            
            # Bind change detection to reset save button color
            entry.bind("<KeyRelease>", self._on_field_change)
            
            # Store reference
            self.field_entries[key] = entry

    def drop(self, event, field_name):
        file_path = event.data.strip("{}")  # handles spaces in paths
        
        if field_name in self.field_entries:
            entry = self.field_entries[field_name]
            entry.delete(0, "end")
            entry.insert(0, file_path)
            print(f"{field_name}:", file_path)
            # Reset save button color when field changes
            self._reset_save_button_color()
    
    def _on_field_change(self, event=None):
        """Reset save button color when any field changes"""
        self._reset_save_button_color()
    
    def _reset_save_button_color(self):
        """Reset save button to default blue color"""
        self.save_button.configure(
            fg_color=["#3B8ED0", "#1F6AA5"],  # Default blue
            hover_color=["#36719F", "#144870"]  # Default blue hover
        )

    def clear_fields(self):
        """Clear all entry fields"""
        for entry in self.field_entries.values():
            entry.delete(0, "end")
        print("All fields cleared")
        # Reset save button color when fields are cleared
        self._reset_save_button_color()

    def save_config(self):
        # Get values from all dynamic entry widgets
        config_data = {}
        for key, entry in self.field_entries.items():
            value = entry.get()
            config_data[key] = value if value else None
        
        config_filename = self.current_config_file
        if not config_filename:
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "Error: No config file selected\n")
            return
            
        config_path = get_writable_path(config_filename)
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            print(f"Configuration saved to {config_path}")
            print(f"Saved values: {config_data}")
            
            # Read back and display the saved config
            with open(config_path, 'r') as f:
                config_contents = f.read()
            
            # Display in output textbox
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "Configuration saved successfully!\n\n")
            self.output_textbox.insert("end", f"Contents of {config_filename}:\n")
            self.output_textbox.insert("end", "-" * 40 + "\n")
            self.output_textbox.insert("end", config_contents)
            self.output_textbox.insert("end", "-" * 40 + "\n")
            
            # Change save button to green to indicate successful save
            self.save_button.configure(
                fg_color=["#4CAF50", "#388E3C"],  # Green color
                hover_color=["#66BB6A", "#43A047"]  # Lighter green hover
            )
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", f"Error saving configuration: {e}\n")
    
    def _check_values_match(self):
        """Check if GUI values match the saved yml values"""
        if not self.current_config_file:
            return True
        
        config_path = get_writable_path(self.current_config_file)
        try:
            with open(config_path, 'r') as f:
                saved_values = yaml.safe_load(f) or {}
        except:
            return True  # If can't read file, allow to proceed
        
        # Get current GUI values
        gui_values = {}
        for key, entry in self.field_entries.items():
            value = entry.get()
            gui_values[key] = value if value else None
        
        # Compare values
        return gui_values == saved_values
    
    def _show_mismatch_warning(self):
        """Show warning popup when GUI values don't match yml values"""
        # Get saved and GUI values
        config_path = get_writable_path(self.current_config_file)
        with open(config_path, 'r') as f:
            saved_values = yaml.safe_load(f) or {}
        
        gui_values = {}
        for key, entry in self.field_entries.items():
            value = entry.get()
            gui_values[key] = value if value else None
        
        # Build comparison message with prominent confirmation text
        message = "⚠️ CONFIGURATION MISMATCH DETECTED ⚠️\n\n"
        message += "="*60 + "\n"
        message += "CONFIRM YOU WANT TO RUN PROCESS WITH:\n"
        message += "="*60 + "\n\n"
        
        # Show YAML (saved) values first
        message += "📄 SAVED YAML VALUES:\n"
        message += "-"*60 + "\n"
        for key in sorted(saved_values.keys()):
            saved_val = saved_values.get(key, "(not set)")
            message += f"  {key}: {saved_val}\n"
        
        message += "\n" + "="*60 + "\n"
        message += "COMPARISON WITH CURRENT GUI VALUES:\n"
        message += "="*60 + "\n\n"
        
        all_keys = set(list(saved_values.keys()) + list(gui_values.keys()))
        for key in sorted(all_keys):
            saved_val = saved_values.get(key, "(not set)")
            gui_val = gui_values.get(key, "(not set)")
            
            message += f"{key}:\n"
            message += f"  Saved in YML:  {saved_val}\n"
            message += f"  Current in GUI: {gui_val}\n"
            if saved_val != gui_val:
                message += f"  >>> MISMATCH <<<\n"
            message += "\n"
        
        message += "\n⚠️  Click 'Save & Run' to use the current GUI values.\n"
        message += "⚠️  Or manually save your configuration before running.\n"
        
        # Create overlay frame (orange semi-transparent background)
        self.warning_overlay = ctk.CTkFrame(
            self,
            fg_color=("#FFE0B2", "#E65100"),  # Light orange / Dark orange
            bg_color="transparent"
        )
        self.warning_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.warning_overlay.bind("<Button-1>", lambda e: self._close_warning_popup())
        
        # Create warning frame (centered)
        warning_frame = ctk.CTkFrame(
            self.warning_overlay,
            width=700,
            height=500,
            corner_radius=10,
            fg_color=("#FFF3E0", "#F57C00")  # Light orange / Orange
        )
        warning_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on warning_frame from closing the overlay
        warning_frame.bind("<Button-1>", lambda e: "break")
        
        # Add warning icon and title
        title_label = ctk.CTkLabel(
            warning_frame,
            text="⚠️ CONFIGURATION MISMATCH ⚠️",
            font=("Segoe UI", 18, "bold"),
            text_color=("#E65100", "#FFF3E0")  # Dark orange / Light orange
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add message textbox
        warning_textbox = ctk.CTkTextbox(
            warning_frame,
            width=660,
            height=330,
            font=("Segoe UI", 10),
            fg_color=("white", "#FF6F00"),
            text_color=("#E65100", "#FFF3E0")
        )
        warning_textbox.pack(pady=10, padx=20)
        warning_textbox.insert("1.0", message)
        warning_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store message for copying
        self.current_warning_message = message
        
        # Button frame
        button_frame = ctk.CTkFrame(warning_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add save and run button
        save_button = ctk.CTkButton(
            button_frame,
            text="💾 Save & Run",
            command=self._save_and_run,
            width=180,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#4CAF50", "#388E3C"),
            hover_color=("#66BB6A", "#43A047")
        )
        save_button.pack(side="left", padx=5)
        save_button.bind("<Button-1>", lambda e: "break")
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy Details",
            command=self._copy_warning_to_clipboard,
            width=150,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#FF9800", "#F57C00"),
            hover_color=("#FFB74D", "#FB8C00")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_warning_popup,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#FF6F00", "#E65100"),
            hover_color=("#FB8C00", "#BF360C")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_warning_popup(self):
        """Close the warning popup overlay"""
        if hasattr(self, 'warning_overlay'):
            self.warning_overlay.destroy()
            del self.warning_overlay
    
    def _save_and_run(self):
        """Save configuration, close warning popup, and run the script"""
        self.save_config()
        self._close_warning_popup()
        # Now run the script (skip validation since we just saved)
        self._proceed_with_run()
    
    def _copy_warning_to_clipboard(self):
        """Copy the warning message to clipboard"""
        if hasattr(self, 'current_warning_message'):
            self.clipboard_clear()
            self.clipboard_append(self.current_warning_message)
            self.update()
            print("Warning details copied to clipboard")

    def run_wait_script(self):
        selected_script = self.script_dropdown.get()
        if selected_script == "No scripts found":
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "No scripts available to run\n")
            return
        
        # Prevent multiple simultaneous executions
        if self.script_is_running:
            self.output_textbox.insert("end", "\nA script is already running. Please wait...\n")
            return
        
        # Check if GUI values match saved yml values
        if not self._check_values_match():
            self._show_mismatch_warning()
            return
        
        self._proceed_with_run()
    
    def _proceed_with_run(self):
        """Execute the script (called after validation passes)"""
        selected_script = self.script_dropdown.get()
        
        # Set running state
        self.script_is_running = True
        self.current_process = None  # Will be set when subprocess starts
        
        # Update button to show running state
        self.wait_button.configure(
            text=f"⏳ Running {selected_script}...",
            fg_color=["#FF9800", "#F57C00"],  # Orange color for running
            state="disabled"
        )
        
        # Show stop button
        self.stop_button.pack(side="left", padx=5)
        
        # Store script context for error reporting
        self.current_script_name = selected_script
        self.script_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_conda_env = self.env_dropdown.get()  # Store conda environment
        self.current_command = None  # Will be set when subprocess starts
        
        # Read current config values
        self.current_config_values = {}
        if self.current_config_file:
            config_path = get_writable_path(self.current_config_file)
            try:
                with open(config_path, 'r') as f:
                    self.current_config_values = yaml.safe_load(f) or {}
            except:
                pass
            
        script_path = get_resource_path(selected_script)
        
        # Get config file path (if exists)
        config_file_path = None
        if self.current_config_file:
            config_file_path = str(get_writable_path(self.current_config_file))
        
        self.output_textbox.delete("1.0", "end")
        self.output_textbox.insert("1.0", f"Starting {selected_script}...\n")
        
        # Run in a separate thread to avoid blocking GUI
        thread = threading.Thread(target=self._execute_script, args=(script_path, config_file_path))
        thread.daemon = True
        thread.start()

    def _execute_script(self, script_path, config_file_path=None):
        try:
            # Get selected conda environment
            selected_env = self.env_dropdown.get()
            
            # Set environment variables for unbuffered output
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            # Build command with config file path argument if available
            script_args = f'--config "{config_file_path}"' if config_file_path else ''
            
            # Build command based on whether conda env is selected
            if selected_env and selected_env != "No conda environments found":
                # Use conda run to execute in selected environment
                # Use cmd /c to ensure proper output handling on Windows
                command = f'cmd /c conda run --no-capture-output -n {selected_env} python -u "{script_path}" {script_args}'
                self.after(0, self._update_output, f"Using conda environment: {selected_env}\n")
            else:
                # Use system Python - don't use shell for direct python execution
                command = [sys.executable, '-u', str(script_path)]
                if config_file_path:
                    command.extend(['--config', config_file_path])
            
            try:
                if isinstance(command, str):
                    # Shell command for conda
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=0,
                        shell=True,
                        env=env
                    )
                else:
                    # Direct command for system python
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=0,
                        env=env
                    )
            except FileNotFoundError as e:
                # If conda command fails, fall back to system Python
                if selected_env and selected_env != "No conda environments found":
                    self.after(0, self._update_output, f"Warning: Could not activate conda environment '{selected_env}', using system Python instead.\n")
                    command = [sys.executable, '-u', str(script_path)]
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=0,
                        env=env
                    )
                else:
                    raise
            
            # Store process reference for stop button
            self.current_process = process
            
            # Store command for execution details
            if isinstance(command, str):
                self.current_command = command
            else:
                self.current_command = ' '.join(str(c) for c in command)
            
            # Read output line by line
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.after(0, self._update_output, line)
                if process.poll() is not None:
                    # Process finished, read any remaining output
                    remaining = process.stdout.read()
                    if remaining:
                        self.after(0, self._update_output, remaining)
                    break
            
            process.wait()
            
            if process.returncode == 0:
                self.after(0, self._update_output, "\nScript completed successfully!\n")
                self.after(0, self._save_run_to_history, True)  # Save successful run
                self.after(0, self._set_button_success)
                self.after(0, self._restore_button_state)
                self.after(0, self._show_success_popup)
            else:
                stderr_output = process.stderr.read()
                self.after(0, self._update_output, f"\nError: {stderr_output}\n")
                self.after(0, self._save_run_to_history, False)  # Save failed run
                self.after(0, self._set_button_error)
                self.after(0, self._restore_button_state)
                self.after(0, lambda: self._show_error_popup(stderr_output, include_context=True))
                
        except Exception as e:
            error_msg = str(e)
            self.after(0, self._update_output, f"\nError running script: {e}\n")
            self.after(0, self._save_run_to_history, False)  # Save failed run
            self.after(0, self._set_button_error)
            self.after(0, self._restore_button_state)
            self.after(0, lambda: self._show_error_popup(error_msg, include_context=True))

    def _set_button_success(self):
        """Set button color to default (success state)"""
        self.wait_button.configure(fg_color=["#3B8ED0", "#1F6AA5"])  # Default blue

    def _set_button_error(self):
        """Set button color to red (error state)"""
        self.wait_button.configure(fg_color=["#D32F2F", "#B71C1C"])  # Red color
    
    def _restore_button_state(self):
        """Restore button to normal state after script execution"""
        self.script_is_running = False
        self.current_process = None
        selected_script = self.script_dropdown.get()
        self.wait_button.configure(
            text=f"Run {selected_script}",
            state="normal"
        )
        # Hide stop button
        self.stop_button.pack_forget()

    def stop_script(self):
        """Stop the currently running script"""
        if self.current_process and self.script_is_running:
            try:
                self.current_process.terminate()  # Try graceful termination first
                self.after(1000, self._force_kill_if_needed)  # Force kill after 1 second if still running
                self._update_output("\n⏹ Script termination requested...\n")
            except Exception as e:
                self._update_output(f"\nError stopping script: {e}\n")
    
    def _force_kill_if_needed(self):
        """Force kill the process if it didn't terminate gracefully"""
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.kill()
                self._update_output("\n⏹ Script forcefully terminated.\n")
            except:
                pass

    def _show_error_popup(self, error_message, include_context=False):
        """Display error popup overlay with red background"""
        # Build full error message with context
        full_message = error_message if error_message.strip() else "An unknown error occurred."
        
        if include_context:
            context_info = "\n" + "="*60 + "\n"
            context_info += "EXECUTION CONTEXT:\n"
            context_info += "="*60 + "\n"
            context_info += f"Script: {getattr(self, 'current_script_name', 'Unknown')}\n"
            context_info += f"Conda Environment: {getattr(self, 'current_conda_env', 'Unknown')}\n"
            context_info += f"Command: {getattr(self, 'current_command', 'Unknown')}\n"
            context_info += f"Started: {getattr(self, 'script_start_time', 'Unknown')}\n"
            context_info += f"\nConfig File ({getattr(self, 'current_config_file', 'Unknown')}):\n"
            context_info += "-"*60 + "\n"
            
            config_values = getattr(self, 'current_config_values', {})
            if config_values:
                for key, value in config_values.items():
                    context_info += f"  {key}: {value}\n"
            else:
                context_info += "  (No configuration values)\n"
            
            full_message = full_message + context_info
        # Create overlay frame (red semi-transparent background)
        self.error_overlay = ctk.CTkFrame(
            self,
            fg_color=("#FFCDD2", "#B71C1C"),  # Light red / Dark red
            bg_color="transparent"
        )
        self.error_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.error_overlay.bind("<Button-1>", lambda e: self._close_error_popup())
        
        # Create error frame (centered)
        error_frame = ctk.CTkFrame(
            self.error_overlay,
            width=600,
            height=450,
            corner_radius=10,
            fg_color=("#FFEBEE", "#C62828")  # Light red / Red
        )
        error_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on error_frame from closing the overlay
        error_frame.bind("<Button-1>", lambda e: "break")
        
        # Add warning icon and title
        title_label = ctk.CTkLabel(
            error_frame,
            text="⚠️ SCRIPT FAILED ⚠️",
            font=("Segoe UI", 18, "bold"),
            text_color=("#B71C1C", "#FFEBEE")  # Dark red / Light red
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add error message textbox
        error_textbox = ctk.CTkTextbox(
            error_frame,
            width=560,
            height=250,
            font=("Segoe UI", 10),
            fg_color=("white", "#D32F2F"),
            text_color=("#B71C1C", "#FFEBEE")
        )
        error_textbox.pack(pady=10, padx=20)
        error_textbox.insert("1.0", full_message)
        # Keep in normal state to allow text selection and copying
        error_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store error message for copying
        self.current_error_message = full_message
        
        # Button frame for Copy and Close buttons
        button_frame = ctk.CTkFrame(error_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_error_to_clipboard,
            width=180,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#EF6C00", "#E65100"),
            hover_color=("#E65100", "#BF360C")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_error_popup,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#D32F2F", "#B71C1C"),
            hover_color=("#C62828", "#8B0000")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_error_popup(self):
        """Close the error popup overlay"""
        if hasattr(self, 'error_overlay'):
            self.error_overlay.destroy()
            del self.error_overlay
    
    def _show_success_popup(self):
        """Display success popup overlay with green background"""
        # Build context info
        context_info = "="*60 + "\n"
        context_info += "EXECUTION DETAILS:\n"
        context_info += "="*60 + "\n"
        context_info += f"Script: {getattr(self, 'current_script_name', 'Unknown')}\n"
        context_info += f"Conda Environment: {getattr(self, 'current_conda_env', 'Unknown')}\n"
        context_info += f"Command: {getattr(self, 'current_command', 'Unknown')}\n"
        context_info += f"Started: {getattr(self, 'script_start_time', 'Unknown')}\n"
        context_info += f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        context_info += f"\nConfig File ({getattr(self, 'current_config_file', 'Unknown')}):\n"
        context_info += "-"*60 + "\n"
        
        config_values = getattr(self, 'current_config_values', {})
        if config_values:
            for key, value in config_values.items():
                context_info += f"  {key}: {value}\n"
        else:
            context_info += "  (No configuration values)\n"
        
        # Create overlay frame (green semi-transparent background)
        self.success_overlay = ctk.CTkFrame(
            self,
            fg_color=("#C8E6C9", "#2E7D32"),  # Light green / Dark green
            bg_color="transparent"
        )
        self.success_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.success_overlay.bind("<Button-1>", lambda e: self._close_success_popup())
        
        # Create success frame (centered)
        success_frame = ctk.CTkFrame(
            self.success_overlay,
            width=600,
            height=450,
            corner_radius=10,
            fg_color=("#E8F5E9", "#388E3C")  # Light green / Green
        )
        success_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on success_frame from closing the overlay
        success_frame.bind("<Button-1>", lambda e: "break")
        
        # Add success icon and title
        title_label = ctk.CTkLabel(
            success_frame,
            text="✓ SCRIPT COMPLETED SUCCESSFULLY ✓",
            font=("Segoe UI", 18, "bold"),
            text_color=("#1B5E20", "#E8F5E9")  # Dark green / Light green
        )
        title_label.pack(pady=20)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add context textbox
        context_textbox = ctk.CTkTextbox(
            success_frame,
            width=560,
            height=250,
            font=("Segoe UI", 10),
            fg_color=("white", "#2E7D32"),
            text_color=("#1B5E20", "#E8F5E9")
        )
        context_textbox.pack(pady=10, padx=20)
        context_textbox.insert("1.0", context_info)
        context_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store context for copying
        self.current_success_context = context_info
        
        # Button frame for Copy and Close buttons
        button_frame = ctk.CTkFrame(success_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Add copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy Details",
            command=self._copy_success_to_clipboard,
            width=150,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#66BB6A", "#43A047"),
            hover_color=("#4CAF50", "#388E3C")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Add close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_success_popup,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#388E3C", "#2E7D32"),
            hover_color=("#2E7D32", "#1B5E20")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_success_popup(self):
        """Close the success popup overlay"""
        if hasattr(self, 'success_overlay'):
            self.success_overlay.destroy()
            del self.success_overlay
    
    def _copy_success_to_clipboard(self):
        """Copy the success context to clipboard"""
        if hasattr(self, 'current_success_context'):
            self.clipboard_clear()
            self.clipboard_append(self.current_success_context)
            self.update()  # Required to finalize clipboard content
            print("Success details copied to clipboard")
    
    def _copy_error_to_clipboard(self):
        """Copy the error message to clipboard"""
        if hasattr(self, 'current_error_message'):
            self.clipboard_clear()
            self.clipboard_append(self.current_error_message)
            self.update()  # Required to finalize clipboard content
            print("Error message copied to clipboard")

    def _update_output(self, text):
        self.output_textbox.insert("end", text)
        self.output_textbox.see("end")
        
        # Also update expanded output window if it's open
        if hasattr(self, 'expanded_output_textbox'):
            try:
                self.expanded_output_textbox.insert("end", text)
                self.expanded_output_textbox.see("end")
            except:
                # Window might have been closed
                if hasattr(self, 'expanded_output_textbox'):
                    del self.expanded_output_textbox
    
    def _ensure_history_file(self):
        """Ensure history file exists"""
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump([], f)
    
    def _save_run_to_history(self, success):
        """Save current run configuration and results to history"""
        try:
            # Read existing history
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            # Create new history entry
            entry = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'script': getattr(self, 'current_script_name', 'Unknown'),
                'conda_env': getattr(self, 'current_conda_env', 'Unknown'),
                'config_file': getattr(self, 'current_config_file', 'Unknown'),
                'config_values': getattr(self, 'current_config_values', {}),
                'success': success,
                'command': getattr(self, 'current_command', 'Unknown')
            }
            
            # Add to beginning of history
            history.insert(0, entry)
            
            # Keep only last 100 runs
            history = history[:100]
            
            # Save back to file
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            print(f"Error saving to history: {e}")
    
    def show_history_browser(self):
        """Display history browser window"""
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
        
        if not history:
            # Show message if no history
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", "No run history available yet.\n")
            return
        
        # Create overlay frame
        self.history_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.history_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Bind click on overlay to close it
        self.history_overlay.bind("<Button-1>", lambda e: self._close_history_browser())
        
        # Create history frame (centered, larger)
        history_frame = ctk.CTkFrame(
            self.history_overlay,
            width=800,
            height=600,
            corner_radius=10
        )
        history_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Prevent clicks on history_frame from closing the overlay
        history_frame.bind("<Button-1>", lambda e: "break")
        
        # Add title label
        title_label = ctk.CTkLabel(
            history_frame,
            text="📜 Run History",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(pady=15)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Add scrollable frame for history items
        scroll_frame = ctk.CTkScrollableFrame(
            history_frame,
            width=760,
            height=450
        )
        scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)
        scroll_frame.bind("<Button-1>", lambda e: "break")
        
        # Display each history entry
        for i, entry in enumerate(history):
            self._create_history_entry_widget(scroll_frame, entry, i)
        
        # Add close button
        close_button = ctk.CTkButton(
            history_frame,
            text="Close",
            command=self._close_history_browser,
            width=120,
            height=40,
            font=("Segoe UI", 12, "bold")
        )
        close_button.pack(pady=15)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _create_history_entry_widget(self, parent, entry, index):
        """Create a widget for a single history entry"""
        # Determine colors based on success/failure
        if entry.get('success', False):
            bg_color = ("#E8F5E9", "#1B5E20")  # Green
            hover_color = ("#C8E6C9", "#2E7D32")
            status_icon = "✓"
        else:
            bg_color = ("#FFEBEE", "#B71C1C")  # Red
            hover_color = ("#FFCDD2", "#C62828")
            status_icon = "✗"
        
        # Create frame for this entry
        entry_frame = ctk.CTkFrame(
            parent,
            fg_color=bg_color,
            corner_radius=8
        )
        entry_frame.pack(pady=5, padx=5, fill="x")
        entry_frame.bind("<Button-1>", lambda e: "break")
        
        # Create inner frame for better layout
        inner_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
        inner_frame.pack(pady=10, padx=10, fill="x")
        inner_frame.bind("<Button-1>", lambda e: "break")
        
        # Header with timestamp and status
        header_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        header_frame.pack(fill="x")
        header_frame.bind("<Button-1>", lambda e: "break")
        
        timestamp_label = ctk.CTkLabel(
            header_frame,
            text=f"{status_icon} {entry.get('timestamp', 'Unknown')} - {entry.get('script', 'Unknown')}",
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        timestamp_label.pack(side="left")
        timestamp_label.bind("<Button-1>", lambda e: "break")
        
        # Environment and config info
        info_label = ctk.CTkLabel(
            inner_frame,
            text=f"Environment: {entry.get('conda_env', 'Unknown')} | Config: {entry.get('config_file', 'Unknown')}",
            font=("Segoe UI", 10),
            anchor="w"
        )
        info_label.pack(fill="x", pady=(5, 0))
        info_label.bind("<Button-1>", lambda e: "break")
        
        # Configuration values
        config_values = entry.get('config_values', {})
        if config_values:
            config_text = "Settings: "
            config_items = [f"{k}={v}" for k, v in list(config_values.items())[:3]]
            config_text += ", ".join(config_items)
            if len(config_values) > 3:
                config_text += f" (+{len(config_values)-3} more)"
            
            config_label = ctk.CTkLabel(
                inner_frame,
                text=config_text,
                font=("Segoe UI", 9),
                anchor="w",
                wraplength=700
            )
            config_label.pack(fill="x", pady=(2, 0))
            config_label.bind("<Button-1>", lambda e: "break")
        
        # Button frame
        button_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        button_frame.pack(pady=(10, 0))
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Load button
        load_button = ctk.CTkButton(
            button_frame,
            text="📥 Load Settings",
            command=lambda: self._load_history_entry(entry),
            width=140,
            height=32,
            font=("Segoe UI", 10, "bold"),
            fg_color=("#2196F3", "#1976D2"),
            hover_color=("#42A5F5", "#1565C0")
        )
        load_button.pack(side="left", padx=5)
        load_button.bind("<Button-1>", lambda e: "break")
        
        # View details button
        details_button = ctk.CTkButton(
            button_frame,
            text="📋 View Details",
            command=lambda: self._show_history_details(entry),
            width=140,
            height=32,
            font=("Segoe UI", 10, "bold"),
            fg_color=("#757575", "#616161"),
            hover_color=("#9E9E9E", "#757575")
        )
        details_button.pack(side="left", padx=5)
        details_button.bind("<Button-1>", lambda e: "break")
    
    def _load_history_entry(self, entry):
        """Load configuration from a history entry"""
        try:
            # Switch to the script from history
            script_name = entry.get('script', '')
            if script_name and script_name in self.script_dropdown.cget('values'):
                self.script_dropdown.set(script_name)
                self.on_script_selected(script_name)
            
            # Switch to the conda environment from history
            conda_env = entry.get('conda_env', '')
            if conda_env and conda_env in self.env_dropdown.cget('values'):
                self.env_dropdown.set(conda_env)
            
            # Load configuration values
            config_values = entry.get('config_values', {})
            for key, value in config_values.items():
                if key in self.field_entries:
                    self.field_entries[key].delete(0, "end")
                    if value:
                        self.field_entries[key].insert(0, str(value))
            
            # Close history browser
            self._close_history_browser()
            
            # Show confirmation message
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", f"✓ Loaded settings from {entry.get('timestamp', 'previous run')}\n\n")
            self.output_textbox.insert("end", "Configuration loaded successfully!\n")
            self.output_textbox.insert("end", "-" * 40 + "\n")
            for key, value in config_values.items():
                self.output_textbox.insert("end", f"{key}: {value}\n")
            
            # Reset save button color since values changed
            self._reset_save_button_color()
            
        except Exception as e:
            print(f"Error loading history entry: {e}")
            self.output_textbox.delete("1.0", "end")
            self.output_textbox.insert("1.0", f"Error loading history entry: {e}\n")
    
    def _show_history_details(self, entry):
        """Show detailed information about a history entry"""
        details = "="*60 + "\n"
        details += "RUN DETAILS\n"
        details += "="*60 + "\n"
        details += f"Timestamp: {entry.get('timestamp', 'Unknown')}\n"
        details += f"Script: {entry.get('script', 'Unknown')}\n"
        details += f"Conda Environment: {entry.get('conda_env', 'Unknown')}\n"
        details += f"Config File: {entry.get('config_file', 'Unknown')}\n"
        details += f"Status: {'✓ Success' if entry.get('success', False) else '✗ Failed'}\n"
        details += f"Command: {entry.get('command', 'Unknown')}\n"
        details += "\nConfiguration Values:\n"
        details += "-"*60 + "\n"
        
        config_values = entry.get('config_values', {})
        if config_values:
            for key, value in config_values.items():
                details += f"  {key}: {value}\n"
        else:
            details += "  (No configuration values)\n"
        
        # Create overlay for details
        self.details_overlay = ctk.CTkFrame(
            self,
            fg_color=("gray80", "gray20"),
            bg_color="transparent"
        )
        self.details_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.details_overlay.bind("<Button-1>", lambda e: self._close_details_overlay())
        
        # Create details frame
        details_frame = ctk.CTkFrame(
            self.details_overlay,
            width=600,
            height=500,
            corner_radius=10
        )
        details_frame.place(relx=0.5, rely=0.5, anchor="center")
        details_frame.bind("<Button-1>", lambda e: "break")
        
        # Title
        title_label = ctk.CTkLabel(
            details_frame,
            text="📋 Run Details",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=15)
        title_label.bind("<Button-1>", lambda e: "break")
        
        # Details textbox
        details_textbox = ctk.CTkTextbox(
            details_frame,
            width=560,
            height=350,
            font=("Segoe UI", 11)
        )
        details_textbox.pack(pady=10, padx=20)
        details_textbox.insert("1.0", details)
        details_textbox.bind("<Button-1>", lambda e: "break")
        
        # Store details for copying
        self.current_details = details
        
        # Button frame
        button_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        button_frame.bind("<Button-1>", lambda e: "break")
        
        # Copy button
        copy_button = ctk.CTkButton(
            button_frame,
            text="📋 Copy",
            command=self._copy_details_to_clipboard,
            width=120,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        copy_button.pack(side="left", padx=5)
        copy_button.bind("<Button-1>", lambda e: "break")
        
        # Close button
        close_button = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self._close_details_overlay,
            width=120,
            height=35,
            font=("Segoe UI", 11, "bold")
        )
        close_button.pack(side="left", padx=5)
        close_button.bind("<Button-1>", lambda e: "break")
    
    def _close_details_overlay(self):
        """Close the details overlay"""
        if hasattr(self, 'details_overlay'):
            self.details_overlay.destroy()
            del self.details_overlay
    
    def _copy_details_to_clipboard(self):
        """Copy details to clipboard"""
        if hasattr(self, 'current_details'):
            self.clipboard_clear()
            self.clipboard_append(self.current_details)
            self.update()
            print("Details copied to clipboard")
    
    def _close_history_browser(self):
        """Close the history browser overlay"""
        if hasattr(self, 'history_overlay'):
            self.history_overlay.destroy()
            del self.history_overlay


app = App()
app.mainloop()
