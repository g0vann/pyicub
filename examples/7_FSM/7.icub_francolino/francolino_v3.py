from pyicub.rest import iCubRESTApp, iCubFSM
from pyicub.actions import iCubFullbodyAction
from pyicub.fsm import FSM
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')


logger = FSM.getLogger()

app = iCubRESTApp()

app.setFSM(iCubFSM(JSON_dict={"name": "InitialEmptyFSM", "states": [], "transitions": []}))

app.rest_manager.run_forever()