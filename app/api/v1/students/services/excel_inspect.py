import pandas as pd
import io
import string

def get_column_letter(col_idx):
    """Convierte índice de columna (0=A, 1=B, 2=C, ...) en formato de Excel"""
    result = ""
    while col_idx >= 0:
        result = string.ascii_uppercase[col_idx % 26] + result
        col_idx = col_idx // 26 - 1
    return result

def inspect_excel(file: bytes):
    excel_data = pd.ExcelFile(io.BytesIO(file))
    structure = {}

    for sheet_name in excel_data.sheet_names:
        df = excel_data.parse(sheet_name, header=None)
        df.fillna(value="No Definido", inplace=True)

        formatted_data = []
        for row_idx, row in df.iterrows():
            formatted_row = {}
            for col_idx, value in enumerate(row):
                cell_ref = f"{get_column_letter(col_idx)}{row_idx + 1}"
                formatted_row[cell_ref] = value
            formatted_data.append(formatted_row)

        structure[sheet_name] = {
            "sample_data": formatted_data
        }

    return {"structure": structure}
