import json
import random
from typing import Dict, List, Optional

from openai import OpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel
from pydantic import ValidationError


# --- Pydantic Model for Quiz Question ---
class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    answer: str
    explanation: str


# --- Initial prompt (Priming the assistant) ---
chat_history: List[ChatCompletionMessageParam] = [
    {
        "role": "system",
        "content": (
            "You are a REST API server with an endpoint /generate-random-question/:topic. "
            "The endpoint returns a random Python quiz question as JSON with the following fields:\n"
            "- question (string)\n"
            "- options (list of strings)\n"
            "- answer (string, must match one of the options)\n"
            "- explanation (string)"
        ),
    },
    {
        "role": "user",
        "content": "GET /generate-random-question/variables"
    },
    {
        "role": "assistant",
        "content": '''{
    "question": "Which of the following is a valid variable name in Python?",
    "options": ["2nd_var", "my-var", "_value", "None"],
    "answer": "_value",
    "explanation": "Variable names must begin with a letter or underscore and cannot be a reserved keyword like 'None'."
}'''
    }
]


def get_quiz_from_topic(topic: str, api_key: str, context_chunks: Optional[List[str]] = None) -> Optional[
    Dict[str, str]]:
    context_chunks = context_chunks or []

    global chat_history

    client = OpenAI(api_key=api_key)

    context_text = context_chunks[0] if context_chunks else ""

    prompt = f"""
    Use the following study material to create a quiz question about "{topic}".

    Study Material:
    {context_text}

    Return a Python dictionary with keys: "question", "options", "answer", "explanation".
    """

    current_user_message: ChatCompletionMessageParam = {
        "role": "user",
        "content": prompt.strip(),
    }

    current_chat = chat_history + [current_user_message]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=current_chat
        )

        content = response.choices[0].message.content
        print(f"Response:\n{content}")

        # Append conversation to history
        assistant_message: ChatCompletionMessageParam = {
            "role": "assistant",
            "content": content
        }
        chat_history.append(current_user_message)
        chat_history.append(assistant_message)

        # Parse the raw content into a validated object
        quiz_question = QuizQuestion.parse_raw(content)

        # Shuffle options and preserve correct answer by value
        options = quiz_question.options
        correct_answer = quiz_question.answer

        if correct_answer not in options:
            raise ValueError("Answer is not among the provided options.")

        random.shuffle(options)
        quiz_question.options = options  # assign back

        return quiz_question.dict()

    except (OpenAIError, json.JSONDecodeError, ValidationError, ValueError) as e:
        print(f"Error: {e}")
        return None
