import json
from openai import OpenAI

# 配置RAGFlow API
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
    model = config['model']
    api_key = config['api_key']
    dialogid = config['dialogid']

client = OpenAI(api_key=api_key, base_url=f"http://localhost/api/v1/chats_openai/{dialogid}")

completion = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "你是一个乐于助人的助手"},
        {"role": "user", "content": "你是谁？"},
    ],
    stream=True
)

stream = True
if stream:
    for chunk in completion:
        print(chunk)
else:
    print(completion.choices[0].message.content)