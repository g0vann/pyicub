import argparse
from pyicub.rest import iCubRESTApp, iCubFSM
import logging

# Configura il logger per vedere i messaggi del server
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class DynamicFSMServer(iCubRESTApp):
    """
    Un server REST per iCub che può caricare dinamicamente una FSM
    tramite una chiamata HTTP POST, senza necessità di riavvio.
    """
    def __init__(self, robot_name="icub", **kargs):
        """
        Costruttore: inizializza il server e registra l'endpoint custom.
        """
        super().__init__(robot_name=robot_name, **kargs)
        
        # Registra il nostro metodo custom 'load_fsm' come un endpoint REST.

        # Sarà accessibile via POST all'URL stampato all'avvio.

        self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.load_fsm, target_name='load_fsm')

        # Registra il nuovo metodo per ottenere la FSM completa, incluse le azioni.
        self.__register_method__(robot_name=self.robot_name, app_name=self.name, method=self.get_full_fsm, target_name='get_full_fsm')

        # Carica una FSM iniziale vuota per evitare errori al primo avvio
        self.setFSM(iCubFSM(JSON_dict={"name": "EmptyFSM"}))
        self.logger.info(f"Server '{self.name}' avviato con una FSM vuota. In attesa di caricamento via HTTP.")
        
        
        
    def get_full_fsm(self, **kwargs):

        """
        Restituisce la definizione JSON completa della FSM correntemente caricata,
        includendo la sezione 'actions' che manca nel toJSON() di base.
        """

        import json
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

    print("--- Avvio del Server FSM Dinamico ---")

    # Crea un'istanza della nostra applicazione server
    app = DynamicFSMServer(robot_name=args.robot)
    
    # Recupera le informazioni del server da mostrare all'utente
    app_name = app.name
    host = app.rest_manager._host_
    port = app.rest_manager._port_
    robot_name = app.robot_name

    print(f"\nServer in ascolto su http://{host}:{port}")
    print(f"Nome Robot: {robot_name}")
    print(f"Nome App:   {app_name}\n")
    print("Endpoint principali:")
    print(f"  - Per caricare/cambiare FSM: POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/load_fsm")
    print(f"  - Per esportare la FSM completa: POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/get_full_fsm")
    print(f"  - Per eseguire uno step:       POST http://{host}:{port}/pyicub/{robot_name}/{app_name}/fsm.runStep")
    print("\nPronto per ricevere richieste. Premi Ctrl+C per uscire.")

    # Avvia il server e lo lascia in esecuzione
    app.rest_manager.run_forever()

        			
