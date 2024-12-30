import os
import tkinter as tk
from tkinter import ttk
import sys
import threading
import sv_ttk
import darkdetect
from notifypy import Notify
from PIL import Image, ImageTk

from scraper_backend import run


class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, string):
        self.widget.insert(tk.END, string)
        self.widget.see(tk.END)  # Auto-scroll to the end

    def flush(self):
        pass  # Required for compatibility with some libraries


def handle_button_click(icon_path, filters):
    username = str(username_var.get())
    password = str(password_var.get())
    course_url = str(url_var.get())
    converted_to_pdf = str(converted_var.get())

    # Clear the message display area
    message_display.delete(1.0, tk.END)

    # Disable the button
    global download_button
    download_button.state(['disabled'])

    # Perform some processing and print messages to the GUI
    def download():
        try:
            run(username, password, course_url, converted_to_pdf, filters)
            notification = Notify()
            notification.title = "StudySnatcher"
            notification.message = "All files downloaded"
            notification.icon = icon_path
            notification.send()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Re-enable the button after the process completes
            global download_button
            download_button.state(['!disabled'])

    threading.Thread(target=download).start()


def open_filter_dialog(start_filters, callback):
    """
    Opens a dialog to configure filters and returns them through a callback.

    :param callback: A function that will receive the filters as an argument.
    """
    def save_filters():
        """
        Saves the configured filters and calls the callback with the filter dictionary.
        """
        filters = {}
        for attribute, entry in input_fields.items():
            value = entry.get() if isinstance(
                entry, tk.Entry) else entry_var[attribute].get()
            if value != "":
                # Convert to appropriate type if necessary
                if attribute_types[attribute] == int:
                    try:
                        value = int(value)
                    except ValueError:
                        value = None  # Skip invalid values
                elif attribute_types[attribute] == float:
                    try:
                        value = float(value)
                    except ValueError:
                        value = None  # Skip invalid values
                filters[attribute] = value

        filter_dialog.destroy()
        callback(filters)

    def load_filters(start_filters):
        """
        Loads the provided filter values into the corresponding fields in the dialog.
        :param start_filters: A dictionary containing the initial filter values to populate.
        """
        for attribute, value in start_filters.items():
            if attribute in input_fields:
                if isinstance(input_fields[attribute], tk.Entry):
                    input_fields[attribute].delete(
                        0, tk.END)  # Clear existing value
                    if value is not None:
                        # Populate with the provided value
                        input_fields[attribute].insert(0, str(value))
                elif attribute in entry_var:
                    # Set checkbox or other variable values
                    entry_var[attribute].set(value)

    def reset_filters():
        """
        Clears all input fields in the dialog.
        """
        for attribute in input_fields:
            if isinstance(input_fields[attribute], tk.Entry):
                input_fields[attribute].delete(0, tk.END)
            elif attribute in entry_var:
                entry_var[attribute].set(False)

    # Available filter attributes (example schema with nested attributes)
    attribute_types = {
        "link": str,
        "file_id": int,
        # "file_name": str,
        # "description": str,
        # "uploaded": str,
        # "time": str,
        # "course_id": int,
        # "course_name": str,
        # "course_link": str,
        # "university_id": int,
        # "university_name": str,
        "semester": str,
        "semester_id": int,
        "professor": str,
        # "has_ai_content": bool,
        # "flashcard_set_id": int,  # None or int, handled as int for filtering
        # "study_list_id": int,    # None or int, handled as int for filtering
        # "visibility": int,
        "file_type": int,
        # "type_name": str,
        # "is_owner": bool,
        # "is_followed": bool,
        # "is_infected": bool,
        # "preview_link": str,
        # "uservote": bool,
        "user_star_vote": int,
        "avg_star_score": int,
        "upvotes": int,
        "downvotes": int,
        "rating": int,
        "downloads": int,
        # "questions": int,
        "user_data.name": str,
        "user_data.link": str,
        "user_data.id": int,              # None or int, handled as int for filtering
        "user_data.identity_id": int,     # None or int, handled as int for filtering
        # "user_data.picture": str,
        # "user_data.profile_picture": str,
        # "user_data.karma_points": int,    # None or int, handled as int for filtering
        # "user_data.gamify_avatar_url": str,  # None or str, handled as str for filtering
        # "user_data.time": str,
        # "user_data.is_deleted": bool
    }

    # Create the filter dialog
    filter_dialog = tk.Toplevel(root)
    filter_dialog.title("Set Filters")

    # Create a frame for the scrollable area
    scrollable_frame = ttk.Frame(filter_dialog)
    scrollable_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    # Create a canvas and scrollbar for the filters
    # Increased width of the canvas
    canvas = tk.Canvas(scrollable_frame, width=600, height=800)
    scrollbar = ttk.Scrollbar(
        scrollable_frame, orient="vertical", command=canvas.yview)
    scrollable_content = ttk.Frame(canvas)

    # Configure canvas and scrollbar
    canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Grid the canvas and scrollbar
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Configure scrollable area resizing
    scrollable_frame.grid_rowconfigure(0, weight=1)
    scrollable_frame.grid_columnconfigure(0, weight=1)

    # Bind the canvas to resize with its contents
    scrollable_content.bind("<Configure>", lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")))

    input_fields = {}
    entry_var = {}

    # Track current parent to add subheadings
    current_parent = None

    row_index = 0  # Track row index dynamically

    # Add filters to the scrollable content
    for attribute, attr_type in attribute_types.items():
        # Determine the parent name for subheadings
        parent_name = attribute.split(".")[0] if "." in attribute else None

        # Add a subheading if the parent changes
        if parent_name and parent_name != current_parent:
            current_parent = parent_name
            ttk.Label(scrollable_content, text=current_parent).grid(
                row=row_index, column=0, columnspan=2, padx=20, pady=(10, 5), sticky=tk.W
            )
            row_index += 1

        # Indent nested attributes for clarity
        nested_depth = attribute.count(".")
        padding = 20 + nested_depth * 40  # Indent by 40 pixels per level of nesting

        # Adjust entry width based on nesting depth
        entry_width = max(20 - nested_depth * 4, 5)  # Minimum width of 5

        # Add label and input field
        ttk.Label(scrollable_content, text=attribute).grid(
            row=row_index, column=0, padx=(padding, 20), pady=5, sticky=tk.W
        )

        # Define a validation command for numeric input
        def validate_numeric_input(new_value):
            """
            Validation function to allow only numeric input.

            :param new_value: The new value being entered in the Entry field.
            :return: True if the input is valid (numeric), False otherwise.
            """
            if new_value == "" or new_value.isdigit():  # Allow empty input or numeric input
                return True
            return False

        # Register the validation function with Tkinter
        vcmd = filter_dialog.register(validate_numeric_input)

        if attr_type == bool:
            # Checkbox for booleans
            entry_var[attribute] = tk.BooleanVar()
            ttk.Checkbutton(scrollable_content, variable=entry_var[attribute]).grid(
                row=row_index, column=1, padx=(padding, 20), pady=5, sticky=tk.W
            )
        elif attr_type in [int, float]:
            # Numeric entry for integers or floats
            entry_var[attribute] = tk.IntVar()
            input_fields[attribute] = ttk.Entry(
                scrollable_content,
                textvariable=entry_var[attribute],
                width=entry_width,
                validate='key',
                # Use validation command to restrict input
                validatecommand=(vcmd, '%P')
            )
            input_fields[attribute].grid(
                row=row_index, column=1, padx=(padding, 20), pady=5, sticky=tk.W
            )
        else:
            # Free text for strings
            entry_var[attribute] = tk.StringVar()
            input_fields[attribute] = ttk.Entry(
                scrollable_content, textvariable=entry_var[attribute], width=entry_width)
            input_fields[attribute].grid(row=row_index, column=1, padx=(
                padding, 20), pady=5, sticky=tk.W)

        row_index += 1

    reset_filters()
    load_filters(start_filters)

    # Create a frame for the buttons
    button_frame = ttk.Frame(filter_dialog)
    button_frame.grid(row=1, column=0, columnspan=2,
                      pady=(20, 10), sticky="ew")

    # Configure the columns in the button frame to expand equally
    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=1)

    # Add Save and Reset buttons inside the frame
    ttk.Button(button_frame, text="Save", command=save_filters).grid(
        row=0, column=0, padx=10, sticky="e")
    ttk.Button(button_frame, text="Reset", command=reset_filters).grid(
        row=0, column=1, padx=10, sticky="w")


