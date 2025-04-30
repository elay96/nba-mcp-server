# NBA MCP Server

## Description
An MCP server for Anthropic's Claude LLM that allows the model to fetch recent NBA games and stats that it struggles to currently. It does this using the opensource [nba_api](https://pypi.org/project/nba_api/)

## Installation
Run these steps in the directory where you have cloned the repo
```bash
uv venv
.venv\Scripts\activate
uv pip install -e .
```

Then add the configuration to your Claude config as you would for any other MCP Server. 

## Features
- Fetch the fetch the final score for all game(s) that happened yesterday / in the past
- Fetch the basic P/R/A breakdown for all players that played in game(s) that happened yesterday / in the past
- Fetch the full PTS/REB/AST/STL/BLK/TO/PLUS_MINUS/MIN that happened yesterday / in the past
- Fetch the four factors for all the game(s) that happened yesterday / in the past 
