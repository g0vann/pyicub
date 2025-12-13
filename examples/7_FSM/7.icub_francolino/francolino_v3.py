from pyicub.rest import iCubRESTApp, iCubFSM
from pyicub.actions import iCubFullbodyAction
from pyicub.fsm import FSM

logger = FSM.getLogger()

app = iCubRESTApp()

app.setFSM(iCubFSM(JSON_dict={"name": "InitialEmptyFSM", "states": [], "transitions": []}))

app.rest_manager.run_forever()