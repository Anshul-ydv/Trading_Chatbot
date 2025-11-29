from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .config import get_settings
from .data.news_fetcher import fetch_news
from .fa_engine import FundamentalSummary
from .llm_client import LLMClient
from .rag_index import Document, LocalRAGIndex, bootstrap_default_corpus
from .strategy_engine import StrategyResult
from .utils import get_logger

logger = get_logger(__name__)


@dataclass
class ChatAgent:
    """Lightweight RAG-style agent that crafts educational responses."""

    persona: str = "university demo"

    def __post_init__(self) -> None:
        self.settings = get_settings()
        self.index = LocalRAGIndex(self.settings)
        self.llm_client = LLMClient(self.settings)
        bootstrap_default_corpus(self.index)

    def ingest_analysis(self, notes: Iterable[str], source: str = "notebook") -> None:
        docs = [Document(text=n, source=source) for n in notes]
        self.index.add_documents(docs)

    def explain(
        self,
        ticker: str,
        strategy: StrategyResult,
        fundamentals: FundamentalSummary,
        user_question: Optional[str] = None,
    ) -> str:
        prompt = user_question or f"Explain {ticker} {strategy.strategy} decision"
        
        # Handle basic/conversational queries immediately
        q_lower = (user_question or "").lower().strip()
        basic_greetings = {"hi", "hello", "hey", "help", "what can you do", "start", "good morning", "good evening"}
        if q_lower in basic_greetings:
            return (
                f"Hello! I am your AI Trading Assistant. I can help you analyze stocks like {ticker}.\n\n"
                "**What I can do:**\n"
                "- **Analyze Fundamentals:** Ask 'fundamentals for {ticker}'\n"
                "- **Technical Strategy:** Ask 'support levels' or 'strategy'\n"
                "- **Latest News:** Ask 'news for {ticker}'\n\n"
                f"Currently, I'm looking at **{ticker}**. How can I help you with it?"
            )

        context_docs = self.index.query(prompt, top_k=3)
        context_text = "\n- ".join(doc.text for doc in context_docs)
        
        # Fetch news
        news_items = fetch_news(ticker)
        
        sections = [
            f"Ticker: {ticker}",
            f"Strategy: {strategy.strategy} (score {strategy.score}/100)",
            f"Entry/Stop/Target: {strategy.entry} / {strategy.stop} / {strategy.target}",
            "Reasons:",
        ]
        sections.extend(f"  - {reason}" for reason in strategy.reasons)
        sections.append("Fundamentals:")
        for key, value in fundamentals.metrics.items():
            sections.append(f"  - {key}: {value}")
            
        if news_items:
            sections.append("Recent News:")
            for item in news_items:
                sections.append(f"  - {item['title']} ({item['published']})")
                
        if context_text:
            sections.append("Context snippets:\n- " + context_text)
        sections.append("Safety: Educational example only; not investment advice.")

        llm_prompt = self._build_prompt(prompt, ticker, strategy, fundamentals, context_docs, sections, news_items)
        llm_response = self.llm_client.generate(llm_prompt)
        if llm_response and llm_response.text:
            return llm_response.text.strip()
            
        # Fallback: Smart Template Response based on user question
        q = (user_question or "").lower()
        
        # 1. News Query
        if "news" in q:
            if not news_items:
                return f"I couldn't find any recent news for {ticker} at the moment. However, technically, I see a {strategy.strategy} setup."
            headlines = "\n".join([f"- {n['title']} ({n['published']})" for n in news_items[:3]])
            return (
                f"Here are the latest news headlines for {ticker}:\n\n{headlines}\n\n"
                f"In terms of price action, I'm tracking a {strategy.strategy} setup with a target of {strategy.target}."
            )

        # 2. Fundamental Query
        if "fundamental" in q or "valuation" in q or "pe ratio" in q or "profit" in q:
            # Format metrics into a Markdown table
            rows = []
            for k, v in fundamentals.metrics.items():
                # Format value: round floats to 2 decimals
                val_str = str(v)
                if isinstance(v, (float, int)):
                    val_str = f"{v:.2f}"
                rows.append(f"| {k.replace('_', ' ').title()} | {val_str} |")
            
            table_str = "| Metric | Value |\n| --- | --- |\n" + "\n".join(rows)
            
            return (
                f"### Fundamental Snapshot for {ticker}\n\n"
                f"{table_str}\n\n"
                f"**Analysis**\n"
                f"* **Overall Score**: {fundamentals.score}/100\n"
                f"* **Strengths**: {', '.join(fundamentals.strengths) if fundamentals.strengths else 'None detected'}\n"
                f"* **Risks**: {', '.join(fundamentals.risks) if fundamentals.risks else 'None detected'}"
            )

        # 3. Technical/Support/Levels Query
        if "support" in q or "resistance" in q or "level" in q or "target" in q or "stop" in q:
            return (
                f"For {ticker}, the technical outlook is a '{strategy.strategy}' setup.\n\n"
                f"**Key Levels:**\n"
                f"- Entry: {strategy.entry}\n"
                f"- Stop Loss: {strategy.stop}\n"
                f"- Target: {strategy.target}\n\n"
                f"**Technical Rationale:**\n"
                f"{'; '.join(strategy.reasons)}."
            )

        # 4. Default / General Summary
        reasons_text = "; ".join(strategy.reasons).lower()
        fund_text = ", ".join(f"{k}: {v}" for k, v in fundamentals.metrics.items())
        news_text = ""
        if news_items:
            news_text = " Recent news headlines: " + "; ".join([f"'{n['title']}'" for n in news_items[:2]]) + "."
        
        return (
            f"Based on my analysis of {ticker}, I recommend a '{strategy.strategy}' strategy with a confidence score of {strategy.score}/100. "
            f"The suggested entry price is {strategy.entry}, with a stop-loss at {strategy.stop} and a target of {strategy.target}. "
            f"Key technical factors include: {reasons_text}. "
            f"On the fundamental side: {fund_text}.{news_text} "
            "Please note this is for educational purposes only and not financial advice."
        )

    def _build_prompt(
        self,
        question: str,
        ticker: str,
        strategy: StrategyResult,
        fundamentals: FundamentalSummary,
        context_docs: list[Document],
        sections: list[str],
        news_items: list[dict],
    ) -> str:
        context_block = "\n".join(f"- {doc.text} (source: {doc.source})" for doc in context_docs) or "- n/a"
        fundamentals_block = "\n".join(
            f"- {key}: {value}"
            for key, value in fundamentals.metrics.items()
        ) or "- no fundamentals"
        reasons_block = "\n".join(f"- {reason}" for reason in strategy.reasons) or "- no reasons"
        news_block = "\n".join(f"- {n['title']} ({n['published']})" for n in news_items) or "- no recent news"
        
        prompt = f"""You are an educational trading assistant named {self.persona}.
Use the provided technical/fundamental data to craft an explainable response for university evaluators.

CRITICAL INSTRUCTION:
- DO NOT write paragraphs.
- Use ONLY bullet points and tables.
- If you write a paragraph, the system will fail.

Structure your response EXACTLY as follows:

### Recommendation
* **Strategy**: {strategy.strategy}
* **Score**: {strategy.score}/100
* **Action**: Buy/Sell/Wait

### Key Levels
| Level | Price |
| --- | --- |
| Entry | {strategy.entry} |
| Stop Loss | {strategy.stop} |
| Target | {strategy.target} |

### Technical Analysis
* **Indicators**:
{reasons_block}

### Fundamental Snapshot
| Metric | Value |
| --- | --- |
{fundamentals_block}

### News & Risks
* **News**:
{news_block}

Question: {question}
Ticker: {ticker}
Strategy: {strategy.strategy} (score {strategy.score}/100)
Entry: {strategy.entry} | Stop: {strategy.stop} | Target: {strategy.target}
Reasons:
{reasons_block}
Fundamentals:
{fundamentals_block}
Recent News:
{news_block}
Retrieved context:
{context_block}

If information is missing, state the limitation explicitly in a bullet point.
"""
        prompt += "\nRaw sections for reference:\n" + "\n".join(sections)
        return prompt
