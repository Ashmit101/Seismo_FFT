from loguru import logger

from ground_motion_analyzer.app import Application


def main():
    logger.info("Starting application")
    app = Application()
    app.mainloop()


if __name__ == "__main__":
    main()
