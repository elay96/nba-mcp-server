from typing import Any
from mcp.server.fastmcp import FastMCP
from nba_api.stats.endpoints import scoreboardv2, boxscoretraditionalv2
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


def get_game_box_score(game_id: int) -> Any:
    game = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id).get_dict()['resultSets'][0]
    df = pd.DataFrame(game['rowSet'], columns = game['headers']) 
    print(df)
    return df 

def get_final_score(game: Any) -> dict:
    teams = set (game['TEAM_ABBREVIATION'] )
    team_1_name = teams.pop()
    team_2_name = teams.pop()
    team_1 = game[game['TEAM_ABBREVIATION'] == team_1_name]
    team_2 = game[game['TEAM_ABBREVIATION'] == team_2_name]
    team_1_pts = int(team_1['PTS'].sum())
    team_2_pts = int(team_2['PTS'].sum())
    return {team_1_name: team_1_pts, team_2_name: team_2_pts}

@mcp.tool()
async def get_game_ids_tool() -> str:
    """Get the game IDs for all the games that happened yesterday."""

    return get_game_ids()

@mcp.tool()
async def get_game_score() -> str:
    """Get the score for a game It should be of the format Team 1: Score 1 - Team 2: Score 2. It would be great if claude to take the team name and return the full name, for example if dict 1 item is Memphis it would be great if it could return Memphis Grizzlies"""
    for gid in get_game_ids():
        d = get_final_score(get_game_box_score(gid))

    return d

@mcp.tool()
async def get_game_scores() -> list:
    """Get the score for all games that happened yesterady. It should be of the format Team 1: Score 1 - Team 2: Score 2. It would be great if claude to take the team name and return the full name, for example if dict 1 item is Memphis it would be great if it could return Memphis Grizzlies"""
    scores = []
    for gid in get_game_ids():
        d = get_final_score(get_game_box_score(gid))
        scores.append(d)

    return scores

    
if __name__ == "__main__":

    for gid in get_game_ids():
        print(get_final_score(get_game_box_score(gid)))
    # Initialize and run the server
    mcp.run(transport='stdio')