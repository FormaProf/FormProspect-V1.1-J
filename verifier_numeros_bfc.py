import sqlite3
import re

db_path = r"C:\Users\Nacim\Desktop\projet\PROJET 1 - BFC\project.db"

conn = sqlite3.connect(db_path)

try:
    rows = conn.execute(
        """
        SELECT telephone
        FROM prospects
        WHERE telephone IS NOT NULL
          AND TRIM(telephone) != ''
        """
    ).fetchall()

    multi = []

    for (value,) in rows:
        text = str(value or "")
        numbers = re.findall(r"\+?\d[\d .()/-]{5,}\d", text)

        if len(numbers) >= 2:
            multi.append(text)

    print("Prospects avec téléphone :", len(rows))
    print("Prospects contenant plusieurs numéros :", len(multi))
    print("Exemples :")
    for value in multi[:10]:
        print(" -", value)

finally:
    conn.close()
