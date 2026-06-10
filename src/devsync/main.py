import logging

from devsync.config import load_config
from devsync.infra.identity import info
from devsync.infra.log import setup_logging


def main() -> None:
    config = load_config()


if __name__ == "__main__":
    main()
