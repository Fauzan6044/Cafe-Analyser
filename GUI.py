import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter.filedialog as fd
import os
import tkVideoPlayer as tkv
import subprocess
import threading
import PerformanceDetection_GUI
import queue
import time
import google.generativeai as genai
import speech_recognition as sr
import pyttsx3
import sys

output_file_name = "output" 
staff1_n = "Staff 1"
staff2_n = "Staff 2"

input_filepath = None
output_filepath = None
conversation_history = []

def text_to_speech(text):

    my_text = text
    engine = pyttsx3.init("sapi5")
    if len(engine.getProperty('voices')) > 1:
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[0].id)

    engine.say(my_text)
    engine.runAndWait()
    engine.stop()

def speech_to_text(chat_text, entry_field):  # Add chat_text and entry_field as arguments
    r = sr.Recognizer()
    mic = sr.Microphone()
    chat_text.insert(tk.END, "How may I help you?\n")  # Display prompt in chat_text
    with mic as source:
        audio = r.listen(source)
    chat_text.insert(tk.END, 'Processing audio...\n')
    try:
        text = r.recognize_google(audio)
        entry_field.insert(0, text)  # Insert recognized text into the entry field
        return text
    except sr.UnknownValueError:
        chat_text.insert(tk.END, "Sorry, I could not understand your audio.\n")
        return ""
    except sr.RequestError as e:
        chat_text.insert(tk.END, f"Could not request results from Google Speech Recognition service; {e}\n")
        return ""


def get_user_input(chat_text, entry_field):  # Add chat_text and entry_field as arguments
    input_method = entry_field.get()  # Get input directly from the entry field
    entry_field.delete(0, tk.END)     # Clear the entry field

    if input_method.strip().lower() == "exit":
        chat_text.insert(tk.END, "Exiting conversation with Gemini.\n")
        return None
    else:
        return input_method


