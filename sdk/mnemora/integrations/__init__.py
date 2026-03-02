"""Framework integrations for the Mnemora SDK.

Each integration is an optional extra — import only what you need to avoid
pulling in heavy framework dependencies for users who do not use them.

Available integrations
----------------------
langgraph
    ``MnemoraCheckpointSaver`` — LangGraph ``BaseCheckpointSaver`` that
    persists graph state to Mnemora working memory.  Requires the
    ``langgraph`` extra: ``pip install 'mnemora[langgraph]'``.

langchain
    ``MnemoraMemory`` — LangChain ``BaseChatMessageHistory`` backed by
    Mnemora episodic memory.  Requires the ``langchain`` extra:
    ``pip install 'mnemora[langchain]'``.

crewai
    ``MnemoraCrewStorage`` — CrewAI ``Storage`` backend backed by Mnemora
    working memory.  Requires the ``crewai`` extra:
    ``pip install 'mnemora[crewai]'``.

Example::

    from mnemora.integrations.langgraph import MnemoraCheckpointSaver
    from mnemora.integrations.langchain import MnemoraMemory
    from mnemora.integrations.crewai import MnemoraCrewStorage
"""

from __future__ import annotations
