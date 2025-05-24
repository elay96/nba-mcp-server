from typing import Any
from mcp.server.fastmcp import FastMCP
from nba_api.stats.endpoints import scoreboardv2, boxscoretraditionalv2, boxscorefourfactorsv2, playbyplayv2
import pandas as pd
from fastapi import FastAPI
import uvicorn

# Initialize FastMCP server
mcp = FastMCP("nba")
pd.set_option('display.max_rows', None)

def get_game_ids(game_date: str = None) -> set:
    if(game_date is None):
        s = scoreboardv2.ScoreboardV2(day_offset=-1)
    else:
        s = scoreboardv2.ScoreboardV2(game_date=game_date)
    games = None
    for r in s.get_dict()['resultSets']:
        if r['name'] == 'LineScore':
            games = r
    dataframe = pd.DataFrame(games['rowSet'], columns = games['headers']) 
    return set(dataframe['GAME_ID'])

def get_game_box_score(game_id: int) -> Any:
    game = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id).get_dict()['resultSets'][0]
    dataframe = pd.DataFrame(game['rowSet'], columns = game['headers']) 
    return dataframe 

def get_final_score(game: Any) -> dict:
    teams = set (game['TEAM_ABBREVIATION'] )
    team_1_name = teams.pop()
    team_2_name = teams.pop()
    team_1 = game[game['TEAM_ABBREVIATION'] == team_1_name]
    team_2 = game[game['TEAM_ABBREVIATION'] == team_2_name]
    team_1_pts = int(team_1['PTS'].sum())
    team_2_pts = int(team_2['PTS'].sum())
    return {team_1_name: team_1_pts, team_2_name: team_2_pts}

def get_play_by_play_data(game_id: str) -> Any:
    data = playbyplayv2.PlayByPlayV2(game_id=game_id).get_dict()['resultSets'][0]
    dataframe = pd.DataFrame(data['rowSet'], columns = data['headers'])
    return dataframe[['WCTIMESTRING', 'HOMEDESCRIPTION', 'NEUTRALDESCRIPTION', 'VISITORDESCRIPTION', 'SCORE']]


def filter_to_pra_columns(game: Any) -> Any:
    return game[['PLAYER_NAME', 'TEAM_CITY', 'PTS', 'REB', 'AST']]

