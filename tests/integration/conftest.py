import asyncio
import pytest
from soc_deploy.bootstrap import create_context
from soc_deploy.core.engine import Orchestrator
from soc_deploy.core.state import StateManager


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def ctx():
    """Création d'un contexte réel avec DB temporaire"""
    ctx = create_context()
    # Réinitialiser la base pour chaque test
    await ctx.db.initialize()
    yield ctx
    await ctx.db.close()


@pytest.fixture
async def engine(ctx):
    state = StateManager(ctx.db, ctx.logger)
    return Orchestrator(ctx, state)
