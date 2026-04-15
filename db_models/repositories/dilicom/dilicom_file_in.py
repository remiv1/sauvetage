"""Module de service pour les opérations de parsing des fichiers reçus de Dilicom."""

from typing import Optional, List
from os import getenv
from pathlib import Path
import pandas as pd
from db_models.repositories.dilicom.typing.distributor_data import (
    df_to_distributor_data, DistributorData, FileDistri
)

class DilicomFileIn:
    """Classe de service pour le parsing des fichiers reçus de Dilicom."""

    def __init__(self):
        self.directory: Path = Path(getenv('DILICOM_IN_DIR', './DILICOM_IN'))
        self.data: Optional[pd.DataFrame] = None
        self.file_path: Optional[Path] = None
        self.filename: str = ""
        self.distributor_data: Optional[DistributorData] = None
        if not self.directory.exists():
            self.directory.mkdir(parents=True, exist_ok=True)

    def __define_file_type(self, header: List[str]) -> str:
        """Détermine le type de fichier en fonction de son en-tête."""
        headers_and_types = {
            "Distrib_DLC": "supplier",
        }
        if len(header) != 3:
            raise ValueError(f"Taille du header inattendue: {len(header)}, attendu : 3")
        if header[0] != "L000000":
            raise ValueError(f"Unexpected header format: {header[0]}")
        match header[1]:
            case t if any(t.startswith(k) for k in headers_and_types):
                return next(v for k, v in headers_and_types.items() if t.startswith(k))
            case _:
                return 'unknown'

    def __parse_distrib(self, file_distri: FileDistri):
        """Parse les fichiers de type 'supplier' et extrait les données."""
        if self.data is not None:
            self.distributor_data = df_to_distributor_data(file_distri)
        else:
            print("No data to parse. Please parse the file first.")

    def __get_header_footer_and_data(self) -> FileDistri:
        """Lit le fichier et retourne l'en-tête et les données."""
        _file_to_read = Path(self.directory / self.filename)
        with _file_to_read.open('r', encoding='cp1252') as f:
            lines = f.readlines()
            header = lines[0].strip().split(';')
            footer = lines[-1].strip()
            data = [line.strip().split(';') for line in lines[1:-1]]
            df = pd.DataFrame(data)
        return FileDistri(header, footer, df)

    def parse_file(self, filename: str):
        """Parse le fichier en fonction de son type et extrait les données."""
        parsers = {
            'supplier': self.__parse_distrib,
        }
        self.filename = filename
        self.file_path = self.directory / filename
        distri_file = self.__get_header_footer_and_data()
        file_type = self.__define_file_type(distri_file.header)
        print(f"Determined file type: {file_type}")
        if file_type in parsers:
            self.data = distri_file.data
            parsers[file_type](distri_file)
        else:
            print(f"Unknown file type for header: {distri_file.header[1]}. No parsing performed.")
