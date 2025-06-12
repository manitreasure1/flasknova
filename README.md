[project]
name = "flasknova"
version = "0.1.0"
description = "Extra check using pydandic in flask application"
authors = [
    {name = "manitreasure1",email = "manitreasure1@gmail.com"}
]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "Flask==3.1.1",
    "pydantic==2.11.5",
    "uvicorn==0.34.3"
]


[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
