## Stato del progetto e limiti noti

Questo progetto è un bridge per Linux che invia la telemetria dei simulatori
di guida ai display UDP dei volanti e alla webdash integrata. È stato scritto
da un appassionato, con l'aiuto di un'AI, quindi il codice potrebbe non essere
elegante, ma funziona.

### Cosa funziona oggi
- Velocità, marcia, giri motore e LED del cambio
- Livello di carburante
- Usura delle gomme
- Tempo sul giro corrente
- Gioco testato: Le Mans Ultimate (LMU) [aggiungi gli altri giochi provati]
- Hardware testato: Thrustmaster T-GT II, SF1000 (firmware v9.15), T-LCM
- Sistema operativo: CachyOS Linux

### Cosa manca
- **Delta del giro**: non ancora implementato.
- **Batteria / ERS / KERS sul display dell'SF1000**: i valori sono presenti
  nei dati di telemetria e l'ho verificato, ma non sono riuscito a farli
  comparire sul display del volante. La causa potrebbe essere un limite del
  firmware del volante e non del bridge, ma non sono riuscito a confermarlo.
- ERS / batteria sulla webdash: [non ancora fatto / da aggiungere].

### Cerco aiuto
Non sono un programmatore professionista e non penso di sviluppare molto
oltre questo progetto. Se hai le competenze e la voglia, i contributi sono
molto benvenuti, in particolare per:
- implementare il delta del giro;
- capire se l'SF1000 può mostrare la barra ERS;
- aggiungere ERS / batteria alla webdash;
- supportare altri volanti e display.

Puoi aprire una issue o una pull request, oppure fare un fork del progetto.
