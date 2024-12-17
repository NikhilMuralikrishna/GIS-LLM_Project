import os
import customtkinter as ctk  # Using CustomTkinter for enhanced visuals
from tkinter import filedialog, messagebox
from PIL import Image, ImageEnhance
import openai
from LLM_Geo_kernel import Solution
import LLM_Geo_Constants as constants
import helper

# Function to browse for CSV file
def browse_csv():
    filename = filedialog.askopenfilename(title="Select CSV file", filetypes=[("CSV files", "*.csv")])
    csv_entry.delete(0, ctk.END)
    csv_entry.insert(0, filename)

# Function to browse for shapefile
def browse_shp():
    filename = filedialog.askopenfilename(title="Select Shapefile", filetypes=[("Shapefiles", "*.shp")])
    shp_entry.delete(0, ctk.END)
    shp_entry.insert(0, filename)

# Function to execute the geographic task
def execute_task():
    task_name = task_name_entry.get()  # Get dynamic task name from the user
    user_query = request_entry.get()  # User-defined task query from the GUI
    csv_file = csv_entry.get()
    shp_file = shp_entry.get()

    # Nullify columns if "None" button is clicked
    if none_clicked:
        task = f"{user_query}\nIgnore values that are 0."
        data_locations = [
            f"CSV: {csv_file}",
            f"Shapefile: {shp_file}"
        ]
        english_entry.delete(0, ctk.END)
        italian_entry.delete(0, ctk.END)
        csv_language_var.set(False)
        shp_language_var.set(False)
    else:
        csv_column = english_entry.get()
        shp_column = italian_entry.get()
        csv_language = "English" if not csv_language_var.get() else "Italian"
        shp_language = "English" if not shp_language_var.get() else "Italian"

        # Dynamic task description and data locations
        task = (f"{user_query}\n"
                f"Ignore values that are 0.\n"
                f"Columns of interest - CSV ({csv_language}): {csv_column}, "
                f"Shapefile ({shp_language}): {shp_column}")
        data_locations = [
            f"CSV: {csv_file} (column of interest: {csv_column})",
            f"Shapefile: {shp_file} (column of interest: {shp_column})"
        ]

    # Validation: Ensure all fields are filled unless "None" is clicked
    if not task_name or not user_query or not csv_file or not shp_file or (not none_clicked and (not csv_column or not shp_column)):
        messagebox.showerror("Error", "All fields are required, or click 'None' for columns of interest.")
        return

    # Create the save directory for outputs
    save_dir = os.path.join(os.getcwd(), task_name)
    os.makedirs(save_dir, exist_ok=True)

    # Initialize the Solution object
    selected_model = model_var.get()
    solution = Solution(task=task, task_name=task_name, save_dir=save_dir, data_locations=data_locations, model=selected_model)
    print("Prompt to get solution graph:\n")
    print(solution.direct_request_prompt)
    
    try:
        # Execute the task using the LLM and generated code
        response = solution.get_direct_request_LLM_response(review=True)
        exec_code = solution.execute_complete_program(code=solution.direct_request_code, try_cnt=10)
        if exec_code:
            messagebox.showinfo("Success", "Task executed successfully. Check the output directory.")
    except Exception as e:
        if "Failed to execute and debug the code within 10 times." in str(e):
            messagebox.showerror("Task Failed", "Task failed after 10 attempts.")
        else:
            messagebox.showerror("Error", f"An error occurred: {e}")

# Function to reset the GUI for a new task
def refresh_gui():
    global none_clicked
    task_name_entry.delete(0, ctk.END)
    request_entry.delete(0, ctk.END)
    csv_entry.delete(0, ctk.END)
    shp_entry.delete(0, ctk.END)
    italian_entry.delete(0, ctk.END)
    english_entry.delete(0, ctk.END)
    csv_language_var.set(False)
    shp_language_var.set(False)
    none_clicked = False
    none_button.configure(fg_color="blue")
    model_var.set("gpt-4o")  # Reset model to default
    print("GUI has been reset for a new task.")

# Function to toggle "None" button state
def toggle_none():
    global none_clicked
    none_clicked = not none_clicked
    none_button.configure(fg_color="lightblue" if none_clicked else "blue")
    if none_clicked:
        english_entry.delete(0, ctk.END)
        italian_entry.delete(0, ctk.END)
        csv_language_var.set(False)
        shp_language_var.set(False)

# Set up the main window
ctk.set_appearance_mode("Dark")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "dark-blue", "green"

root = ctk.CTk()
root.title("GeoGPT")
root.geometry("523x450")

# Font settings
label_font = ("Helvetica", 12, "bold")
entry_font = ("Helvetica", 12)
button_font = ("Helvetica", 12, "bold")

def apply_font(widget, font):
    widget.configure(font=font)

# Set up the background image with transparency
bg_image_path = r"E:\geo\LLM-Geo\LOGO.png"  # Replace with the path to your logo
bg_image = Image.open(bg_image_path)
bg_image = bg_image.resize((523, 450), Image.Resampling.LANCZOS)  # Resize to fit the window

# Reduce the visibility by adjusting the alpha/transparency
bg_image = bg_image.convert("RGBA")  # Ensure the image has an alpha channel
alpha = 0.3  # Set transparency level (0 is fully transparent, 1 is fully opaque)
bg_image = ImageEnhance.Brightness(bg_image).enhance(alpha)

