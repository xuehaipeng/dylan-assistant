"""
Unit tests for Dylan Assistant tools
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.base import get_weather, calculate, get_current_time


class TestWeatherTool:
    """Test weather tool functionality"""
    
    @pytest.mark.asyncio
    async def test_get_weather_success(self):
        """Test successful weather retrieval"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "current_condition": [{
                    "temp_C": "25",
                    "FeelsLikeC": "27",
                    "weatherDesc": [{"value": "Sunny"}],
                    "humidity": "60",
                    "windspeedKmph": "15"
                }]
            }
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await get_weather("London")
            assert "Weather in London" in result
            assert "25°C" in result
            assert "Sunny" in result
    
    @pytest.mark.asyncio
    async def test_get_weather_failure(self):
        """Test weather retrieval failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await get_weather("InvalidCity123")
            assert "Could not get weather" in result


class TestCalculatorTool:
    """Test calculator tool functionality"""
    
    @pytest.mark.asyncio
    async def test_calculate_basic_operations(self):
        """Test basic mathematical operations"""
        assert "= 4" in await calculate("2 + 2")
        assert "= 6" in await calculate("2 * 3")
        assert "= 5" in await calculate("10 / 2")
        assert "= 3" in await calculate("5 - 2")
    
    @pytest.mark.asyncio
    async def test_calculate_complex_expression(self):
        """Test complex mathematical expression"""
        result = await calculate("(2 + 3) * 4 - 1")
        assert "= 19" in result
    
    @pytest.mark.asyncio
    async def test_calculate_invalid_expression(self):
        """Test invalid expression handling"""
        result = await calculate("2 + + 2")
        assert "Error" in result


class TestTimeTool:
    """Test time tool functionality"""
    
    @pytest.mark.asyncio
    async def test_get_current_time_utc(self):
        """Test getting current time in UTC"""
        result = await get_current_time()
        assert "Current time" in result
        assert "UTC" in result
    
    @pytest.mark.asyncio
    async def test_get_current_time_with_timezone(self):
        """Test getting current time with specific timezone"""
        result = await get_current_time("America/New_York")
        assert "Current time" in result
    
    @pytest.mark.asyncio
    async def test_get_current_time_invalid_timezone(self):
        """Test handling of invalid timezone"""
        result = await get_current_time("Invalid/Timezone")
        assert "UTC" in result  # Should fallback to UTC