if __name__ == "__main__":
    # Get path to app icon file
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    elif __file__:
        application_path = os.path.dirname(__file__)

    icon_path = os.path.join(application_path, 'icon.ico')

    # Create the main window
    root = tk.Tk()
    root.title("StudySnatcher")

    log = Image.open(icon_path)
    logo = ImageTk.PhotoImage(log)
    root.tk.call('wm', 'iconphoto', root._w, logo)

    # Create variables to store user inputs
    username_var = tk.StringVar()
    password_var = tk.StringVar()
    url_var = tk.StringVar()
    converted_var = tk.BooleanVar()

    # Create widgets with updated fonts
    ttk.Label(root, text="Username:").grid(
        row=0, column=0, padx=10, pady=5)
    ttk.Entry(root, textvariable=username_var).grid(
        row=0, column=1, padx=10, pady=5)

    ttk.Label(root, text="Password:").grid(
        row=1, column=0, padx=10, pady=5)
    ttk.Entry(root, textvariable=password_var, show="*").grid(
        row=1, column=1, padx=10, pady=5)

    ttk.Label(root, text="URL of StudyDrive course:").grid(
        row=2, column=0, padx=10, pady=5)
    ttk.Entry(root, textvariable=url_var).grid(
        row=2, column=1, padx=10, pady=5)

    ttk.Checkbutton(root, text="Convert all files to PDF", variable=converted_var, style="TCheckbutton").grid(
        row=3, column=0, columnspan=2, pady=5)

    lock = threading.Lock()

    global filters_var
    filters_var = {}

    def store_filters(filters):
        with lock:
            global filters_var
            filters_var = filters

    def open_dialog():
        with lock:
            global filters_var
            filters_local = filters_var
        open_filter_dialog(filters_local, store_filters)

    ttk.Button(root, text="Filter", command=open_dialog, style="TButton").grid(
        row=4, column=0, columnspan=2, pady=10)

    # Create the button and store a reference to it
    download_button = ttk.Button(
        root,
        text="Download",
        command=lambda: handle_button_click(icon_path, filters_var),
        style="TButton"
    )
    download_button.grid(row=5, column=0, columnspan=2,
                         pady=10)  # Call grid() separately

    # Text widget to display messages
    message_display = tk.Text(root, height=10, width=50)
    message_display.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

    # Redirect print output to the Text widget
    sys.stdout = TextRedirector(message_display)

    # Start the GUI main loop
    sv_ttk.set_theme(darkdetect.theme())
    root.mainloop()
