from typing import Any, Set, List, Dict
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from nba_api.stats.endpoints import (
    scoreboardv2,
    boxscoretraditionalv2,
    boxscorefourfactorsv2,
    playbyplayv2,
)
import pandas as pd

# ---------- MCP server ----------
mcp = FastMCP("nba")                    # יוצר שרת MCP
pd.set_option("display.max_rows", None)

# ---------- פונקציות עזר ----------
def get_game_ids(game_date: str | None = None) -> Set[str]:
    sb = (
        scoreboardv2.ScoreboardV2(day_offset=-1)
        if game_date is None
        else scoreboardv2.ScoreboardV2(game_date=game_date)
    )
    line_score = next(r for r in sb.get_dict()["resultSets"] if r["name"] == "LineScore")
    df = pd.DataFrame(line_score["rowSet"], columns=line_score["headers"])
    return set(df["GAME_ID"])


def get_game_box_score(game_id: str) -> pd.DataFrame:
    game = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id).get_dict()[
        "resultSets"
    ][0]
    return pd.DataFrame(game["rowSet"], columns=game["headers"])


def get_final_score(game_df: pd.DataFrame) -> Dict[str, int]:
    teams = list(game_df["TEAM_ABBREVIATION"].unique())
    return {
        teams[0]: int(game_df[game_df["TEAM_ABBREVIATION"] == teams[0]]["PTS"].sum()),
        teams[1]: int(game_df[game_df["TEAM_ABBREVIATION"] == teams[1]]["PTS"].sum()),
    }


def get_play_by_play_data(game_id: str) -> pd.DataFrame:
    data = playbyplayv2.PlayByPlayV2(game_id=game_id).get_dict()["resultSets"][0]
    df = pd.DataFrame(data["rowSet"], columns=data["headers"])
    return df[
        ["WCTIMESTRING", "HOMEDESCRIPTION", "NEUTRALDESCRIPTION", "VISITORDESCRIPTION", "SCORE"]
    ]


def filter_to_pra_columns(game_df: pd.DataFrame) -> pd.DataFrame:
    return game_df[["PLAYER_NAME", "TEAM_CITY", "PTS", "REB", "AST"]]


def filter_to_full_columns(game_df: pd.DataFrame) -> pd.DataFrame:
    return game_df[
        [
            "PLAYER_NAME",
            "TEAM_CITY",
            "PTS",
            "REB",
            "AST",
            "STL",
            "BLK",
            "TO",
            "PLUS_MINUS",
            "MIN",
        ]
    ]

# ---------- MCP tools ----------
@mcp.tool()
async def get_game_ids_tool(game_date: str | None = None) -> Set[str]:
    """Return game IDs for the given date (yesterday if not provided)."""
    return get_game_ids(game_date)


@mcp.tool()
async def get_game_scores(game_date: str | None = None) -> List[Dict[str, int]]:
    """Return final scores for all games on a date (yesterday if not provided)."""
    return [get_final_score(get_game_box_score(gid)) for gid in get_game_ids(game_date)]


@mcp.tool()
async def get_four_factors(game_date: str | None = None) -> List[dict]:
    """Return Four Factors for each game on the date requested."""
    results = []
    for gid in get_game_ids(game_date):
        raw = boxscorefourfactorsv2.BoxScoreFourFactorsV2(game_id=gid).get_dict()[
            "resultSets"
        ][1]
        df = pd.DataFrame(raw["rowSet"], columns=raw["headers"])
        results.append(
            {
                row["TEAM_ABBREVIATION"]: [
                    row["EFG_PCT"],
                    row["FTA_RATE"],
                    row["TM_TOV_PCT"],
                    row["OREB_PCT"],
                ]
                for _, row in df.iterrows()
            }
        )
    return results


@mcp.tool()
async def get_pra_breakdown(game_date: str | None = None) -> List[str]:
    """Return CSV strings of PTS-REB-AST for every game on the date."""
    return [
        filter_to_pra_columns(get_game_box_score(gid)).to_csv(index=False)
        for gid in get_game_ids(game_date)
    ]


@mcp.tool()
async def get_full_breakdown(game_date: str | None = None) -> List[str]:
    """Return full box-score CSV strings for every game on the date."""
    return [
        filter_to_full_columns(get_game_box_score(gid)).to_csv(index=False)
        for gid in get_game_ids(game_date)
    ]


@mcp.tool()
async def get_play_by_play(game_id: str) -> str:
    """Return play-by-play CSV for the given game ID."""
    return get_play_by_play_data(game_id).to_csv(index=False)

# ---------- FastAPI app ----------
app = FastAPI(title="NBA MCP Server", description="NBA data server for MCP")

# ברירת המחדל של FastMCP בגרסאות 2.3 ומעלה – נתיב /mcp
app.mount("/mcp", mcp.http_app())

# בריאות בסיסית
@app.get("/")
async def root():
    return {"message": "NBA MCP Server is running", "status": "healthy"}

# ---------- הרצה מקומית בלבד ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("nba:app", host="0.0.0.0", port=8000, reload=True)
