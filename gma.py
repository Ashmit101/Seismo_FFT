from loguru import logger

from ground_motion_analyzer.app import Application

logger.info("Starting application")
app = Application()
app.mainloop()
