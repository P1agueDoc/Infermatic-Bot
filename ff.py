import telebot
import requests
import json
import time
from threading import Lock
import re


TELEGRAM_BOT_TOKEN = ''
API_URL = 'https://api.totalgpt.ai/v1/completions'
API_KEY = ''

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

#chat history
chat_history = []

#story string
story_string = """<|start_header_id|>system<|end_header_id|>
{{#if system}}{{system}}
{{/if}}{{#if wiBefore}}{{wiBefore}}
{{/if}}{{#if description}}{{description}}
{{/if}}{{#if personality}}{{char}}'s personality: {{personality}}
{{/if}}{{#if scenario}}Scenario: {{scenario}}
{{/if}}{{#if wiAfter}}{{wiAfter}}
{{/if}}{{#if persona}}{{persona}}
{{/if}}{{trim}}<|eot_id|>"""

# Character
char_description = ("{{char}} это Мэгги это типичный инженер которая имеет острый язык и не прочь подколоть. "
                    "Она любит отвечать язвительно но с инженерскими замашками. Любит ставить людей на место."
                    "Мэгги Макгиннис всегда умела строить. В 4 года она использовала конструктор Lincoln Logs, чтобы воссоздать архитектурные чудеса."
                    " В 10 лет она собрала и переделала светильник на заказ к юбилею родителей."
                    " В 15 лет она сконструировала машину, которая перерабатывала души умерших..."
                    " Последняя поделка привлекла чуть больше внимания, чем «Линкольн Логс»"
                    "Сейчас Макгиннис возглавляет военный отдел Fairfax Industries RLORED и проводит время в механическом цехе, а не в лаборатории."
                    " Ее не интересует теория, для нее наука - это магия, которую можно потрогать. {{char}} Не разговаривает за других, только от себя."
                    "{{char}} использует только Русский язык и не пишет вещи по типу 'по скрипту' {{char}} always avoid writing 'p.s' or anything like that. {{char}} avoid using english or chineese. {{char}} avoid answering like wall of text.")

# Rate limit
lock = Lock()
last_request_times = []
RATE_LIMIT = 16  # 16 requests per minute


def generate_response(prompt):
    global last_request_times

    with lock:
        current_time = time.time()
        last_request_times = [t for t in last_request_times if current_time - t < 60]

        if len(last_request_times) >= RATE_LIMIT:
            return "Rate limit exceeded. Please wait a moment before trying again."

        last_request_times.append(current_time)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    payload = {
        "model": "Sao10K-72B-Qwen2.5-Kunou-v1-FP8-Dynamic",
        "prompt": prompt,
        "max_tokens": 7000,
        "temperature": 0.7,
        "top_k": 40,
        "repetition_penalty": 1.2
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            # Extract and clean the response text
            text = response.json().get('choices', [{}])[0].get('text', '').strip()
            # Remove unwanted debug metadata (e.g., Markdown-style headers)
            clean_text = re.sub(r"###.*?(\\n|$)", "", text).strip()
            return clean_text if clean_text else "I'm sorry, I couldn't think of a response. Try asking me something else!"
        else:
            return f"Error: {response.status_code} - {response.text}"
    except requests.RequestException as e:
        return f"An error occurred while trying to connect to the API: {e}"

@bot.message_handler(func=lambda message: message.text and f"@{bot.get_me().username}" in message.text)
def handle_mention(message):
    user_query = message.text.replace(f"@{bot.get_me().username}", "").strip()
    username = message.from_user.username or message.from_user.first_name

    prompt = f"{story_string}\n{char_description}\nUser: {user_query}\nAssistant:"

    bot_reply = generate_response(prompt)
    print(str(chat_history))

    if not bot_reply.strip():
        bot_reply = "I couldn't generate a response. Please try again later."

    #history
    chat_history.append({
        "user": username,
        "question": user_query,
        "answer": bot_reply
    })

    bot.reply_to(message, bot_reply)
    print(str(chat_history))

@bot.message_handler(commands=['history'])
def show_history(message):
    history_text = "\n".join(
        [f"{entry['user']} asked: {entry['question']}\nBot answered: {entry['answer']}" for entry in chat_history]
    )
    if not history_text:
        history_text = "No chat history yet."

    bot.reply_to(message, history_text)

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling()
