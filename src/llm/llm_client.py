from __future__ import annotations

import json
import re

from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.prompts.prompt_templates import STOCK_ADVISOR_SYSTEM_PROMPT
from src.retrieval.retriever import get_retriever
from src.utils.helpers import get_env


def _bool_env(name: str, default: str = "false") -> bool:
    return get_env(name, default).strip().lower() in {"1", "true", "yes", "on"}


def get_chat_model():
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=get_env("OLLAMA_MODEL", "qwen3:8b"),
        base_url=get_env("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )


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
            "Use FIRST for qualitative Vietnam company context stored in Qdrant: "
            "company overview, business model, operating fields, company profile, "
            "management, shareholders, risks, disclosures, annual reports, and company reports. "
            "Prefer this tool for questions like 'FPT la cong ty gi?', 'hoat dong linh vuc nao?', "
            "'tong quan cong ty', or any stock analysis requiring business context. "
            "For deep analysis or buy/sell/hold questions, query broadly with symbol plus terms such as "
            "tong quan, mo hinh kinh doanh, lich su, rui ro, ban lanh dao, co dong, von dieu le."
        ),
    )

    sql_tool = get_sql_tool()
    sql_tool.name = "sql"
    sql_tool.description = (
        "Use for structured Vietnam stock market queries in Postgres: prices, OHLCV, "
        "volume, rankings, counts, financial statements, ratios, and corporate actions. "
        "Only write SELECT statements against the market_data schema. "
        "For buy/sell/hold or 'buy today' questions, use this tool to get latest price, "
        "latest available trade_date, recent close prices, recent 60-session trend, and liquidity. "
        "Do not use this as the only tool for company overview or business model questions; "
        "if company metadata is blank or incomplete, call find next."
    )
    return [retriever_tool, sql_tool]


def get_llm_and_agent(return_prompt: bool = False):
    llm = get_chat_model()

    tools = get_tools()
    tool_names = [tool.name for tool in tools]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", STOCK_ADVISOR_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            (
                "human",
                "{input}\n\n{agent_scratchpad}\n\n"
                "Reminder: respond with exactly one JSON blob action. "
                "Use Final Answer when you are ready to answer the user.",
            ),
        ]
    )

    agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        tool_names=tool_names,
        verbose=_bool_env("AGENT_VERBOSE", "false"),
        max_iterations=int(get_env("AGENT_MAX_ITERATIONS", "6")),
        handle_parsing_errors=(
            "Invalid format. Return exactly one JSON blob with action and action_input. "
            "Use action \"Final Answer\" for the final response."
        ),
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
