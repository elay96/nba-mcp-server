from typing import Any
from mcp.server.fastmcp import FastMCP
from nba_api.stats.endpoints import scoreboardv2
import pandas as pd
from datetime import date, timedelta

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

def get_game_ids():
    yesteday = date.today() - timedelta(days = 1)
    y = str(yesteday).split('-')
    y = str(y[1])+'/'+str(y[2])+'/'+str(y[0])
    s = scoreboardv2.ScoreboardV2(day_offset=-1)
    games = None
    for r in s.get_dict()['resultSets']:
        if r['name'] == 'LineScore':
            games = r
    df = pd.DataFrame(games['rowSet'], columns = games['headers']) 
    return set(df['GAME_ID'])



@mcp.tool()
async def get_game_ids_too() -> str:
    """Get the game IDs for all the games that happened yesterday."""

    return get_game_ids()
    
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')