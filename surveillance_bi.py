
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil
import time
import logging

PAIRS = [
    (Path(r"L:\Chris\2026\BI\Entrée"), Path(r"D:\SBM\BI\Entrée")),
    (Path(r"L:\Chris\2026\BI\Sortie"), Path(r"D:\SBM\BI\Sortie")),
]

logging.basicConfig(
    filename="copy.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)

def copier(fichier, destination):
    if not fichier.is_file() or fichier.name.startswith("~$"):
        return

    # Attendre la fin d'une éventuelle écriture Excel.
    taille_precedente = -1
    for _ in range(6):
        try:
            taille = fichier.stat().st_size
            if taille == taille_precedente:
                break
            taille_precedente = taille
        except OSError:
            return
        time.sleep(2)
    else:
        logging.warning("Fichier encore en cours de modification : %s", fichier)
        return

    cible = destination / fichier.name
    temporaire = destination / (fichier.name + ".tmp_copie")

    try:
        destination.mkdir(parents=True, exist_ok=True)

        # Évite la copie si taille et date sont identiques.
        if cible.exists():
            src, dst = fichier.stat(), cible.stat()
            if (src.st_size == dst.st_size
                    and src.st_mtime_ns == dst.st_mtime_ns):
                return

        shutil.copy2(fichier, temporaire)

        # Vérifier que la source n'a pas changé pendant la copie.
        if fichier.stat().st_size != temporaire.stat().st_size:
            temporaire.unlink(missing_ok=True)
            logging.warning("Copie incomplète : %s", fichier)
            return

        temporaire.replace(cible)
        logging.info("Copié : %s -> %s", fichier, cible)
        print(f"[COPIÉ] {fichier.name}")

    except OSError as erreur:
        logging.error("Erreur pour %s : %s", fichier, erreur)
        print(f"[ERREUR] {fichier.name} : {erreur}")
        temporaire.unlink(missing_ok=True)

class GestionnaireFichiers(FileSystemEventHandler):
    def __init__(self, destination):
        self.destination = destination

    def traiter(self, chemin):
        copier(Path(chemin), self.destination)

    def on_created(self, event):
        if not event.is_directory:
            self.traiter(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.traiter(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.traiter(event.dest_path)

def main():
    observateurs = []

    for source, destination in PAIRS:
        if not source.is_dir():
            print(f"[ERREUR] Source inaccessible : {source}")
            continue

        destination.mkdir(parents=True, exist_ok=True)
        gestionnaire = GestionnaireFichiers(destination)
        observateur = Observer()
        observateur.schedule(gestionnaire, str(source), recursive=False)
        observateur.start()
        observateurs.append(observateur)

        print(f"[SURVEILLANCE] {source} -> {destination}")

        # Synchroniser les fichiers déjà présents au démarrage.
        for fichier in source.iterdir():
            copier(fichier, destination)

    if not observateurs:
        print("Aucun dossier accessible. Vérifie le lecteur réseau L:.")
        return

    print("Surveillance active. Arrêt avec Ctrl+C.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArrêt de la surveillance...")
    finally:
        for observateur in observateurs:
            observateur.stop()
        for observateur in observateurs:
            observateur.join()

if __name__ == "__main__":
    main()
