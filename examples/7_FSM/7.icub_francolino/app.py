# francolino_v3.py
import argparse
import logging
from pyicub.rest import iCubRESTApp, iCubFSM

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

print("--- Avvio del Server iCub con Funzionalità Native ---")

parser = argparse.ArgumentParser(description="PyiCub Native FSM Server.")
parser.add_argument("--robot", type=str, default="icubSim", help="Nome del robot (es. icub, icubSim).")
args = parser.parse_args()

app = iCubRESTApp(
    robot_name=args.robot
)

# Abilitiamo forzatamente il logger per vedere i messaggi di debug
app.logger.enable_logs()
print("!!! Logger forzatamente abilitato. In attesa di messaggi... !!!")

# Avviamo una FSM vuota di default
app.setFSM(iCubFSM(JSON_dict={"name": "InitialEmptyFSM", "states": [], "transitions": []}))

print(f"\nServer '{app.name}' in esecuzione per il robot '{app.robot_name}'.")
print(f"Le funzionalità native di gestione FSM e Azioni sono attive.")
print("Pronto per ricevere richieste. Premi Ctrl+C per uscire.")

# Essecute il server REST
app.rest_manager.run_forever()