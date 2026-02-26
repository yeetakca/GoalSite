from pathlib import Path
import json
import sys

from goalsite2.game import Game


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def main() -> None:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config/game_config.json")
    config = load_config(config_path)
    game = Game(config)
    game.run()


if __name__ == "__main__":
    main()
