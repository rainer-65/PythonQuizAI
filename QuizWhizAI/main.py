import json
import os
import time

import openai
import streamlit as st
from dotenv import load_dotenv

from create_context_from_PDF import load_topic_contexts
from firebase_service import initialize_firebase, save_quiz_question, get_random_quiz_questions, \
    delete_all_quiz_questions, get_quiz_question_count, is_duplicate_question
from get_quiz import get_quiz_from_topic

# --- Initialize Firebase (do this once) ---
initialize_firebase("firebase_credentials.json")

# --- Constants ---
MAX_QUESTIONS = 10  # Set the maximum number of quiz questions

# --- Title Section ---
st.image("https://www.python.org/static/community_logos/python-logo-master-v3-TM.png", width=200)
st.markdown(
    "<h1 style='text-align: center; color: #4B8BBE;'>Python Quiz</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center;'>Test your knowledge of Python fundamentals with this interactive quiz!</p>",
    unsafe_allow_html=True
)
st.markdown("---")

# --- Load environment and initialize session state ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# --- Initialize session state ---
for key, default in {
    "questions": [], "answers": {}, "current_question": 0,
    "right_answers": 0, "wrong_answers": 0, "quiz_complete": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- SIDEBAR ---
topics = [
    'Comments in Python', 'Variables in Python',
    'Reading input from the keyboard in Python', 'Strings in Python',
    'Print in Python', 'F-Strings in Python'
]
# Load contextual content from PDFs once
topic_contexts = load_topic_contexts(topics)

st.sidebar.markdown(
    "<span style='font-size:18px; '>Select quiz topic</span>",
    unsafe_allow_html=True
)
topic = st.sidebar.selectbox(
    "Select a topic",
    topics,
    index=0,
    label_visibility="collapsed"
)

# --- Timer-related session state ---
if "question_start_time" not in st.session_state:
    st.session_state.question_start_time = time.time()
if "timer_expired" not in st.session_state:
    st.session_state.timer_expired = False

# --- ✅ Toggle: Enable/Disable saving to Firestore ---
save_to_db = st.sidebar.checkbox("💾 Save questions to DB", value=True)

# ✅ --- Display current DB entry count in sidebar ---
question_count = get_quiz_question_count()
st.sidebar.info(f"📦 Total number of quiz questions in DB: {question_count}")

# --- Start Quiz ---
if st.sidebar.button("Start Quiz"):
    # Reset session state
    st.session_state.answers = {}
    st.session_state.current_question = 0
    st.session_state.questions = []
    st.session_state.right_answers = 0
    st.session_state.wrong_answers = 0
    st.session_state.quiz_complete = False

    try:
        first_question = get_quiz_from_topic(topic, api_key, topic_contexts.get(topic, []))
        if not first_question or not isinstance(first_question, dict):
            st.error("Failed to load a quiz question. Please try again.")
        else:
            st.session_state.questions.append(first_question)
            if save_to_db and not is_duplicate_question(first_question):
                save_quiz_question(topic, first_question)
    except openai.error.AuthenticationError:
        st.error("Invalid API key.")

# --- Loading random questions ---
if st.sidebar.button("🎲 Load 10 Random Questions"):
    st.session_state.answers = {}
    st.session_state.current_question = 0
    st.session_state.questions = []
    st.session_state.right_answers = 0
    st.session_state.wrong_answers = 0
    st.session_state.quiz_complete = False

    random_questions = get_random_quiz_questions(10)

    if not random_questions:
        st.error("No questions found in Firestore.")
    else:
        st.session_state.questions = random_questions
        st.session_state.max_questions_override = len(random_questions)
        st.success(f"{len(random_questions)} random questions loaded!")

# --- Deleting all questions with confirmation ---
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

if st.sidebar.button("🧹 Delete All Questions"):
    st.session_state.confirm_delete = True

if st.session_state.confirm_delete:
    st.sidebar.warning("⚠️ This will delete *all* quiz questions. Are you sure?")
    col_del1, col_del2 = st.sidebar.columns(2)
    if col_del1.button("✅ Yes, Delete"):
        with st.spinner("Deleting all questions..."):
            success = delete_all_quiz_questions()
            if success:
                st.sidebar.success("All quiz questions deleted.")
            else:
                st.sidebar.error("Failed to delete questions.")
        st.session_state.confirm_delete = False
    if col_del2.button("❌ Cancel"):
        st.sidebar.info("Deletion cancelled.")
        st.session_state.confirm_delete = False


def display_question():
    if len(st.session_state.questions) == 0:
        st.info("Please start the quiz from the sidebar.")
        return

    question = st.session_state.questions[st.session_state.current_question]

    if question is None or not isinstance(question, dict):
        st.error("There was a problem loading this question.")
        return

    already_answered = st.session_state.current_question in st.session_state.answers

    # --- TIMER LOGIC with auto-refresh ---
    if "last_rendered_question" not in st.session_state or \
            st.session_state.last_rendered_question != st.session_state.current_question:
        st.session_state.question_start_time = time.time()
        st.session_state.timer_expired = False
        st.session_state.last_rendered_question = st.session_state.current_question

    # --- TIMER ---
    elapsed = int(time.time() - st.session_state.question_start_time)
    remaining = 30 - elapsed

    if remaining <= 0 and not st.session_state.timer_expired:
        st.session_state.timer_expired = True
        st.warning("⏰ Time's up! Moving to next question...")
        time.sleep(1.5)
        next_question()
        st.rerun()

    # Show timer info
    if remaining > 0:
        st.markdown(f"⏳ **Time left: {remaining} seconds**")
        st.progress((30 - remaining) / 30)

    # --- Always show question number with prefix ---
    question_number = st.session_state.current_question + 1
    question_text = question["question"]
    question_label = f"**QUESTION {question_number}.**"

    if "```" in question_text:
        st.markdown(question_label, unsafe_allow_html=True)
        st.markdown(question_text, unsafe_allow_html=True)
    elif "\n" in question_text or "    " in question_text:
        st.markdown(question_label)
        st.code(question_text, language="python")
    else:
        st.markdown(f"{question_label} {question_text}")

    # --- Answer options ---
    options = st.empty()
    user_answer = options.radio(
        "Your answer:", question["options"], key=st.session_state.current_question
    )

    if already_answered:
        index = st.session_state.answers[st.session_state.current_question]
        options.radio(
            "Your answer:",
            question["options"],
            key=float(st.session_state.current_question),
            index=index,
        )

    # 🔒 Disable Submit if already answered or time's up
    submit_button = st.button("Submit", disabled=already_answered or st.session_state.timer_expired)

    if submit_button:
        st.session_state.answers[st.session_state.current_question] = question["options"].index(user_answer)

        if user_answer == question["answer"]:
            st.success("✅ Correct!")
            st.session_state.right_answers += 1
        else:
            st.error(f"❌ Sorry, the correct answer was: **{question['answer']}**")
            st.session_state.wrong_answers += 1

        # --- Explanation block ---
        with st.expander("Explanation"):
            explanation = question["explanation"]
            if "```" in explanation:
                st.markdown(explanation, unsafe_allow_html=True)
            elif "\n" in explanation or "    " in explanation or "print(" in explanation:
                st.code(explanation, language="python")
            else:
                st.write(explanation)

    st.write(f"Right answers: {st.session_state.right_answers}")
    st.write(f"Wrong answers: {st.session_state.wrong_answers}")

    # 🌀 Auto-refresh countdown only if unanswered and timer is running
    if remaining > 0 and not already_answered and not st.session_state.timer_expired:
        time.sleep(1)
        st.rerun()


# --- Summary screen ---
def show_summary():
    st.markdown("## 🎉 Quiz Complete!")
    st.success("You’ve reached the end of the quiz.")

    total = st.session_state.right_answers + st.session_state.wrong_answers
    score = (st.session_state.right_answers / total) * 100 if total > 0 else 0

    st.markdown(f"""
    **📊 Your Stats:**
    - ✅ Correct Answers: {st.session_state.right_answers}
    - ❌ Incorrect Answers: {st.session_state.wrong_answers}
    - 🧠 Total Questions Answered: {total}
    - 🏁 Final Score: **{score:.1f}%**
    """)

    if st.button("🔁 Restart Quiz"):
        # Reset session state
        st.session_state.answers = {}
        st.session_state.current_question = 0
        st.session_state.questions = []
        st.session_state.right_answers = 0
        st.session_state.wrong_answers = 0
        st.session_state.quiz_complete = False
        st.session_state.pop("max_questions_override", None)

        try:
            first_question = get_quiz_from_topic(topic, api_key, topic_contexts.get(topic, []))
            if first_question and isinstance(first_question, dict):
                st.session_state.questions.append(first_question)
                if save_to_db and not is_duplicate_question(first_question):
                    save_quiz_question(topic, first_question)
        except openai.error.AuthenticationError:
            st.error("Invalid API key.")
            return
        st.rerun()  # ✅ Force a rerun to show the first question immediately


# --- Navigation functions ---
def next_question():
    question_limit = st.session_state.get("max_questions_override", MAX_QUESTIONS)
    current_index = st.session_state.current_question

    # 🚨 If unanswered, mark as incorrect and warn the user
    if current_index not in st.session_state.answers:
        st.markdown(
            """
            <div style="background-color: #fff3cd; border-left: 6px solid #ffecb5; padding: 12px 16px 12px 8px; 
            margin-bottom: 1.2rem; border-radius: 8px; font-size: 14px; line-height: 1.5;">
                <strong>⚠️ Skipped!</strong> This question was not answered and has been marked as incorrect.
            </div>
            """,
            unsafe_allow_html=True
        )
        st.session_state.wrong_answers += 1

    if current_index + 1 >= question_limit:
        st.session_state.quiz_complete = True
        return

    st.session_state.current_question += 1

    # ⏱️ Reset timer for the next question
    st.session_state.question_start_time = time.time()
    st.session_state.timer_expired = False

    if st.session_state.current_question >= len(st.session_state.questions):
        try:
            next_q = get_quiz_from_topic(topic, api_key, topic_contexts.get(topic, []))
            if not next_q or not isinstance(next_q, dict):
                st.error("Failed to load the next quiz question.")
                st.session_state.current_question -= 1
                return
            st.session_state.questions.append(next_q)
            if save_to_db and not is_duplicate_question(next_q):
                save_quiz_question(topic, next_q)

        except openai.error.AuthenticationError:
            st.error("Invalid API key.")
            st.session_state.current_question -= 1


# --- Layout: Quiz and navigation ---
col_main, col_next = st.columns([8, 1])  # Wider main area, slim right column

with col_next:
    if not st.session_state.quiz_complete and st.button("Next"):
        next_question()

with col_main:
    if st.session_state.quiz_complete:
        show_summary()
    else:
        display_question()

# --- Download quiz data ---
st.sidebar.download_button(
    "Download Quiz Data",
    data=json.dumps(st.session_state.questions, indent=4),
    file_name="quiz_session.json",
    mime="application/json",
)

# --- Close App Button ---
if st.sidebar.button("Close App"):
    st.warning("Closing app...")
    os._exit(0)  # Be cautious with this — abrupt termination
