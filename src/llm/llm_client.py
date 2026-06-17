from __future__ import annotations

import json
import re

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from src.prompts.prompt_templates import STOCK_ADVISOR_SYSTEM_PROMPT
from src.retrieval.retriever import get_retriever
from src.utils.helpers import get_env


def get_sql_tool():
    db = SQLDatabase.from_uri(
        get_env("POSTGRES_URI", "postgresql://stocks:stocks@localhost:5432/stocks"),
        schema=get_env("POSTGRES_SCHEMA", "market_data"),
        include_tables=[
            "companies",
            "securities",
            "price_daily",
            "financial_statements",
            "financial_ratios",
            "corporate_actions",
            "text_documents",
        ],
        sample_rows_in_table_info=3,
    )
    return QuerySQLDataBaseTool(
        db=db,
        description=(
            "Execute read-only SQL SELECT queries on the Postgres market_data schema "
            "for Vietnam stock market structured data."
        ),
    )


def get_tools():
    retriever_tool = create_retriever_tool(
        get_retriever(),
        name="find",
        description=(
            "Use for semantic search over Vietnam stock text documents stored in Qdrant: "
            "disclosures, annual reports, financial statement notes, and company reports."
        ),
    )

    sql_tool = get_sql_tool()
    sql_tool.name = "sql"
    sql_tool.description = (
        "Use for structured Vietnam stock market queries in Postgres. "
        "Only write SELECT statements against the market_data schema."
    )
    return [retriever_tool, sql_tool]


def get_llm_and_agent(return_prompt: bool = False):
    llm = ChatGoogleGenerativeAI(
        model=get_env("GEMINI_MODEL", "gemini-2.5-flash"),
        temperature=0,
        streaming=True,
        google_api_key=get_env("GEMINI_API_KEY"),
    )

    tools = get_tools()
    tool_names = [tool.name for tool in tools]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", STOCK_ADVISOR_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("assistant", "{agent_scratchpad}"),
        ]
    ).partial(tools="sql, find", tool_names="sql, find")

    agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        tool_names=tool_names,
        verbose=True,
        handle_parsing_errors=True,
    )

    if return_prompt:
        return executor, STOCK_ADVISOR_SYSTEM_PROMPT
    return executor


def safe_invoke(agent_executor, input_data):
    try:
        result = agent_executor.invoke(input_data)

        if isinstance(result, dict) and "output" in result:
            output = result["output"]

            if isinstance(output, (dict, list)):
                return output

            if isinstance(output, str):
                output = re.sub(r"(?<![\s\{])(\{)", r"\n\1", output).strip()
                if output.startswith("{") and output.endswith("}"):
                    return json.loads(output)
                return {"action": "Final Answer", "action_input": output}

        return {"action": "Final Answer", "action_input": str(result)}

    except Exception as exc:
        return {
            "action": "Final Answer",
            "action_input": f"Loi khi xu ly agent: {exc}",
        }
