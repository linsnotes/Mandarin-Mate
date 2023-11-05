import openai
import os
import json
import logging
import time
from dotenv import load_dotenv
from flask import Flask, render_template, request

app = Flask(__name__)

# Constants
MAX_RETRIES = 3
SLEEP_DURATION = 2
MODEL = "gpt-3.5-turbo"

# Configure logging
logging.basicConfig(level=logging.ERROR, filename='app.log', filemode='a', format='%(name)s - %(levelname)s - %(message)s')

# Load the .env file to get the OPENAI_KEY
load_dotenv()
openai.api_key = os.getenv('OPENAI_KEY')

class CustomException(Exception):
    pass

def clean_input(user_input):
    cleaned_input = user_input.replace("，", ",").replace(", ", ",").replace(" ", "")
    return cleaned_input

def send_chat_message(messages):
    for attempt in range(MAX_RETRIES):
        try:
            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=messages
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            logging.error(f"Error on attempt {attempt + 1}: {e}")
            time.sleep(SLEEP_DURATION)
            if attempt == MAX_RETRIES - 1:
                logging.error(f"Failed after {MAX_RETRIES} attempts. Messages: {messages}")
                raise CustomException(f"Failed to send messages after {MAX_RETRIES} retries")

def parse_json_response(response_text, word):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        logging.error(f"Failed to parse response as JSON for word: {word}")
        raise CustomException("Failed to parse response as JSON")

def generate_content(word):
    messages = [
        {
            "role": "system", 
            "content": "You are a helpful assistant."
        },
        {
            "role": "user", 
            "content": f"""Provide information for the Chinese word: {word} in a structured JSON format:\n\n
            {{
                "Hanyu Pinyin": "Provide the accurate Hanyu Pinyin",
                "Chinese Meaning": "Provide the accurate Chinese Meaning",
                "English Meaning": "Provide the accurate English Meaning",
                "Common Collocations": ["Provide the first most common collocation label with (1) at the begining", "Provide the second most common collocation label with (2) at the begining", "Provide the third most common collocation label with (3) at the begining"],
                "Example Sentences": ["Provide the first example sentence label with (1) at the begining, ensuring that the sentence reflects the correct meaning of the word and isn't just a direct translation from English", "Provide the second example sentence label with (2) at the beginingensuring that the sentence reflects the correct meaning of the word and isn't just a direct translation from English."]
            }}
                follow the format of this example which is very clean and structured, take note of the label (1),(2),(3) as well as the next line break. this example use the Chinese word "宁静":
            {{
                "Hanyu Pinyin": "níng jìng",
                "Chinese Meaning": "安静、平静",
                "English Meaning": "peaceful, tranquil",
                "Common Collocations": ["(1) 宁静的环境 (a peaceful environment)", "(2) 宁静的心灵 (a tranquil mind)", "(3) 宁静的夜晚 (a quiet night)"],
                "Example Sentences": ["(1) 在湖边散步能够感受到大自然的宁静。(Walking by the lake, you can feel the tranquility of nature.)", "(2) 她喜欢去宁静的地方远离城市喧嚣。(She likes to go to quiet places to get away from the hustle and bustle of the city.)"]
            }}
            """
        }
    ]
    generated_text = send_chat_message(messages)
    return parse_json_response(generated_text, word)

def do_enumerate(sequence, start=0):
    return enumerate(sequence, start=start)

app.jinja_env.filters['enumerate'] = do_enumerate

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_time = time.time()  # Capture the start time

        user_input = request.form['words']
        cleaned_input = clean_input(user_input)
        words = cleaned_input.split(',')
        word_dict = {}
        errors = []

        for word in words:
            try:
                generated_content = generate_content(word)
                word_dict[word] = {
                    'Hanyu Pinyin': generated_content.get('Hanyu Pinyin', ''),
                    'Chinese Meaning': generated_content.get('Chinese Meaning', ''),
                    'English Meaning': generated_content.get('English Meaning', ''),
                    'Common Collocations': generated_content.get('Common Collocations', ['', '', '']),
                    'Example Sentences': generated_content.get('Example Sentences', ['', ''])
                }
            except CustomException as e:
                logging.error(f"Failed to process word {word}: {e}")
                errors.append(f"Failed to process word {word}: {e}")

        processing_time = time.time() - start_time  # Calculate the processing time
        logging.info(f"Processing time: {processing_time:.2f} seconds")  # Log the processing time

        return render_template('results.html', word_dict=word_dict, errors=errors)
    return render_template('index.html') 

if __name__ == "__main__":
    app.run()
