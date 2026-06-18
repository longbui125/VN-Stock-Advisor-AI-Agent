import streamlit as st
from dotenv import load_dotenv
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from src.llm.llm_client import get_llm_and_agent, safe_invoke


def setup_page() -> None:
    st.set_page_config(
        page_title="Vietnam Stock Advisor",
        page_icon=":chart_with_upwards_trend:",
        layout="wide",
    )


def initialize_app() -> None:
    load_dotenv()
    setup_page()


def setup_chat_interface():
    st.title("Vietnam Stock Advisor")
    st.caption("Tro ly phan tich du lieu chung khoan Viet Nam")

    msgs = StreamlitChatMessageHistory(key="langchain_messages")

    if "messages" not in st.session_state:
        greeting = "Xin chao, ban muon phan tich ma co phieu nao?"
        st.session_state.messages = [{"role": "assistant", "content": greeting}]
        msgs.add_ai_message(greeting)

    for msg in st.session_state.messages:
        role = "assistant" if msg["role"] == "assistant" else "human"
        st.chat_message(role).write(msg["content"])

    return msgs


def build_chat_history() -> list:
    chat_history = []
    for msg in st.session_state.messages[:-1]:
        if msg["role"] == "human":
            chat_history.append(HumanMessage(content=msg["content"]))
        else:
            chat_history.append(AIMessage(content=msg["content"]))
    return chat_history


def handle_user_input(msgs, agent_executor) -> None:
    if prompt := st.chat_input("Hoi ve gia, BCTC, ty so tai chinh..."):
        st.session_state.messages.append({"role": "human", "content": prompt})
        st.chat_message("human").write(prompt)
        msgs.add_user_message(prompt)

        with st.chat_message("assistant"):
            response = safe_invoke(
                agent_executor,
                {
                    "input": prompt,
                    "chat_history": build_chat_history(),
                },
            )

            output = response.get("action_input", "Khong co phan hoi.")
            st.session_state.messages.append({"role": "assistant", "content": output})
            msgs.add_ai_message(output)
            st.write(output)


def main() -> None:
    initialize_app()
    msgs = setup_chat_interface()

    try:
        agent_executor = get_llm_and_agent()
    except Exception as exc:
        st.error(f"Khong khoi tao duoc agent: {exc}")
        st.stop()

    handle_user_input(msgs, agent_executor)


if __name__ == "__main__":
    main()
