# IMproVision
per vedere un esempio cercare Roger Dannenberg e andare sulla sua immaginina.
il concetto è bene o male quello, ma molto più figo.

per ora è basato su [mypaint](https://github.com/mypaint/mypaint)

# Installazione locale

prima di tutto è necessario installare i [requisiti di mypaint](https://github.com/mypaint/mypaint/blob/master/BUILDING.md#install-libmypaint-and-mypaint-brushes), sono entrambi dipendenze di altri tool grafici come ad esempio gimp, quindi probabilmente saranno già disponibili a sistema, tuttavia della libmypaint è necessaria la versione 2, che non viene installata con gimp, quindi almeno quella è necessario installarla in locale e [renderla disponibile a sistema](https://github.com/mypaint/libmypaint#check-availability).

dopo di che bisogna installare le [dipendenze di mypaint](https://github.com/mypaint/mypaint/blob/master/BUILDING.md#install-third-party-dependencies) e in aggiunta anche il pacchetto pygame, necessario per l'output midi.

infine bisogna procedere ad un'installazione locale di mypaint in modo da poter estrarre la libreria dinamica compilata contro tutte le dipendenze locali:

    [me@localhost IMproVision]$ python setup.py managed_install --prefix=/tmp/improvision
    ...
    [me@localhost IMproVision]$ mv /tmp/improvision/lib/mypaint/lib/_mypaintlib.*.so lib/

a questo punto è sufficiente lanciare lo script mypaint.py nella root del progetto per avviare l'applicazione
