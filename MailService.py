import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import os
from OpenAIService import OpenAIService

def fetch_email_by_id(email_id):
    # Wczytaj dane z pliku .env
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
            # Przetwórz wiadomość
            msg = email.message_from_bytes(response_part[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            
            # Pobierz zawartość wiadomości
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

    # Wyloguj się
    mail.logout()

    return email_content

def convert_email_to_markdown(subject, html_content):
    # Użyj BeautifulSoup do parsowania HTML
    soup = BeautifulSoup(html_content, "html.parser")

    # Usuń niepotrzebne elementy, np. skrypty, style
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    # Przekształć HTML na Markdown
    markdown_content = md(str(soup))

    # Dodaj tytuł jako nagłówek
    markdown_email = f"# {subject}\n\n{markdown_content}"

    return markdown_email

def fetch_all_email_ids():
    # Wczytaj dane z pliku .env
    load_dotenv()
    imap_host = os.getenv("IMAP_HOST")
    imap_user = os.getenv("IMAP_USER")
    imap_pass = os.getenv("IMAP_PASS")

    # Połącz się z serwerem IMAP
    mail = imaplib.IMAP4_SSL(imap_host)
    mail.login(imap_user, imap_pass)

    # Wybierz skrzynkę odbiorczą
    mail.select("inbox")

    # Pobierz identyfikatory wszystkich wiadomości
    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split() if status == 'OK' else []

    # Wyloguj się
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

                if token_count < 900:
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
                        else:
                            file.write('\n'.join(current_chunk) + "\n\n")

                            current_chunk = [line]
                            current_chunk_tokens = line_tokens

                    if current_chunk:
                        file.write('\n'.join(current_chunk) + "\n\n")

                file.write(markdown_email + "\n\n")
        else:
            print(f"No email found for ID: {email_id}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
