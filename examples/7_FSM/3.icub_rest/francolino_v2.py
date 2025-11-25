import argparse
from pyicub.rest import iCubRESTApp, iCubFSM
import logging
import os
import json

# Configura il logger per vedere i messaggi del server
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class DynamicFSMServer(iCubRESTApp):
    """
    Un server REST per iCub che può caricare dinamicamente una FSM
    e gestire le definizioni delle azioni.
    """
    def __init__(self, robot_name="icub", **kargs):
        """
        Costruttore: inizializza il server, carica le azioni e registra gli endpoint.
        """
        super().__init__(robot_name=robot_name, **kargs)
        
        # --- Gestione Azioni ---
        self.actions_dir = os.path.join(os.path.dirname(__file__), 'francolino-actions')
        self.available_actions = {}
        self._load_actions_from_disk()
        
        # Endpoint per ottenere le azioni disponibili per la palette del frontend
        self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.get_available_actions, target_name='get_available_actions', verb='GET')
        
        # --- Gestione FSM ---
        self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.load_fsm, target_name='load_fsm')
        self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.get_full_fsm, target_name='get_full_fsm', verb='GET')

        self.setFSM(iCubFSM(JSON_dict={"name": "EmptyFSM"}))
        self.logger.info(f"Server '{self.name}' avviato con una FSM vuota. In attesa di caricamento via HTTP.")
        
    def _load_actions_from_disk(self):
        """
        Scansiona la directory 'actions', carica i file JSON e li memorizza.
        """
        self.logger.info(f"Caricamento delle definizioni delle azioni da '{self.actions_dir}'...")
        if not os.path.exists(self.actions_dir):
            self.logger.warning(f"La directory delle azioni '{self.actions_dir}' non esiste. Creazione in corso...")
            os.makedirs(self.actions_dir)
        
        self.available_actions = {}
        try:
            for filename in os.listdir(self.actions_dir):
                if filename.endswith('.json'):
                    action_name = os.path.splitext(filename)[0]
                    filepath = os.path.join(self.actions_dir, filename)
                    with open(filepath, 'r') as f:
                        action_data = json.load(f)
                        self.available_actions[action_name] = action_data
                        self.logger.info(f"  - Caricata azione: '{action_name}'")
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento delle azioni: {e}")
            
    def get_available_actions(self, **kwargs):
        """
        Endpoint REST per il frontend.
        Restituisce una lista di oggetti 'palette' per popolare l'interfaccia.
        """
        self.logger.info("Richiesta per le azioni disponibili ricevuta.")
        palette_actions = []
        for action_name, action_data in self.available_actions.items():
            if '_palette' in action_data:
                palette_info = action_data['_palette'].copy()
                # Assicuriamoci che il nome sia consistente con il nome del file
                palette_info['name'] = action_name
                palette_actions.append(palette_info)
            else:
                self.logger.warning(f"L'azione '{action_name}' non contiene la chiave '_palette' per la UI.")
        
        return palette_actions

    def get_full_fsm(self, **kwargs):
        """
        Restituisce la definizione JSON completa della FSM correntemente caricata,
        includendo la sezione 'actions' che manca nel toJSON() di base.
        """
        self.logger.info(f"Esportazione definizione completa per FSM '{self.fsm.name}'...")
        try:
            if not isinstance(self.fsm, iCubFSM):
                return self.fsm.toJSON()

            # Converte gli oggetti 'action' in dizionari usando il loro metodo toJSON()
            actions_as_dict = {name: json.loads(action.toJSON()) for name, action in self.fsm.actions.items()}

            # Assembla manualmente il dizionario completo
            full_fsm_data = {
                "name": self.fsm.name,
                "states": self.fsm.getStates(),
                "transitions": self.fsm.getTransitions(),
                "initial_state": self.fsm._machine_.initial,
                "actions": actions_as_dict
            }

            return full_fsm_data

        except Exception as e:
            self.logger.error(f"Errore durante l'esportazione completa della FSM: {e}")
            return {"status": "error", "message": str(e)}, 500

    def load_fsm(self, **fsm_definition):
        """
        Questo metodo viene eseguito quando si chiama l'endpoint /load_fsm.
        Il corpo della richiesta JSON viene passato qui come un dizionario.
        """
        try:
            self.logger.info("Ricevuta richiesta di caricamento nuova FSM...")
           
            if not fsm_definition:
                self.logger.warning("Tentativo di caricare una FSM da un JSON vuoto.")
                return {"status": "error", "message": "Il corpo della richiesta non può essere vuoto."}, 400

            # Crea una nuova istanza di iCubFSM usando il JSON ricevuto
            new_fsm = iCubFSM(JSON_dict=fsm_definition)
        
            # Questo metodo scarta la vecchia FSM e registra la nuova
            self.setFSM(new_fsm)
           
            fsm_name = new_fsm.name or "UnnamedFSM"
            self.logger.info(f"Nuova FSM '{fsm_name}' caricata con successo.")
            
            # Ritorna un messaggio di successo con i trigger disponibili
            return {
                "status": "success",
                "message": f"FSM '{fsm_name}' caricata.",
                "initial_triggers": self.fsm.getCurrentTriggers()
            }
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento della FSM: {e}")
            return {"status": "error", "message": str(e)}, 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyiCub Dynamic FSM Server.")
    parser.add_argument("--robot", type=str, default="icub", help="Nome del robot (es. icub, icubSim).")
    args = parser.parse_args()

    print("--- Avvio del Server FSM Dinamico (v2) ---")
    app = DynamicFSMServer(robot_name=args.robot)
    
    app_name = app.name
    host = app.rest_manager._host_
    port = app.rest_manager._port_
    robot_name = app.robot_name

    print(f"\nServer in ascolto su http://{host}:{port}")
    print(f"Nome Robot: {robot_name}")
    print(f"Nome App:   {app_name}\n")
    print("Endpoint principali:")
    print(f"  - Per ottenere le azioni:         GET http://{host}:{port}/pyicub/{robot_name}/{app_name}/get_available_actions")
    print(f"  - Per caricare/cambiare FSM:      POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/load_fsm")
    print(f"  - Per esportare la FSM completa:  GET http://{host}:{port}/pyicub/{robot_name}/{app_name}/get_full_fsm")
    print(f"  - Per eseguire uno step:          POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/fsm.runStep")
    print("\nPronto per ricevere richieste. Premi Ctrl+C per uscire.")

    app.rest_manager.run_forever()