# Convert the image to CTkImage for CustomTkinter
bg_image_tk = ctk.CTkImage(light_image=bg_image, size=(523, 450))

# Set the label with the semi-transparent background
background_label = ctk.CTkLabel(root, image=bg_image_tk, text="")
background_label.place(x=0, y=0, relwidth=1, relheight=1)

# Input for task name
task_name_label = ctk.CTkLabel(root, text="Task Name:")
apply_font(task_name_label, label_font)
task_name_label.grid(row=0, column=0, sticky='w', padx=10, pady=10)
task_name_entry = ctk.CTkEntry(root, width=400)
apply_font(task_name_entry, entry_font)
task_name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=10)

# Input for task request
request_label = ctk.CTkLabel(root, text="Your request:")
apply_font(request_label, label_font)
request_label.grid(row=1, column=0, sticky='w', padx=10, pady=10)
request_entry = ctk.CTkEntry(root, width=400)
apply_font(request_entry, entry_font)
request_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=10)

# Inputs for file locations
files_label = ctk.CTkLabel(root, text="Specify the location of all the CSV files and shapefiles:")
apply_font(files_label, label_font)
files_label.grid(row=2, column=0, columnspan=3, sticky='w', padx=10, pady=5)

csv_label = ctk.CTkLabel(root, text="CSV files:")
apply_font(csv_label, label_font)
csv_label.grid(row=3, column=0, sticky='w', padx=10)
csv_entry = ctk.CTkEntry(root)
apply_font(csv_entry, entry_font)
csv_entry.grid(row=3, column=1, padx=10)
csv_button = ctk.CTkButton(root, text="Browse Files", command=browse_csv)
apply_font(csv_button, button_font)
csv_button.grid(row=3, column=2, padx=10)

shp_label = ctk.CTkLabel(root, text="Shapefiles:")
apply_font(shp_label, label_font)
shp_label.grid(row=4, column=0, sticky='w', padx=10)
shp_entry = ctk.CTkEntry(root)
apply_font(shp_entry, entry_font)
shp_entry.grid(row=4, column=1, padx=10)
shp_button = ctk.CTkButton(root, text="Browse Files", command=browse_shp)
apply_font(shp_button, button_font)
shp_button.grid(row=4, column=2, padx=10)

# Input for columns of interest
columns_label = ctk.CTkLabel(root, text="Which is the column of interest in your data?")
apply_font(columns_label, label_font)
columns_label.grid(row=5, column=0, columnspan=3, sticky='w', padx=10, pady=5)

# "In Shapefile" entry and checkbox
italian_label = ctk.CTkLabel(root, text="In Shapefile")
apply_font(italian_label, label_font)
italian_label.grid(row=6, column=0, sticky='w', padx=10)
italian_entry = ctk.CTkEntry(root)
apply_font(italian_entry, entry_font)
italian_entry.grid(row=6, column=1, padx=10)

shp_language_var = ctk.BooleanVar(value=False)  # Checkbox variable for shapefile language
shp_language_checkbox = ctk.CTkCheckBox(root, text="Is Italian?", variable=shp_language_var)
apply_font(shp_language_checkbox, label_font)
shp_language_checkbox.grid(row=6, column=2, padx=10)

# "In CSV file" entry and checkbox
english_label = ctk.CTkLabel(root, text="In CSV file")
apply_font(english_label, label_font)
english_label.grid(row=7, column=0, sticky='w', padx=10)
english_entry = ctk.CTkEntry(root)
apply_font(english_entry, entry_font)
english_entry.grid(row=7, column=1, padx=10)

csv_language_var = ctk.BooleanVar(value=False)  # Checkbox variable for CSV language
csv_language_checkbox = ctk.CTkCheckBox(root, text="Is Italian?", variable=csv_language_var)
apply_font(csv_language_checkbox, label_font)
csv_language_checkbox.grid(row=7, column=2, padx=10)

# "None" button for columns of interest
none_clicked = False
none_button = ctk.CTkButton(root, text="None", command=toggle_none, fg_color="blue")
apply_font(none_button, button_font)
none_button.grid(row=8, column=1, padx=10, pady=5)

# Dropdown menu for model selection
model_label = ctk.CTkLabel(root, text="Select Model:")
apply_font(model_label, label_font)
model_label.grid(row=9, column=0, sticky='w', padx=10, pady=10)
model_var = ctk.StringVar(value="gpt-4o")  # Default model
model_dropdown = ctk.CTkOptionMenu(root, variable=model_var, values=["gpt-4o", "gpt-4"])
apply_font(model_dropdown, entry_font)
model_dropdown.grid(row=9, column=1, padx=10, pady=10)

# Execute and Refresh buttons
execute_button = ctk.CTkButton(root, text="Execute", command=execute_task)
apply_font(execute_button, button_font)
execute_button.grid(row=10, column=1, sticky='e', padx=10, pady=10)

refresh_button = ctk.CTkButton(root, text="Refresh", command=refresh_gui)
apply_font(refresh_button, button_font)
refresh_button.grid(row=10, column=2, sticky='w', padx=10, pady=10)

# Start the GUI event loop
root.mainloop()