def start_genai_chatbox():
    print("here in guipy")
    # genai.configure(api_key='AIzaSyCMSX8Ol_eEuotJZAfCM9erYM4CDNKggkM')
    genai.configure(api_key='AIzaSyBr6qPykqG__W3x8DQ9RPiN4n9P816Pv6o')
    model = genai.GenerativeModel(model_name="gemini-1.5-pro")

    video_file_name = str(output_filepath)
    video_file = genai.upload_file(path=output_filepath)
    
    conversation_history.append("The video is of a Cafe with 2 staff members on the left side of the table, serving coffee to any incoming customers. I am the owner of the cafe, and based on what you see throughout the video, I want to ask a few questions, try to keep the answers around 50 words or so and keep your answers specific to my cafe instead of generic answers.")
    conversation_history.append(video_file)
    user_input = ""
    recording = False

    def start_recording(event=None):
        nonlocal recording
        if not recording:
            recording = True
            chat_text.insert(tk.END, "Listening...\n")  # Indicate recording started
            # ... start your recording process here (e.g., using pyaudio or another library)
            threading.Thread(target=record_audio).start()

    def stop_recording(event=None):
        nonlocal recording
        if recording:
            recording = False
            chat_text.insert(tk.END, "Processing audio...\n")
    
    def record_audio():
        r = sr.Recognizer()
        device_index = None
        selected_mic_name = selected_mic.get()
        if selected_mic_name != "Default":
            for i, mic_name in enumerate(mic_options):
                if mic_name == selected_mic_name:
                    device_index = i
                    break
        with sr.Microphone(device_index=device_index) as source:   # Index 3 for FiFine K669-B 
            while recording:
                try:
                    audio = r.listen(source)
                    text = r.recognize_google(audio)
                    entry_field.insert(0, text)
                    send_message()  # Send the message immediately
                    break            # Exit the loop after sending
                except sr.UnknownValueError:
                    chat_text.insert(tk.END, "Sorry, I could not understand your audio.\n")
                    break
                except sr.RequestError as e:
                    chat_text.insert(tk.END, f"Could not request results; {e}\n")
                    break

    def send_message(user_input=None):
        if user_input is None:
            user_input = get_user_input(chat_text, entry_field)
        if user_input:
            # Display user's message in the chat window
            chat_text.insert(tk.END, f"You: {user_input}\n")
            conversation_history.append({"text": user_input})
            entry_field.delete(0, tk.END)

            # Nested function to run in a separate thread
            def generate_response_thread():
                try:
                    response = model.generate_content(conversation_history)
                    chat_text.insert(tk.END, f"Café AI: {response.text}\n")
                    text_to_speech(response.text)
                    conversation_history.append(response.text)
                except Exception as e:  # Catch exceptions and display errors
                    chat_text.insert(tk.END, f"Error generating response: {e}\n")

            # Start the thread to generate the response
            threading.Thread(target=generate_response_thread).start()

    chat_window = tk.Toplevel()  # Create a new window for the chatbox
    chat_window.title("Café AI Chat")  # Set the title
    chat_window.geometry("550x500")  # Set the dimensions

    # Create a text widget for displaying the conversation
    chat_text = tk.Text(chat_window, wrap="word")
    chat_text.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    # Create a scrollbar for the text widget
    scrollbar = tk.Scrollbar(chat_window, command=chat_text.yview)
    scrollbar.grid(row=0, column=1, sticky="nse")
    chat_text.config(yscrollcommand=scrollbar.set)

    # Create an entry widget for user input
    entry_field = tk.Entry(chat_window)
    entry_field.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
    chat_text.insert(tk.END, f"Connecting to Café AI - please wait...\n")
    time.sleep(5)
    chat_text.insert(tk.END, "You can now start a conversation with Café AI!\n")

    seen_elements = set()

    # Create a button for sending messages
    send_button = tk.Button(chat_window, text="Send", command=send_message)
    send_button.grid(row=1, column=1, padx=5, pady=5)
    voice_button = tk.Button(chat_window, text="Voice")
    voice_button.bind("<ButtonPress-1>", start_recording)  # Bind to button press event
    voice_button.bind("<ButtonRelease-1>", stop_recording)  # Bind to button release event
    voice_button.grid(row=2, column=1, padx=5, pady=5)

    # --- Microphone Selection ---

    # Create a label for the microphone selection
    mic_label = ttk.Label(chat_window, text="Select Microphone:")
    mic_label.grid(row=3, column=0, sticky="w", padx=5, pady=5)  # Adjust row/column as needed

    # Create a StringVar to store the selected mic
    selected_mic = tk.StringVar(value="Default")

    # Create a Combobox for microphone selection
    mic_options = sr.Microphone.list_microphone_names()  # Get available mics
    mic_combobox = ttk.Combobox(chat_window, textvariable=selected_mic, values=mic_options)
    mic_combobox.grid(row=3, column=0, sticky="ew", padx=120, pady=5)
    def on_mic_select(event):
        # Function to handle microphone selection
        selected_mic_name = selected_mic.get()
        for i, mic_name in enumerate(mic_options):
            if mic_name == selected_mic_name:
                device_index = i
                break
        # Update the microphone index in record_audio (see below)

    mic_combobox.bind("<<ComboboxSelected>>", on_mic_select)

    # --- End Microphone Selection ---

    # Bind the Enter key to the send_message function
    chat_window.bind("<Return>", lambda event: send_message())


def update_results():
    try:
        while not PerformanceDetection_GUI.counter1_queue.empty():
            counter1 = PerformanceDetection_GUI.counter1_queue.get_nowait()
            staff1_value.set(counter1)

        while not PerformanceDetection_GUI.counter2_queue.empty():
            counter2 = PerformanceDetection_GUI.counter2_queue.get_nowait()
            staff2_value.set(counter2)

    except queue.Empty:
        pass

    app.after(100, update_results)

def execute_analysis():
    if not input_filepath:
        print("No input video selected.")
        return
    #PerformanceDetection_GUI.run_analysis(input_filepath, output_file_name, check_person, check_arcup, check_cup, check_preview, app)
    app.after(100)
    app.update()
    analysis_thread = threading.Thread(target=PerformanceDetection_GUI.run_analysis, args=(input_filepath, output_file_name, check_person, check_arcup, check_cup, check_preview, staff1_n, staff2_n))
    analysis_thread.start() 
    # execute_frame.after(0, update_results)
    # execute_frame.update_idletasks()

def execute_genai():
    progress_bar = ttk.Progressbar(labelframe_exp, mode="indeterminate", length=200)
    progress_bar.grid(row=5, column=0, columnspan=2, padx=10, pady=10)  # Place the progress bar
    progress_bar.start()  # Start the animation
    
    # Start a new thread for the GenAI conversation
    def start_genai_thread():
        start_genai_chatbox()
        progress_bar.stop()  # Stop the animation when chatbox is ready
        progress_bar.grid_forget()  # Remove the progress bar
    # Start a new thread for the GenAI conversation
    genai_thread = threading.Thread(target=start_genai_thread)
    genai_thread.start()


