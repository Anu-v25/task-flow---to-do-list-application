import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
import openai

# --- AI Setup ---
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- File paths ---
TASK_FILE = "tasks.csv"
USER_FILE = "users.csv"

# --- Themes ---
THEMES = {
    "Nature": "https://images.unsplash.com/photo-1506748686214-e9df14d4d9d0",
    "Sky": "https://images.unsplash.com/photo-1506744038136-46273834b3fb",
    "Dark Abstract": "https://images.unsplash.com/photo-1581349482625-368a64dc9f4b",
    "Office": "https://images.unsplash.com/photo-1587614203976-365c74645e83"
}

# --- Set background image ---
def set_bg_from_url(url):
    st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("{url}");
            background-attachment: fixed;
            background-size: cover;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- AI Tool ---
def run_ai_assistant(prompt, tasks_df):
    task_summary = tasks_df.to_string(index=False)
    full_prompt = f"""You are a task assistant. Here's the user's task list:\n{task_summary}\n\nUser asked: {prompt}\n\nRespond in a helpful way."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": full_prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# --- Load/save users ---
def load_users():
    return pd.read_csv(USER_FILE) if os.path.exists(USER_FILE) else pd.DataFrame(columns=["username", "password"])

def save_user(username, password):
    users = load_users()
    new_user = pd.DataFrame([[username, password]], columns=["username", "password"])
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv(USER_FILE, index=False)

# --- Load/save tasks ---
def load_tasks():
    return pd.read_csv(TASK_FILE, parse_dates=["Entry Date", "Exit Date"]) if os.path.exists(TASK_FILE) else pd.DataFrame(columns=["Title", "Priority", "Entry Date", "Exit Date", "Status"])

def save_tasks(df):
    df.to_csv(TASK_FILE, index=False)

# --- Color utilities ---
def get_row_color(priority):
    return {
        "High": "background-color: #FFCCCC;",
        "Medium": "background-color: #FFF2CC;",
        "Low": "background-color: #D9EAD3;"
    }.get(priority, "")

def color_text_by_status(val):
    return {
        "Pending": "color: red;",
        "In-Progress": "color: orange;",
        "Completed": "color: green;"
    }.get(val, "")

def priority_to_stars(priority):
    return "⭐" * {"High": 3, "Medium": 2, "Low": 1}[priority]

# --- Page config ---
st.set_page_config(page_title="AI Task Manager", layout="wide")

# --- Session state ---
for key in ["logged_in", "username", "show_register"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "logged_in" else ""

# --- Background theme ---
theme_choice = st.sidebar.selectbox("🎨 Background Theme", list(THEMES.keys()))
set_bg_from_url(THEMES[theme_choice])

# --- Register ---
if st.session_state.show_register:
    st.title("📝 Register")
    with st.form("Register"):
        new_user = st.text_input("Username")
        new_pass = st.text_input("Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")

        if submit:
            users = load_users()
            if new_user in users["username"].values:
                st.error("Username exists.")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match.")
            elif not new_user or not new_pass:
                st.error("Username and password required.")
            else:
                save_user(new_user, new_pass)
                st.success("Registered! Please log in.")
                st.session_state.show_register = False
                st.rerun()

    if st.button("Back to Login"):
        st.session_state.show_register = False
        st.rerun()

# --- Login ---
elif not st.session_state.logged_in:
    st.title("🔐 Login")
    with st.form("Login"):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            users = load_users()
            if user in users["username"].values:
                real_pw = users[users["username"] == user]["password"].values[0]
                if pw == real_pw:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.rerun()
                else:
                    st.error("Wrong password.")
            else:
                st.error("User not found.")

    if st.button("Register"):
        st.session_state.show_register = True
        st.rerun()

# --- Main App ---
else:
    st.sidebar.success(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("📋 Task Manager with AI")
    tasks = load_tasks()

    # --- Add Task ---
    with st.form("Add Task"):
        st.subheader("➕ Add Task")
        title = st.text_input("Task Title")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        entry = st.date_input("Entry Date", datetime.today())
        exit = st.date_input("Exit Date", datetime.today())
        if st.form_submit_button("Add"):
            new = {
                "Title": title,
                "Priority": priority,
                "Entry Date": pd.to_datetime(entry),
                "Exit Date": pd.to_datetime(exit),
                "Status": "Pending"
            }
            tasks = pd.concat([tasks, pd.DataFrame([new])], ignore_index=True)
            save_tasks(tasks)
            st.success("Task added!")

    # --- Show Tasks ---
    st.subheader("📌 Your Tasks")
    if not tasks.empty:
        tasks["Stars"] = tasks["Priority"].apply(priority_to_stars)

        def highlight(row): return [get_row_color(row.Priority)] * len(row)
        styled = tasks.style.apply(highlight, axis=1).applymap(color_text_by_status, subset=["Status"])
        st.dataframe(styled, use_container_width=True)
    else:
        st.info("No tasks added yet.")

    # --- Edit/Delete ---
    st.subheader("✏️ Edit / Delete")
    if not tasks.empty:
        selected = st.selectbox("Select task", tasks["Title"])
        idx = tasks[tasks["Title"] == selected].index[0]

        new_title = st.text_input("Title", tasks.loc[idx, "Title"])
        new_pri = st.selectbox("Priority", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(tasks.loc[idx, "Priority"]))
        new_ent = st.date_input("Entry", tasks.loc[idx, "Entry Date"])
        new_ext = st.date_input("Exit", tasks.loc[idx, "Exit Date"])
        new_stat = st.selectbox("Status", ["Pending", "In-Progress", "Completed"], index=["Pending", "In-Progress", "Completed"].index(tasks.loc[idx, "Status"]))

        if st.button("Update Task"):
            tasks.loc[idx] = [new_title, new_pri, new_ent, new_ext, new_stat]
            save_tasks(tasks)
            st.success("Updated!")

        if st.button("Delete Task"):
            tasks = tasks.drop(idx).reset_index(drop=True)
            save_tasks(tasks)
            st.warning("Deleted!")

    # --- Charts ---
    st.subheader("📊 Task Overview")
    if not tasks.empty:
        stats = tasks["Status"].value_counts().reset_index()
        stats.columns = ["Status", "Count"]
        fig = px.pie(stats, names='Status', values='Count', title="Task Status Distribution")
        st.plotly_chart(fig, use_container_width=True)

    # --- AI Assistant ---
    st.subheader("🤖 AI Assistant")
    if not tasks.empty:
        user_query = st.text_area("Ask the AI about your tasks:")
        if st.button("Ask"):
            with st.spinner("Thinking..."):
                ai_response = run_ai_assistant(user_query, tasks)
                st.markdown(f"**AI Says:** {ai_response}")
