import logging

GRAY1  = 0xff #white
GRAY2  = 0xC0
GRAY3  = 0x80 #gray
GRAY4  = 0x00 #Blackest

logger = logging.getLogger(__name__)

class EPD:
    def __init__(self):
        self.GRAY1  = GRAY1 #white
        self.GRAY2  = GRAY2
        self.GRAY3  = GRAY3 #gray
        self.GRAY4  = GRAY4 #Blackest

    def reset(self):
        logger.debug("(EMULATED) Reseting Screen")

    def send_command(self, command):
        logger.debug("(EMULATED) Sending command: %s", hex(command))

    def send_data(self, data):
        logger.debug("(EMULATED) Sending data: %s", hex(data))

    def send_data2(self, data):
        logger.debug("(EMULATED) Sending data2: %s", hex(data))

    def ReadBusy(self):
        logger.debug("(EMULATED) Reading busy status")

    def init(self):
        logger.info("(EMULATED) Initializing display")

    def init_fast(self):
        logger.info("(EMULATED) Initializing display in fast mode")

    def init_part(self):
        logger.info("(EMULATED) Initializing display in partial mode")

    def init_4Gray(self):
        logger.info("(EMULATED) Initializing display in 4Gray mode")

    def getBuffer(self, image):
        logger.debug("(EMULATED) Getting buffer from image")
        return bytearray()
    
    def getBuffer_4Gray(self, image):
        logger.debug("(EMULATED) Getting 4Gray buffer from image")
        return bytearray()
    
    def display(self, image):
        logger.info("(EMULATED) Displaying image")

    def display_Partial(self, image):
        logger.info("(EMULATED) Displaying partial image")

    def display_4Gray(self, image):
        logger.info("(EMULATED) Displaying 4Gray image")

    def Clear(self):
        logger.info("(EMULATED) Clearing display")

    def sleep(self):
        logger.info("(EMULATED) Putting display to sleep")

    