def select_input_file():
    global input_filepath
    filetypes = (("MP4 files", "*.mp4"), ("All files", "*.*"))
    script_dir = os.path.dirname(os.path.realpath(__file__))
    input_folder = os.path.join(script_dir, "Input")
    if not os.path.isdir(input_folder): #Error Handling for if Input folder does not exist under root/Input
        print(f"Error: Input folder '{input_folder}' not found.")
        return  # Don't open the dialog if the folder doesn't exist
    filepath = fd.askopenfilename(title="Open Input Video", initialdir=input_folder, filetypes=filetypes)

    if filepath:
        input_filepath = filepath
        filename = os.path.basename(filepath)
        filename_entry.configure(state="normal")
        filename_entry.delete(0, "end")
        filename_entry.insert(0, filename)
        filename_entry.configure(state="readonly")

        print(f"Selected input file: {filepath}")

def select_output_file():
    global output_filepath
    filetypes = (("MP4 files", "*.mp4"), ("All files", "*.*"))
    script_dir = os.path.dirname(os.path.realpath(__file__))
    output_folder = os.path.join(script_dir, "Output")
    if not os.path.isdir(output_folder): #Error Handling for if Output folder does not exist under root/Input
        print(f"Error: Output folder '{output_folder}' not found.")
        return  # Don't open the dialog if the folder doesn't exist
    filepath = fd.askopenfilename(title="Open Output Video", initialdir=output_folder, filetypes=filetypes)

    if filepath:
        output_filepath = filepath
        filename = os.path.basename(filepath)
        output_filename_entry.configure(state="normal")
        output_filename_entry.delete(0, "end")
        output_filename_entry.insert(0, filename)
        output_filename_entry.configure(state="readonly")

        print(f"Selected output file: {filepath}")

def update_output_name(*args):
    global output_file_name
    output_file_name = output_entry.get()
    print(f"Output file name updated: {output_file_name}")

def update_staff1_name(*args):
    global staff1_n
    staff1_n = staff1_nentry.get()
    print(f"Staff 1 name has been updated: {staff1_n}")
    staff1_stat.config(text=f"Cups served by {staff1_n}")

def update_staff2_name(*args):
    global staff2_n
    staff2_n = staff2_nentry.get()
    print(f"Staff 2 name has been updated: {staff2_n}")
    staff2_stat.config(text=f"Cups served by {staff2_n}")

def play_video():
    if output_filepath:  # Play the output video (if selected)
        videoplayer = tkv.TkinterVideo(master=preview_frame, scaled=True)
        videoplayer.load(output_filepath)
        # Set desired video player dimensions
        desired_width = 720
        desired_height = int(desired_width*9/16)
        videoplayer.configure(width=desired_width, height=desired_height)
        # Place the video player
        videoplayer.grid(row=3, column=0, rowspan=9, columnspan=6, pady=10, padx=10, sticky = 'nsew')
        # Configure row and column to expand to the video player's size
        preview_frame.rowconfigure(3, weight=1)  # Expand row to video height
        preview_frame.columnconfigure(0, weight=1)  # Expand column to video width
        videoplayer.play()
    else:
        print("No output video selected.")

def center_window(window):
    window.update_idletasks()
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    window.geometry(f"+{x}+{y}")


app = ttk.Window(themename="darkly")  
app.title("Café Analyzer")
app.geometry("800x600")
#initializing Staff1 and Staff2 variables right after app initialization
staff1_value = tk.StringVar(value="0")
staff2_value = tk.StringVar(value="0")

# Create a Notebook widget to hold the tabs
notebook = ttk.Notebook(app)
notebook.grid(row=0, column=0, sticky="nsew")  # Place notebook in the grid
app.rowconfigure(0, weight=1)  # Allow row to expand
app.columnconfigure(0, weight=1)  # Allow column to expand
# Create the "Configure" tab
configure_frame = ttk.Frame(notebook)
notebook.add(configure_frame, text="Configure")
# Create the "Preview" tab
preview_frame = ttk.Frame(notebook)
notebook.add(preview_frame, text="Preview")
# Create the "stats" tab
execute_frame = ttk.Frame(notebook)
notebook.add(execute_frame, text="Execute & Analysis") #can use notebook. Insert instead to positionally lock which tab appears first
# Create the "Experimental" tab
experiment_frame = ttk.Frame(notebook)
notebook.add(experiment_frame, text="Experimental - GenAI")


