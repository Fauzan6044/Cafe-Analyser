import google.generativeai as genai
import time
import speech_recognition as sr
import pyttsx3
import sys

def text_to_speech(text):

    my_text = text
    engine = pyttsx3.init("sapi5")
    if len(engine.getProperty('voices')) > 1:
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[0].id)

    engine.say(my_text)
    engine.runAndWait()
    engine.stop()

def speech_to_text():
    r = sr.Recognizer()
    mic = sr.Microphone()
    print("How may i help you")
    with mic as source:
        audio = r.listen(source)
    print('Processing audio ')
    text = r.recognize_google(audio)
    return text

def get_user_input():
    while True:
        input_method = input("Would you like to speak, type your input, or exit? (speak/type/exit): ").strip().lower()
        if input_method in ["speak", "type", "exit"]:
            break
        print("Invalid input. Please enter 'speak', 'type', or 'exit'.")
    
    if input_method == "speak":
        return speech_to_text()
    elif input_method == "type":
        return input("Please type your input: ")
    elif input_method == "exit":
        print("Exiting conversation with Gemini.")
        return None
        sys.exit()

def have_conversation_with_gemini(output_filepath):
  print(1)
  genai.configure(api_key='AIzaSyCMSX8Ol_eEuotJZAfCM9erYM4CDNKggkM')
  model = genai.GenerativeModel(model_name="gemini-1.5-pro")
  #print(output_filepath)
  video_file_name = str(output_filepath)
  video_file = genai.upload_file(path=output_filepath)

  conversation_history = []
  conversation_history.append(video_file)


  while True:
    
    user_prompt = get_user_input()
    conversation_history.append({"text": user_prompt})

    response = model.generate_content(conversation_history)

    text_to_speech(response.text)
    conversation_history.append(response.text)
    print(conversation_history)
