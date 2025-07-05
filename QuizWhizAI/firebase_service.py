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
        collection_ref = db.collection("quiz_questions").document(topic).collection("questions")
        doc_ref = collection_ref.add(question_data)
        return doc_ref[1].id
    except Exception as e:
        print(f"❌ Failed to save question: {e}")
        return ""


def get_random_quiz_questions(limit=10) -> list:
    try:
        db = firestore.client()
        all_questions = []

        topics = db.collection("quiz_questions").stream()
        for topic_doc in topics:
            questions_ref = db.collection("quiz_questions").document(topic_doc.id).collection("questions")
            questions = questions_ref.stream()
            for q in questions:
                question_data = q.to_dict()
                if question_data:
                    all_questions.append(question_data)

        return random.sample(all_questions, min(limit, len(all_questions)))
    except Exception as e:
        print(f"❌ Failed to retrieve questions: {e}")
        return []