# Welcome Label
welcome_label = ttk.Label(configure_frame, text="Welcome to Employee Performance Tracker")
welcome_label.grid(row=1, column=0, columnspan=2, pady=(20, 10))  # Span 2 columns

labelframe_files = ttk.Labelframe(configure_frame, text="File Settings")
labelframe_files.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
# Configure Tab - Select MP4 Label
input_mp4_label = ttk.Label(labelframe_files, text="Select the input MP4 file:")
input_mp4_label.grid(row=2, column=0, pady=(10, 0), sticky="w")  # Align to the left
# File name entry
filename_entry = ttk.Entry(labelframe_files, state="readonly")  
filename_entry.grid(row=3, column=0, padx=5, pady=(0, 10), sticky="ew")  # Expand to fill width
# Browse button
button = ttk.Button(labelframe_files, text="Browse", command=select_input_file)  
button.grid(row=3, column=1, padx=5, pady=(0, 10), sticky="e")  # Align to the right

# Configure Tab - Output File Name Label
output_label = ttk.Label(labelframe_files, text="Output File Name:")
output_label.grid(row=4, column=0, pady=(10, 0), sticky="w")
# Output File Name Entry
output_entry = ttk.Entry(labelframe_files)
output_entry.insert(0, output_file_name)  # Set default text
output_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=(10,0), sticky="ew")
output_entry.bind("<Return>", update_output_name)  # Update on Enter key press
output_entry.bind("<FocusOut>", update_output_name)  # Update on losing focus

labelframe_opt = ttk.Labelframe(configure_frame, text="Togglable Options")
labelframe_opt.grid(row=6, column=0, padx=20, pady=20, sticky="nsew")
# configure_frame.columnconfigure(6, weight=1)
# configure_frame.rowconfigure(6, weight=1)
check_person = tk.IntVar()
check_cup = tk.IntVar()
check_arcup = tk.IntVar() #Ex: use check_person.get() to get the value of the checkbox.
check_preview = tk.IntVar()
ttk.Checkbutton(labelframe_opt, text="Enable Person Tracking", variable=check_person).grid(row=7, column=0, pady=6, sticky="w")
ttk.Checkbutton(labelframe_opt, text="Enable Cup Tracking", variable=check_cup).grid(row=8, column=0, pady=6,sticky="w")
ttk.Checkbutton(labelframe_opt, text="Enable Cup Registration Area", variable=check_arcup).grid(row=9, column=0, pady=6, sticky="w")
ttk.Checkbutton(labelframe_opt, text="Enable Live Preview", variable=check_preview).grid(row=10, column=0, pady=6, sticky="w")

# Configure Tab - Customizations Container
labelframe_custom = ttk.Labelframe(configure_frame, text="Customizations")
labelframe_custom.grid(row=6, column=2, padx=20, pady=20, sticky="nsew")

#Customizations Container - staff 1 Name label
staff1_label = ttk.Label(labelframe_custom, text="Set name for Staff 1: ")
staff1_label.grid(row=7, column=2, pady=(10, 0), sticky="w")
# Staff 1 Name Entry
staff1_nentry = ttk.Entry(labelframe_custom)
staff1_nentry.insert(0, staff1_n)  # Set default text
staff1_nentry.grid(row=7, column=3, columnspan=2, padx=5, pady=(10,0), sticky="ew")
staff1_nentry.bind("<Return>", update_staff1_name)  # Update on Enter key press
staff1_nentry.bind("<FocusOut>", update_staff1_name)  # Update on losing focus

# Customizations Container - Staff 2 Name Label
staff2_label = ttk.Label(labelframe_custom, text="Set name for Staff 2: ")
staff2_label.grid(row=8, column=2, pady=(10, 0), sticky="w")
# Staff 2 Name Entry
staff2_nentry = ttk.Entry(labelframe_custom)
staff2_nentry.insert(0, staff2_n)  # Set default text
staff2_nentry.grid(row=8, column=3, columnspan=2, padx=5, pady=(10,0), sticky="ew")
staff2_nentry.bind("<Return>", update_staff2_name)  # Update on Enter key press
staff2_nentry.bind("<FocusOut>", update_staff2_name)  # Update on losing focus


