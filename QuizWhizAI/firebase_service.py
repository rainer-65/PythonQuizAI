import random

import firebase_admin
from firebase_admin import credentials, firestore


def initialize_firebase(credential_path: str):
    if not firebase_admin._apps:
        cred = credentials.Certificate(credential_path)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized.")


def save_quiz_question(topic: str, question_data: dict) -> str:
    try:
        db = firestore.client()

        # Flatten structure — add topic to question data
        question_data_with_topic = {
            **question_data,
            "topic": topic
        }

        # Save directly to top-level "quiz_questions" collection
        doc_ref = db.collection("quiz_questions").add(question_data_with_topic)
        return doc_ref[1].id
    except Exception as e:
        print(f"❌ Failed to save question: {e}")
        return ""


def get_random_quiz_questions(limit=10) -> list:
    try:
        db = firestore.client()
        docs = db.collection("quiz_questions").stream()
        questions = [doc.to_dict() for doc in docs if doc.to_dict()]
        return random.sample(questions, min(limit, len(questions)))
    except Exception as e:
        print(f"❌ Failed to retrieve questions: {e}")
        return []


def delete_all_quiz_questions():
    try:
        db = firestore.client()
        docs = db.collection("quiz_questions").stream()
        for doc in docs:
            doc.reference.delete()
        print("🧹 All quiz questions deleted.")
        return True
    except Exception as e:
        print(f"❌ Failed to delete quiz questions: {e}")
        return False


def get_quiz_question_count() -> int:
    try:
        db = firestore.client()
        docs = db.collection("quiz_questions").stream()
        count = sum(1 for _ in docs)
        return count
    except Exception as e:
        print(f"❌ Failed to count quiz questions: {e}")
        return 0
