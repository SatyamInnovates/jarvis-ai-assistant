import re
import asyncio
import pygame
from time import sleep
from google.cloud import texttospeech
import google.generativeai as genai
import speech_recognition as sr
from datetime import datetime

SERVICE_ACCOUNT_PATH = r""
tts_client = texttospeech.TextToSpeechClient.from_service_account_file(SERVICE_ACCOUNT_PATH)

GEMINI_API_KEY = ""
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

count_question = 0
conversation_file = "conversation.txt"

async def save_conversation(question, answer, mode):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await asyncio.to_thread(write_to_file, timestamp, question, answer, mode)

def write_to_file(timestamp, question, answer, mode):
    with open(conversation_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Mode: {mode}\n")
        f.write(f"Question #{count_question}: {question}\n")
        f.write(f"Answer: {answer}\n")
        f.write(f"{'='*60}\n")

async def speak(text):
    sentences = re.split(r'(?<=[।.!?])\s+', text)
    for sentence in sentences:
        if not sentence.strip():
            continue
        try:
            response = await asyncio.to_thread(tts_client.synthesize_speech,
                input=texttospeech.SynthesisInput(text=sentence),
                voice=texttospeech.VoiceSelectionParams(
                    language_code="hi-IN",
                    name="hi-IN-Standard-B"
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16
                )
            )
            wav_file = "chunk.wav"
            with open(wav_file, "wb") as f:
                f.write(response.audio_content)
            await asyncio.to_thread(play_audio, wav_file)
        except Exception as e:
            print(f"TTS Error: {e}")

def play_audio(wav_file):
    pygame.mixer.init()
    pygame.mixer.music.load(wav_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        sleep(0.05)
    pygame.mixer.quit()

async def get_ai_answer(prompt):
    try:
        result = await asyncio.to_thread(model.generate_content, prompt)
        return result.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "speak again"

async def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening..")
        r.adjust_for_ambient_noise(source)
        audio = await asyncio.to_thread(r.listen, source)
    try:
        text = await asyncio.to_thread(r.recognize_google, audio)
        print(f"You said: {text}")
        return text.lower().strip()
    except sr.UnknownValueError:
        print("Could not understand.")
        return ""
    except sr.RequestError:
        print("Speech recognition error.")
        return ""

async def chat():
    global count_question
    mode = input("Enter mode (text/voice): ").lower()
    print(f"Mode: {mode}")

    if "text" in mode:
        await speak("You entered text mode. Type exit to quit.")
        while True:
            question = input("You: ")
            if question.lower() == "exit":
                await speak("Goodbye!")
                break
            elif question.lower() == "question":
                print(f"Total questions asked: {count_question}")
            else:
                count_question += 1
                answer = await get_ai_answer(question)
                print("UI_AI:", answer)
                await save_conversation(question, answer, "text")

    elif "voice" in mode:
        await speak("You entered voice mode. Say exit to quit.")
        while True:
            question = await listen()
            if not question:
                continue
            if "exit" in question:
                await speak("Goodbye!")
                break
            
            count_question += 1
            answer = await get_ai_answer(question)
            print("UI_AI:", answer)
            await speak(answer)
            await save_conversation(question, answer, "voice")
    else:
        await speak("I did not catch that. Please run the program again and say text mode or voice mode.")
        print("Invalid mode.")

asyncio.run(chat())