# Preview Tab - Output Video + Play button
welcome_label = ttk.Label(preview_frame, text="If you have a processed output, select the output file and play them here!")
welcome_label.grid(row=1, column=0, columnspan=2, pady=(20, 10))  # Span 2 columns
output_mp4_label = ttk.Label(preview_frame, text="Select an output video to play!")
output_mp4_label.grid(row=2, column=0, pady=(20, 0), sticky="w")  # Align to the left
output_button = ttk.Button(preview_frame, text="Browse Output", command=select_output_file)
output_button.grid(row=2, column=2, padx=5, pady=(20, 0), sticky="e")
output_filename_entry = ttk.Entry(preview_frame, state="readonly")
output_filename_entry.grid(row=2, column=1, padx=5, pady=(20, 0), sticky="ew")
play_button = ttk.Button(preview_frame, text="Play Video", command=play_video, bootstyle=SUCCESS)
play_button.grid(row=3, column=0, columnspan=2, pady=10)


# Execution Tab
execute_message = ttk.Label(execute_frame, text="Please ensure you have selected the right configuration before proceeding")
execute_message.grid(row=3, column=0, pady=10, sticky='w')
labelframe_analysis = ttk.Labelframe(execute_frame, text="Analytical Statistics")
labelframe_analysis.grid(row=4, column=0, padx=20, pady=20, sticky="nsew")

staff1_stat = ttk.Label(labelframe_analysis, text=f"Cups served by {staff1_n}")
staff1_stat.grid(row=4, column=0, pady=6, sticky='w')
staff1_entry = ttk.Entry(labelframe_analysis, state="readonly", textvariable=staff1_value)  # Create the entry first
staff1_entry.grid(row=4, column=1, padx=5, pady=6, sticky="ew")  # Then place it in the grid
staff1_entry.insert(0, "0") #initializing with 0
staff2_stat = ttk.Label(labelframe_analysis, text=f"Cups served by {staff2_n}")
staff2_stat.grid(row=5, column=0, pady=6, sticky='w')
staff2_entry = ttk.Entry(labelframe_analysis, state="readonly", textvariable=staff2_value)  # Create the entry first
staff2_entry.grid(row=5, column=1, padx=5, pady=6, sticky="ew")  # Then place it in the grid
staff2_entry.insert(0, "0") #initializing with 0
execute_button = ttk.Button(execute_frame, text="Run Cafe Analysis", command=execute_analysis, bootstyle=SUCCESS) #Add command here to run the main script 
execute_button.grid(row=10, column=0, columnspan = 2, padx=(50,0), pady=10)

# Experimental Tab
landing_label = ttk.Label(experiment_frame, text="This is the Experimental Tab where if everything works normally \nAllowing you to have an interaction with an AI and have conversations regarding the output video!\n Depending on the size of the video, you may have to wait longer for the AI to process")
landing_label.grid(row=0, column=0, columnspan=2, pady=(20, 10))  # Span 2 columns
labelframe_exp = ttk.Labelframe(experiment_frame)
labelframe_exp.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
# Experimental Tab - Select MP4 Label
genai_output_mp4_label = ttk.Label(labelframe_exp, text="Select a processed output file:")
genai_output_mp4_label.grid(row=1, column=0, pady=(20, 0), sticky="w")  # Align to the left
output_button = ttk.Button(labelframe_exp, text="Browse Output", command=select_output_file)
output_button.grid(row=1, column=2, padx=5, pady=(20, 0), sticky="e")
output_filename_entry = ttk.Entry(labelframe_exp, state="readonly")
output_filename_entry.grid(row=1, column=1, padx=5, pady=(20, 0), sticky="ew")
play_button = ttk.Button(labelframe_exp, text="Play Video in preview - WIP", command=play_video, bootstyle=SUCCESS)
play_button.grid(row=3, column=0, columnspan=2, padx=(50,0), pady=10)
genai_button = ttk.Button(labelframe_exp, text="Converse with Café AI", command=execute_genai, bootstyle=SUCCESS) #Add command here to run the main script 
genai_button.grid(row=4, column=0, columnspan = 2, padx=(50,0), pady=10)


app.after(100, lambda: center_window(app))
app.after(100, update_results)
app.mainloop()
