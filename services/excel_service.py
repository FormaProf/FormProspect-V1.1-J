from pathlib import Path

import pandas as pd


class ExcelService:

    def __init__(self):
        self.dataframe = None
        self.file_path = None

    def load_excel(self, file_path):

        self.file_path = Path(file_path)

        self.dataframe = pd.read_excel(self.file_path)

        return self.dataframe

    @property
    def row_count(self):

        if self.dataframe is None:
            return 0

        return len(self.dataframe)

    @property
    def columns(self):

        if self.dataframe is None:
            return []

        return list(self.dataframe.columns)