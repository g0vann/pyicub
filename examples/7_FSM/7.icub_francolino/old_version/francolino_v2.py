import argparse
from pyicub.rest import iCubRESTApp, iCubFSM
import logging
import os
import json
import re

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
        
        # --- Registrazione Endpoint ---
        self._register_action_endpoints()
        self._register_fsm_endpoints()

        # Carica una FSM iniziale vuota
        self.setFSM(iCubFSM(JSON_dict={"name": "EmptyFSM"}))
        self.logger.info(f"Server '{self.name}' avviato con una FSM vuota. In attesa di caricamento via HTTP.")

    def _register_action_endpoints(self):
        """Registra gli endpoint relativi alla gestione delle azioni."""
        self.logger.info("Registrazione degli endpoint per le azioni...")
        try:
            prefix = f"/{self.rest_manager._rule_prefix_}/{self.robot_name}/{self.name}"

            # GET /actions -> Lista di tutte le azioni per la palette
            self.rest_manager._flaskapp_.add_url_rule(
                f"{prefix}/actions", 
                'get_available_actions_route',
                lambda: self.get_available_actions(),
                methods=['GET']
            )
            self.logger.info(f"  - Registrato endpoint: GET {prefix}/actions")

            # GET /actions/<action_name> -> Dettaglio di una singola azione
            self.rest_manager._flaskapp_.add_url_rule(
                f"{prefix}/actions/<action_name>",
                'get_action_details_route',
                lambda action_name: self.get_action_details(action_name=action_name),
                methods=['GET']
            )
            self.logger.info(f"  - Registrato endpoint: GET {prefix}/actions/<action_name>")

            # POST /actions -> Crea una nuova azione
            self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.create_action, target_name='actions')

        except Exception as e:
            self.logger.error(f"Impossibile registrare gli endpoint delle azioni: {e}")
    
    def _register_fsm_endpoints(self):
        """Registra gli endpoint relativi alla gestione della FSM."""
        self.logger.info("Registrazione degli endpoint per la FSM...")
        self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.load_fsm, target_name='load_fsm')
        self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.get_full_fsm, target_name='get_full_fsm')

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
        Handler per l'endpoint GET /actions.
        Restituisce una lista di oggetti 'palette' per popolare l'interfaccia.
        """
        self.logger.info("Richiesta GET per la lista delle azioni disponibili ricevuta.")
        palette_actions = []
        for action_name, action_data in self.available_actions.items():
            if '_palette' in action_data:
                palette_info = action_data['_palette'].copy()
                palette_info['name'] = action_name
                palette_actions.append(palette_info)
            else:
                self.logger.warning(f"L'azione '{action_name}' non contiene la chiave '_palette' per la UI.")
        
        return palette_actions

    def get_action_details(self, action_name, **kwargs):
        """
        Handler per l'endpoint GET /actions/{action_name}.
        Restituisce i dettagli completi di una singola azione.
        """
        self.logger.info(f"Richiesta GET per il dettaglio dell'azione: '{action_name}'")
        action_data = self.available_actions.get(action_name)
        if action_data:
            return action_data
        else:
            return {"status": "error", "message": f"Azione '{action_name}' non trovata."}, 404

    def create_action(self, **action_data):
        """
        Handler per l'endpoint POST /actions.
        Crea una nuova azione, la salva su disco e la carica in memoria.
        """
        self.logger.info(f"Richiesta POST per creare una nuova azione...")
        
        # Validazione base del corpo della richiesta
        if not action_data:
            return {"status": "error", "message": "Corpo della richiesta JSON non valido o mancante."}, 400
        
        try:
            action_name = action_data.get('_palette', {}).get('name')
            if not action_name:
                return {"status": "error", "message": "La chiave '_palette.name' è obbligatoria nel JSON dell'azione."}, 400

            # Controlla se il nome è valido per un nome file
            if not re.match(r'^[a-zA-Z0-9_-]+$', action_name):
                 return {"status": "error", "message": f"Il nome dell'azione '{action_name}' non è valido. Usare solo lettere, numeri, _ e -."}, 400

            # Controlla se esiste già
            if action_name in self.available_actions:
                return {"status": "error", "message": f"Un'azione con nome '{action_name}' esiste già."}, 409
            
            # Salva il file JSON
            file_path = os.path.join(self.actions_dir, f"{action_name}.json")
            with open(file_path, 'w') as f:
                json.dump(action_data, f, indent=4)
            
            # Aggiunge l'azione alla lista in memoria
            self.available_actions[action_name] = action_data
            
            self.logger.info(f"Azione '{action_name}' creata e salvata con successo in '{file_path}'.")
            return {"status": "success", "message": f"Azione '{action_name}' creata con successo."}

        except Exception as e:
            self.logger.error(f"Errore durante la creazione dell'azione: {e}")
            return {"status": "error", "message": str(e)}, 500

    def get_full_fsm(self, **kwargs):
        """
        Restituisce la definizione JSON completa della FSM correntemente caricata.
        """
        self.logger.info(f"Esportazione definizione completa per FSM '{self.fsm.name}'...")
        try:
            if not isinstance(self.fsm, iCubFSM):
                return self.fsm.toJSON()

            actions_as_dict = {name: json.loads(action.toJSON()) for name, action in self.fsm.actions.items()}
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
        Carica una nuova FSM dal JSON ricevuto via POST.
        """
        try:
            self.logger.info("Ricevuta richiesta di caricamento nuova FSM...")
            if not fsm_definition:
                self.logger.warning("Tentativo di caricare una FSM da un JSON vuoto.")
                return {"status": "error", "message": "Il corpo della richiesta non può essere vuoto."}, 400

            new_fsm = iCubFSM(JSON_dict=fsm_definition)
            self.setFSM(new_fsm)

            # Svuota azioni precedenti di questa app/FSM
            self.flushActions(name_prefix=self.name + '.FSM')
            self.flushActions(name_prefix=self.name + '.iCubFSM')

            # Importa le nuove azioni della FSM caricata
            for action in self.fsm.actions.values():
                self.importAction(action, name_prefix=self.name + '.' + self.fsm.name)

            fsm_name = new_fsm.name or "UnnamedFSM"
            self.logger.info(f"Nuova FSM '{fsm_name}' caricata con successo.")
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
    print(f"  - Lista azioni (palette):     GET http://{host}:{port}/pyicub/{robot_name}/{app_name}/actions")
    print(f"  - Dettaglio singola azione:   GET http://{host}:{port}/pyicub/{robot_name}/{app_name}/actions/<nome_azione>")
    print(f"  - Crea nuova azione:          POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/actions")
    print(f"  - Carica FSM:                 POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/load_fsm")
    print(f"  - Esporta FSM completa:       POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/get_full_fsm")
    print(f"  - Esegui step FSM:            POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/fsm.runStep")
    print("\nPronto per ricevere richieste. Premi Ctrl+C per uscire.")

    app.rest_manager.run_forever()