def filter_to_full_columns(game: Any) -> Any:
    return game[['PLAYER_NAME', 'TEAM_CITY', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PLUS_MINUS', 'MIN']]


@mcp.tool()
async def get_game_ids_tool() -> str:
    """Get the game IDs for all the games that happened yesterday."""
    return get_game_ids()

@mcp.tool()
async def get_game_scores(game_date=None, game_filter=None, claude_summary=False) -> list:
    """Get the score for a all games, that happened on a date, if no date is provided it gets the score of all games that happened yesterday.
    No matter how the date is provided claude must format it to be 'yyyy/mm/dd' when it passes it into get game ids. 
    It should be of the format Team 1: Score 1 - Team 2: Score 2. 
    It should take the team name and return the full name, for example if dict 1 item is Memphis it would be great if it could return Memphis Grizzlies
    It can take an optional game title, for example 'Memphis Grizzlies game' or 'lakers game', in which case it should only return the score for that game. 
    It can take an optional boolean, claude_summary, if this is false claude should only provide the scores and no other information, if it is true claude should give a little blurb."""
    game_scores = []
    for game_id in get_game_ids(game_date):
        game_scores.append(get_final_score(get_game_box_score(game_id)))

    return game_scores

@mcp.tool()
async def get_four_factors(game_filter=None, table_view=False, claude_summary=False) -> dict:
    """Get the score for all games that happened yesterday. 
    It should start with a bolded title of the two teams that played, for example Memphis Grizzles - Los Angles Lakers and then list the four factors underneath. 
    It can take an optional game title, for example 'Memphis Grizzlies game' or 'lakers game', in which case it should only return the four factors for that game.'
    It can take the option to display the data in a table view as well.
    It can take an optional boolean, claude_summary, if this is false claude should only provide the scores and no other information, if it is true claude should give a little blurb."""
    game_ids = get_game_ids()
    four_factors = []

    for game_id in game_ids:
        game = boxscorefourfactorsv2.BoxScoreFourFactorsV2(game_id=game_id).get_dict()['resultSets'][1]
        dataframe = pd.DataFrame(game['rowSet'], columns = game['headers'])
        filtered_dictionary = {}
        for index, row in dataframe.iterrows():
            filtered_dictionary[row['TEAM_ABBREVIATION']] = [row['EFG_PCT'], row['FTA_RATE'], row['TM_TOV_PCT'], row['OREB_PCT']]
        four_factors.append(filtered_dictionary)

    return four_factors

@mcp.tool()
async def get_pra_breakdown(game_date=None, game_filter=None, table_view=False, claude_summary=False) -> list:
    """Get the points rebounds and assists for all players that played in all games that happened yesterday. 
    It should start with a bolded title of the two teams that played, for example Memphis Grizzles - Los Angles Lakers and then list the four factors underneath. 
    It can take an optional game title, for example 'Memphis Grizzlies game' or 'lakers game', in which case it should only return the four factors for that game.'
    It can take the option to display the data in a table view as well, if it is a table view it should be two tables, one for each team.
    It can take an optional game date, which would be the day the games happened on. If it is not provided then we will fetch yesterdays games. No matter how the date is provided claude must format it to be 'yyyy/mm/dd' when it passes it into get game ids. 
    It can take an optional boolean, claude_summary, if this is false claude should only provide the scores and no other information, if it is true claude should give a little blurb."""
    games = []
    for game_id in get_game_ids(game_date):
        game = filter_to_pra_columns(get_game_box_score(game_id)).to_csv()
        games.append(game)

    return games

@mcp.tool()
async def get_full_breakdown(game_date=None, game_filter=None, table_view=False, claude_summary=False) -> list:
    """Returns the points rebounds, assists steals, blocks, plus minus, turn overs, personal fouls played for all players that played in all games that happened yesterday. 
    It should start with a bolded title of the two teams that played, for example Memphis Grizzles - Los Angles Lakers and then list the four factors underneath. 
    It can take an optional game title, for example 'Memphis Grizzlies game' or 'lakers game', in which case it should only return the four factors for that game.'
    It can take the option to display the data in a table view as well - defaults as False, if it is a table view it should be two tables, one for each team.
    It can take an optional boolean, claude_summary - DEFAULTS TO False, if this is false claude should only provide the scores and no other information, no notes or anything, if it is true claude should give a little blurb.
    It can take an optional game date, which would be the day the games happened on. If it is not provided then we will fetch yesterdays games. No matter how the date is provided claude must format it to be 'yyyy/mm/dd' when it passes it into get game ids. 
    """
    games = []
    for game_id in get_game_ids(game_date):
        game = filter_to_full_columns(get_game_box_score(game_id)).to_csv()
        games.append(game)

    return games

#This is still a WIP
@mcp.tool()
async def get_play_by_play(game_id: str) -> list:
    "Returns the play by play data from a game, Claude should serve this an easy to read format but it should serve the full data, it should not shorten it in any way"
    pbp = get_play_by_play_data(game_id)
    return pbp.to_csv()

# Create FastAPI app for web deployment
app = FastAPI(title="NBA MCP Server", description="NBA data server for Claude MCP")

@app.get("/")
async def root():
    return {"message": "NBA MCP Server is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Add some basic API endpoints for testing
@app.get("/games/scores")
async def api_get_game_scores(game_date: str = None):
    """API endpoint to get game scores"""
    return await get_game_scores(game_date=game_date)

@app.get("/games/pra")
async def api_get_pra_breakdown(game_date: str = None):
    """API endpoint to get PRA breakdown"""
    return await get_pra_breakdown(game_date=game_date)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        # Run as MCP server
        mcp.run(transport='stdio')
    else:
        # Run as web server
        uvicorn.run(app, host="0.0.0.0", port=8000)
