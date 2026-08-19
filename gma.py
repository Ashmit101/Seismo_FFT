from ground_motion_analyzer.app import Application
from loguru import logger

logger.info("Starting application")
app = Application()
app.mainloop()
