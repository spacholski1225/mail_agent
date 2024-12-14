from typing import List, Dict, Any, Union, AsyncIterable
from dotenv import load_dotenv
import tiktoken
import openai
import os
import requests
import json
import aiohttp

class OpenAIService:
    def __init__(self):
        self.openai = openai.OpenAI()
        self.tokenizers: Dict[str, Any] = {}
        self.IM_START = "<|im_start|>"
        self.IM_END = "<|im_end|>"
        self.IM_SEP = "<|im_sep|>"

    async def get_tokenizer(self, model_name: str):
        if model_name not in self.tokenizers:
            special_tokens = {
                self.IM_START: 100264,
                self.IM_END: 100265,
                self.IM_SEP: 100266,
            }
            tokenizer = tiktoken.encoding_for_model(model_name)  # Pobiera tokenizer dla modelu
            self.tokenizers[model_name] = tokenizer
        return self.tokenizers[model_name]

    async def count_tokens(self, messages: List[Dict[str, str]], model: str = 'gpt-4o') -> int:
        tokenizer = await self.get_tokenizer(model)

        formatted_content = ''
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            formatted_content += f"{self.IM_START}{role}{self.IM_SEP}{content}{self.IM_END}"
        formatted_content += f"{self.IM_START}assistant{self.IM_SEP}"

        return len(tokenizer.encode(formatted_content))

    async def completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        stream: bool = False,
        json_mode: bool = False,
        max_tokens: int = 900
    ) -> Union[Dict, AsyncIterable[Dict]]:
        try:
            response_format = {"type": "json_object"} if json_mode else {"type": "text"}
            chat_completion = await self.openai.chat.completions.create(
                messages=messages,
                model=model,
                stream=stream,
                max_tokens=max_tokens,
                response_format=response_format
            )

            if stream:
                return chat_completion
            else:
                return chat_completion
        except Exception as error:
            print("Error in OpenAI completion:", error)
            raise error
    
    async def call_openai_api(self, prompt):
        prompt_string = str(prompt)
        load_dotenv()
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENAI_KEY')}"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": read_file_content('C:\Sources\mail_agent\mail_agent\Prompts\InBriefPrompt.md')}, {"role": "user", "content": prompt_string}],
            "max_tokens": 2000,
            "temperature": 0.7
        }

        print(json.dumps(data))

        if not isinstance(prompt_string, str):
            raise ValueError("Prompt must be a string.")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=json.dumps(data)) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
        except aiohttp.ClientError as e:
            print(f"Błąd podczas łączenia z API OpenAI: {e}")
            return None
        except KeyError as e:
            print(f"Błąd w odpowiedzi API: brak klucza {e}")
            return None

def read_file_content(file_path:str):
    print(os.getcwd())
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return "File not found."
    except Exception as e:
        return f"An error occurred: {e}"
