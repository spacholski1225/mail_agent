import imaplib
import email
import requests
import json
import os
import re
import aiofiles
from email.header import decode_header
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from OpenAIService import OpenAIService

def fetch_email_by_id(email_id):
    load_dotenv()
    imap_host = os.getenv("IMAP_HOST")
    imap_user = os.getenv("IMAP_USER")
    imap_pass = os.getenv("IMAP_PASS")

    # Połącz się z serwerem IMAP
    mail = imaplib.IMAP4_SSL(imap_host)
    mail.login(imap_user, imap_pass)

    # Wybierz skrzynkę odbiorczą
    mail.select("inbox")

    email_content = None
    if email_id:
        # Pobierz wiadomość
        status, msg_data = mail.fetch(email_id, "(RFC822)")

    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    if "attachment" not in content_disposition:
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
            else:
                body = msg.get_payload(decode=True).decode()

            email_content = (subject, body)

    mail.logout()

    return email_content

def convert_email_to_markdown(subject, html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    markdown_content = md(str(soup))

    markdown_email = f"# {subject}\n\n{markdown_content}"

    return markdown_email

def fetch_all_email_ids():
    load_dotenv()
    imap_host = os.getenv("IMAP_HOST")
    imap_user = os.getenv("IMAP_USER")
    imap_pass = os.getenv("IMAP_PASS")

    mail = imaplib.IMAP4_SSL(imap_host)
    mail.login(imap_user, imap_pass)

    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split() if status == 'OK' else []

    mail.logout()

    return email_ids

async def main():
    email_ids = fetch_all_email_ids()

    for email_id in email_ids:
        emails = fetch_email_by_id(email_id)

        if emails:
            with open("emails_markdown.md", "a", encoding="utf-8") as file:
                subject, body = emails
                markdown_email = convert_email_to_markdown(subject, body)

                openai_service = OpenAIService()
                token_count = await openai_service.count_tokens([{"role": "user", "content": markdown_email}])
                print(f"Email length in tokens: {token_count}")

                if token_count < 2000:
                    file.write(markdown_email + "\n\n")
                else:
                    lines = markdown_email.split('\n')
                    current_chunk = []
                    current_chunk_tokens = 0

                    for line in lines:
                        line_tokens = await openai_service.count_tokens([{"role": "user", "content": line}])
                        if current_chunk_tokens + line_tokens < 900:
                            current_chunk.append(line)
                            current_chunk_tokens += line_tokens
                            print(f"Current chunk tokens: {current_chunk_tokens}")
                        else:
                            file.write('\n'.join(current_chunk) + "\n\n")
                            email_text = '\n'.join(current_chunk)
                            print(clean_prompt(email_text))
                            response = await openai_service.call_openai_api(clean_prompt(email_text))
                            
                            print(response + "\n\n")
                            await write_response_to_file(response)

                            current_chunk = [line]
                            current_chunk_tokens = line_tokens

                    if current_chunk:
                        file.write(current_chunk)
        else:
            print(f"No email found for ID: {email_id}")

def clean_prompt(prompt):
    prompt_cleaned = re.sub(r'\n+', '\n', prompt.strip())
    lines = prompt_cleaned.split("\n")
    unique_lines = []
    for line in lines:
        if line not in unique_lines: 
            unique_lines.append(line)
    return "\n".join(unique_lines)

async def write_response_to_file(response):
    try:
        async with aiofiles.open('response.json', 'w') as file:
            await file.write(response)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
