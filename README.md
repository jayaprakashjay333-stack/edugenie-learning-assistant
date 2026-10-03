# EduGenie

EduGenie is a small, responsive learning assistant built with FastAPI and plain
HTML, CSS, and JavaScript. It can answer questions, explain concepts, create a
three-question multiple-choice quiz, summarize study material, and suggest a
personalized learning path. Learners can create an account, sign in, and sign
out; the learning workspace and AI endpoints require an authenticated session.

New users can create an account on `/login`. Account records and hashed
passwords are stored in a local SQLite database at `data/edugenie.sqlite3`.
Passwords are never sent to Gemini. Sessions expire after seven days and use
HTTP-only, SameSite=Lax cookies. When deploying behind HTTPS, set
`EDUGENIE_COOKIE_SECURE=true` in `.env`.

Gemini powers Q&A, quizzes, summaries, and learning paths. Concept explanations
use Gemini by default; they can instead use the optional local
LaMini-Flan-T5-783M model. The local model runs on CPU and is downloaded on the
first explanation request.

## Requirements

- Python 3.10 or newer
- A Google Gemini API key for Gemini-powered tasks
- Internet access for Gemini requests (and for the initial local model download)

## Set up in VS Code on Windows

1. Open this project folder in VS Code.
2. Install the Microsoft Python extension and select Python 3.10+.
3. Open **Terminal → New Terminal** and create a virtual environment:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks environment activation, run
   `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal,
   then activate the environment again.

4. Install the application dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` to a key created in
   Google AI Studio. Keep `.env` private; it is excluded from Git.
6. Start the app:

   ```powershell
   python -m uvicorn main:app --reload
   ```

7. Open <http://127.0.0.1:8000>. Interactive API documentation is at
   <http://127.0.0.1:8000/docs>.

You can also use **Run and Debug → EduGenie: run FastAPI** or select an EduGenie
task from **Terminal → Run Task**.

## Run without a Gemini key

To use the local model for concept explanations:

1. Install its optional dependencies:

   ```powershell
   python -m pip install -r requirements-local.txt
   ```

2. Set `EDUGENIE_EXPLANATION_PROVIDER=local` in `.env`.
3. Restart the server and request an explanation. The first request downloads
   LaMini-Flan-T5-783M, which is a large model and needs available disk space.

The other four tasks still require a Gemini API key. Set the provider back to
`gemini` to use Gemini for explanations.

## Test

With the virtual environment active and dependencies installed, run:

```powershell
python -m unittest discover -s tests -v
```

Tests mock AI model calls; they do not require an API key or make network
requests.

## API

All endpoints return JSON. Invalid input is rejected with HTTP 422. AI provider
and configuration errors are returned with an explanatory message.

| Method | Endpoint | JSON request |
| --- | --- | --- |
| `POST` | `/auth/register` | `{"email":"learner@example.com","display_name":"Learner","password":"at-least-8-characters"}` |
| `POST` | `/auth/login` | `{"email":"learner@example.com","password":"at-least-8-characters"}` |
| `GET` | `/auth/me` | Requires a signed-in session |
| `POST` | `/auth/logout` | Ends the current session |
| `POST` | `/qa` | `{"question":"Which is the largest ocean?"}` |
| `POST` | `/explain` | `{"topic":"The Pythagorean theorem"}` |
| `POST` | `/quiz` | `{"text":"A passage or topic of at least 20 characters."}` |
| `POST` | `/summarize` | `{"text":"A passage of at least 20 characters."}` |
| `POST` | `/learn/recommendations` | `{"topic":"SQL","level":"Beginner"}` |
| `GET` | `/health` | — |

`GEMINI_MODEL` can be changed in `.env` if a different model is available to your
Google AI Studio account. The default is `gemini-2.5-flash`. Set
`EDUGENIE_DB_PATH` to choose a different SQLite file location.
