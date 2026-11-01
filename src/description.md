Description

1. Task Objective
Set up the TroMate Mini App backend with Python and FastAPI, and test Telegram bot libraries/SDKs to pick one for development.

2. Scope of Work (To-Do Checklist)
Set up the Python/FastAPI project (virtual env, dependencies, .env config, folder structure).

Add a webhook endpoint for Telegram bot updates and a basic API for the Mini App.

Build a small proof of concept with each candidate library: python-telegram-bot, aiogram, pyTelegramBotAPI.

Test each library with FastAPI: webhook handling, async support, commands (/start, /balance), inline buttons, and opening the Mini App.

Check Mini App initData on the backend, following Telegram's official validation method.

Check Telegram limits: group privacy mode, bot permissions, and webhook limits.

Compare the libraries on ease of setup, documentation, async/FastAPI fit, and limitations.

Write down setup steps, test results, and the recommended library.

3. Definition of Done
FastAPI backend runs locally and receives Telegram updates through the webhook.

Bot replies to test commands and opens the Mini App from Telegram.

Mini App initData check works on the backend.

Library comparison and recommendation are documented in a technical report linked to the task.

Code is pushed to GitHub, and the work is reviewed and accepted.