from typing import Any
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.types import Tool, TextContent
from nba_api.stats.endpoints import scoreboardv2, boxscoretraditionalv2, boxscorefourfactorsv2, playbyplayv2
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import json

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
    """Get the score for a all games, that happened on a date, if no date is provided it gets the score of all games that happened yesterday."""
    game_scores = []
    for game_id in get_game_ids(game_date):
        game_scores.append(get_final_score(get_game_box_score(game_id)))
    return game_scores

@mcp.tool()
async def get_four_factors(game_filter=None, table_view=False, claude_summary=False) -> dict:
    """Get the four factors for all games that happened yesterday."""
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
    """Get the points rebounds and assists for all players that played in all games."""
    games = []
    for game_id in get_game_ids(game_date):
        game = filter_to_pra_columns(get_game_box_score(game_id)).to_csv()
        games.append(game)
    return games

@mcp.tool()
async def get_full_breakdown(game_date=None, game_filter=None, table_view=False, claude_summary=False) -> list:
    """Returns the full stats breakdown for all players."""
    games = []
    for game_id in get_game_ids(game_date):
        game = filter_to_full_columns(get_game_box_score(game_id)).to_csv()
        games.append(game)
    return games

@mcp.tool()
async def get_play_by_play(game_id: str) -> list:
    """Returns the play by play data from a game."""
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

# MCP over HTTP endpoints
@app.post("/mcp")
async def mcp_main(request: Request):
    """Main MCP endpoint that handles all MCP requests"""
    body = await request.json()
    method = body.get("method")
    
    if method == "initialize":
        return await mcp_initialize_handler(body)
    elif method == "tools/list":
        return await mcp_tools_list_handler(body)
    elif method == "tools/call":
        return await mcp_tools_call_handler(body)
    else:
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
@app.post("/mcp/tools/call")
async def mcp_tools_call(request: Request):
    """Call an MCP tool"""
    body = await request.json()
    return await mcp_tools_call_handler(body)

async def mcp_initialize_handler(body):
    """MCP initialization handler"""
    return {
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "nba-mcp-server",
                "version": "0.1.0"
            }
        }
    }

@app.post("/mcp/initialize")
async def mcp_initialize(request: Request):
    """MCP initialization endpoint"""
    body = await request.json()
    return {
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "nba-mcp-server",
                "version": "0.1.0"
            }
        }
    }

async def mcp_tools_list_handler(body):
    """List available MCP tools handler"""
    tools = [
        {
            "name": "get_game_scores",
            "description": "Get the score for all games that happened on a date",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "game_date": {"type": "string", "description": "Game date in yyyy/mm/dd format"},
                    "game_filter": {"type": "string", "description": "Filter for specific game"},
                    "claude_summary": {"type": "boolean", "description": "Whether to include summary"}
                }
            }
        },
        {
            "name": "get_pra_breakdown",
            "description": "Get points, rebounds, assists for all players",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "game_date": {"type": "string", "description": "Game date in yyyy/mm/dd format"},
                    "game_filter": {"type": "string", "description": "Filter for specific game"},
                    "table_view": {"type": "boolean", "description": "Display in table format"},
                    "claude_summary": {"type": "boolean", "description": "Whether to include summary"}
                }
            }
        },
        {
            "name": "get_full_breakdown",
            "description": "Get full stats breakdown for all players",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "game_date": {"type": "string", "description": "Game date in yyyy/mm/dd format"},
                    "game_filter": {"type": "string", "description": "Filter for specific game"},
                    "table_view": {"type": "boolean", "description": "Display in table format"},
                    "claude_summary": {"type": "boolean", "description": "Whether to include summary"}
                }
            }
        },
        {
            "name": "get_four_factors",
            "description": "Get four factors for games",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "game_filter": {"type": "string", "description": "Filter for specific game"},
                    "table_view": {"type": "boolean", "description": "Display in table format"},
                    "claude_summary": {"type": "boolean", "description": "Whether to include summary"}
                }
            }
        }
    ]
    
    return {
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "result": {"tools": tools}
    }

@app.post("/mcp/tools/list")
async def mcp_tools_list(request: Request):
    """List available MCP tools"""
    body = await request.json()
    return await mcp_tools_list_handler(body)

async def mcp_tools_call_handler(body):
    """Call an MCP tool handler"""
    tool_name = body["params"]["name"]
    arguments = body["params"].get("arguments", {})
    
    try:
        if tool_name == "get_game_scores":
            result = await get_game_scores(**arguments)
        elif tool_name == "get_pra_breakdown":
            result = await get_pra_breakdown(**arguments)
        elif tool_name == "get_full_breakdown":
            result = await get_full_breakdown(**arguments)
        elif tool_name == "get_four_factors":
            result = await get_four_factors(**arguments)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {
                "code": -32000,
                "message": str(e)
            }
        }

# Regular API endpoints for testing
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
    import os
    
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        mcp.run(transport='stdio')
    else:
        port = int(os.getenv('PORT', 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
