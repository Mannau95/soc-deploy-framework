import asyncio

import pytest
import pytest_asyncio  # ajouter l'import

from soc_deploy.bootstrap import create_context
from soc_deploy.core.engine import Orchestrator
from soc_deploy.core.state import StateManager


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def ctx():
    """Création d'un contexte réel avec DB temporaire"""
    ctx = await create_context()  # ajouter await
    # Réinitialiser la base pour chaque test
    await ctx.db.initialize()
    yield ctx
    await ctx.db.close()


@pytest.fixture
async def engine(ctx):
    state = StateManager(ctx.db, ctx.logger)
    return Orchestrator(ctx, state)
