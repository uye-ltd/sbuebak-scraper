from src.cli.cli import build_parser
from src.logger import configure_logging


def main() -> None:
    configure_logging()
    build_parser().parse_args()


if __name__ == "__main__":
    main()
