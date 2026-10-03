import os
import sqlite3
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auth_schemas import CredentialsRequest, RegistrationRequest
from auth_store import (
    authenticate_user,
    create_session,
    create_user,
    delete_session,
    get_user_for_session,
)
from errors import AIServiceError
from explanation_module import explain_concept
from learning_path import get_learning_recommendations
from qna import answer_question
from quiz_module import generate_quiz
from schemas import ExplanationRequest, LearningPathRequest, QuestionRequest, TextRequest
from summary_module import summarize_text

PROJECT_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="EduGenie",
    description="An AI-powered learning assistant for explanations, questions, quizzes, summaries, and learning paths.",
    version="1.0.0",
)
app.mount(
    "/static",
    StaticFiles(directory=PROJECT_DIR / "static"),
    name="static",
)
templates = Jinja2Templates(directory=PROJECT_DIR / "templates")
SESSION_COOKIE_NAME = "edugenie_session"
SESSION_COOKIE_SECURE = os.getenv("EDUGENIE_COOKIE_SECURE", "").strip().lower() in {
    "1",
    "true",
    "yes",
}


def _session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _public_user(user: dict[str, object]) -> dict[str, object]:
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
    }


def require_user(request: Request) -> dict[str, object]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_user_for_session(token) if token else None
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Please sign in to use EduGenie.",
        )
    return user


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(
    request: Request, exc: AIServiceError
) -> JSONResponse:
    return JSONResponse(
        content={"detail": exc.public_message},
        status_code=exc.status_code,
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home(request: Request) -> HTMLResponse:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_user_for_session(token) if token else None
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": _public_user(user)},
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request) -> HTMLResponse:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token and get_user_for_session(token):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@app.post("/auth/register", status_code=201)
async def register(
    payload: RegistrationRequest, response: Response
) -> dict[str, object]:
    try:
        user = create_user(payload.email, payload.display_name, payload.password)
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not save your account. Please try again.",
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Sign in instead.",
        )
    token, max_age = create_session(int(user["id"]))
    _session_cookie(response, token, max_age)
    return {"user": _public_user(user)}


@app.post("/auth/login")
async def sign_in(
    payload: CredentialsRequest, response: Response
) -> dict[str, object]:
    try:
        user = authenticate_user(payload.email, payload.password)
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not check your account. Please try again.",
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect.",
        )
    token, max_age = create_session(int(user["id"]))
    _session_cookie(response, token, max_age)
    return {"user": _public_user(user)}


@app.get("/auth/me")
async def current_user(
    user: dict[str, object] = Depends(require_user),
) -> dict[str, object]:
    return {"user": _public_user(user)}


@app.post("/auth/logout")
async def sign_out(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        try:
            delete_session(token)
        except sqlite3.Error as exc:
            raise HTTPException(
                status_code=503,
                detail="Could not end your session. Please try again.",
            ) from exc
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"message": "Signed out."}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/qa")
async def qa(
    payload: QuestionRequest, user: dict[str, object] = Depends(require_user)
) -> dict[str, str]:
    return {"result": await answer_question(payload.question)}


@app.post("/explain")
async def explain(
    payload: ExplanationRequest, user: dict[str, object] = Depends(require_user)
) -> dict[str, str]:
    return {"result": await explain_concept(payload.topic)}


@app.post("/quiz")
async def quiz(
    payload: TextRequest, user: dict[str, object] = Depends(require_user)
) -> dict[str, list[dict[str, object]]]:
    return {"questions": await generate_quiz(payload.text)}


@app.post("/summarize")
async def summarize(
    payload: TextRequest, user: dict[str, object] = Depends(require_user)
) -> dict[str, str]:
    return {"result": await summarize_text(payload.text)}


@app.post("/learn/recommendations")
async def learning_recommendations(
    payload: LearningPathRequest, user: dict[str, object] = Depends(require_user)
) -> dict[str, str]:
    return {
        "result": await get_learning_recommendations(payload.topic, payload.level)
    }
