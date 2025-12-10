import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from snowflake_connect import load_reviews
from snowflake.snowpark import Session
import google.generativeai as genai
import os

# -------------------------
# Configure Gemini API Key
# -------------------------
# Replace with your actual API key
genai.configure(api_key="AIzaSyANtNJodyCXiALBavNki7XSuh9bn6RB_JA")
MODEL_NAME = "models/gemini-2.5-flash"
gemini_model = genai.GenerativeModel(MODEL_NAME)

# -------------------------
# Streamlit page settings
# -------------------------
st.set_page_config(page_title="Snowflake Sentiment Dashboard + Gemini Chatbot", layout="wide")

# -------------------------
# Load Snowflake Data
# -------------------------
df = load_reviews()

# -------------------------
# Title and Sidebar Filters
# -------------------------
st.title("📊 Product Review Sentiment Dashboard")
st.sidebar.header("Filters")
products = st.sidebar.multiselect(
    "Select Product",
    df["PRODUCT"].unique(),
    default=df["PRODUCT"].unique()
)

filtered_df = df[df["PRODUCT"].isin(products)]

# -------------------------
# Data Preview
# -------------------------
st.subheader("📄 Data Preview")
st.dataframe(filtered_df.head())

# -------------------------
# Sentiment by Region
# -------------------------
st.subheader("🌍 Average Sentiment Score by Region")
region_sentiment = (
    filtered_df.groupby("REGION")["SENTIMENT_SCORE"]
    .mean()
    .sort_values()
)

fig, ax = plt.subplots()
region_sentiment.plot(kind="bar", ax=ax)
ax.set_ylabel("Average Sentiment")
ax.set_title("Sentiment by Region")
st.pyplot(fig)

# Regions with most negative feedback
st.write("### ❗ Regions with Most Negative Sentiment")
st.write(region_sentiment.head())

# -------------------------
# Delivery Issues (Negative Sentiment)
# -------------------------
st.subheader("🚚 Delivery Issues (Negative Sentiment)")
issues = filtered_df[
    (filtered_df["SENTIMENT_SCORE"] < 0) &
    (filtered_df["LATE"] == True)
]
issue_table = issues[["PRODUCT", "REGION", "LATE", "SENTIMENT_SCORE", "REVIEW_TEXT"]]
st.dataframe(issue_table)

# -------------------------
# Setup Snowpark Session for Cortex LLM
# -------------------------
def get_snowpark_session():
    connection_parameters = {
        "account": "CLCQTKU-OXB92104",
        "user": "Michael",
        "password": "Michaeltampoc25",
        "role": "ACCOUNTADMIN",
        "warehouse": "COMPUTE_WH"
    }
    return Session.builder.configs(connection_parameters).create()

session = get_snowpark_session()

# -------------------------
# Chatbot Section
# -------------------------
st.subheader("🤖 Chatbot Assistant")

# Choose which chatbot to use
chatbot_option = st.radio("Select Chatbot", ["Cortex LLM", "Gemini AI"])

if chatbot_option == "Cortex LLM":
    user_prompt = st.text_input("Ask about product reviews, trends, or sentiment:")
    if st.button("Send to Cortex"):
        if user_prompt.strip() != "":
            query = f"""
                SELECT snowflake.cortex.complete(
                    'llama3-70b',
                    'You are an AI assistant analyzing product reviews: {user_prompt}'
                ) AS answer;
            """
            result = session.sql(query).collect()[0]["ANSWER"]
            st.write(result)

elif chatbot_option == "Gemini AI":
    # Session state for Gemini
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display chat history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Type your message for Gemini AI..."):
        st.chat_message("user").markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # Generate Gemini response
        try:
            response = gemini_model.generate_content(prompt)
            reply = response.text
        except Exception as e:
            reply = f"Error: {e}"

        st.chat_message("assistant").markdown(reply)

        st.session_state["messages"].append({"role": "assistant", "content": reply})
