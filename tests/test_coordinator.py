import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from chambers.coordinator import TurnCoordinator, ConfigValidator
from chambers.config import config

# Mock the Config to avoid needing real API keys
@pytest.fixture(autouse=True)
def mock_config():
    with patch('chambers.coordinator.config') as mock_cfg:
        # Setup mock models
        mock_cfg.ai_models = {
            "claude": MagicMock(enabled=True, vendor="anthropic", fallback=None),
            "gemini": MagicMock(enabled=True, vendor="google", fallback=None),
            "grok": MagicMock(enabled=True, vendor="xai", fallback=None),
        }
        yield mock_cfg

# Mock the Clients
@pytest.fixture
def mock_clients():
    with patch('chambers.coordinator.ClaudeClient') as MockClaude, \
         patch('chambers.coordinator.GeminiClient') as MockGemini, \
         patch('chambers.coordinator.GrokClient') as MockGrok:
        
        # Setup stream_response to return a generator
        async def async_gen(*args, **kwargs):
            yield "Test Response"
        
        MockClaude.return_value.stream_response = async_gen
        MockClaude.return_value.health_check = AsyncMock(return_value=True)
        
        MockGemini.return_value.stream_response = async_gen
        MockGemini.return_value.health_check = AsyncMock(return_value=True)
        
        MockGrok.return_value.stream_response = async_gen
        MockGrok.return_value.health_check = AsyncMock(return_value=True)
        
        yield {"claude": MockClaude, "gemini": MockGemini, "grok": MockGrok}

@pytest.mark.asyncio
async def test_coordinator_initialization(mock_config, mock_clients):
    coord = TurnCoordinator("test_session")
    await coord.initialize()
    
    assert len(coord.speaker_queue) == 3
    assert "claude" in coord.healthy_speakers
    assert "gemini" in coord.healthy_speakers

@pytest.mark.asyncio
async def test_mention_parsing_claude(mock_config, mock_clients):
    """Test that @Claude filters the queue."""
    coord = TurnCoordinator("test_session")
    await coord.initialize()
    
    # Inject messages
    messages = [{"role": "user", "content": "Hey @Claude, what's up?"}]
    
    # Mock execute_turn to capture who was called
    coord.execute_turn = AsyncMock(return_value="Response")
    
    await coord.run_round(messages)
    
    # Verify only Claude was called
    called_speakers = [call.args[0] for call in coord.execute_turn.call_args_list]
    assert "claude" in called_speakers
    assert "gemini" not in called_speakers
    assert len(called_speakers) == 1

@pytest.mark.asyncio
async def test_mention_parsing_multiple(mock_config, mock_clients):
    """Test @Claude and @Gemini."""
    coord = TurnCoordinator("test_session")
    await coord.initialize()
    
    messages = [{"role": "user", "content": "Tell me @Claude and @Gemini"}]
    
    coord.execute_turn = AsyncMock(return_value="Response")
    
    await coord.run_round(messages)
    
    called_speakers = [call.args[0] for call in coord.execute_turn.call_args_list]
    assert "claude" in called_speakers
    assert "gemini" in called_speakers
    assert "grok" not in called_speakers

@pytest.mark.asyncio
async def test_mention_parsing_council(mock_config, mock_clients):
    """Test @Council overrides specific mentions."""
    coord = TurnCoordinator("test_session")
    await coord.initialize()
    
    messages = [{"role": "user", "content": "@Council, please report."}]
    
    coord.execute_turn = AsyncMock(return_value="Response")
    
    await coord.run_round(messages)
    
    called_speakers = [call.args[0] for call in coord.execute_turn.call_args_list]
    assert len(called_speakers) == 3  # All 3 should be called

@pytest.mark.asyncio
async def test_subjective_history_logic(mock_config, mock_clients):
    """Test that history is transformed correctly for the speaker."""
    coord = TurnCoordinator("test_session")
    await coord.initialize()
    
    # Setup a history where Claude has already spoken
    initial_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "[Claude]: I am Claude."}
    ]
    
    # We want to see what GEMINI sees
    # We intercept the call to execute_turn
    coord.execute_turn = AsyncMock(return_value="Gemini Response")
    
    # Trigger Gemini turn (via specific mention to isolate)
    new_input = {"role": "user", "content": "@Gemini check history"}
    full_history = initial_history + [new_input]
    
    await coord.run_round(full_history)
    
    # Inspect the 'messages' passed to execute_turn
    # args: (ai_id, messages, system_prompt, callback)
    call_args = coord.execute_turn.call_args
    passed_messages = call_args[0][1]
    
    # For Gemini:
    # Claude's message should be 'user'
    # Vinga's message should be 'user'
    
    # Find Claude's message
    claude_msg = next(m for m in passed_messages if "I am Claude" in m["content"])
    assert claude_msg["role"] == "user"  # <--- The Critical Assertion
