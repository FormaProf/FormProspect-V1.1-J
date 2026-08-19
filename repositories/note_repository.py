from repositories.base_repository import BaseRepository


class NoteRepository(BaseRepository):

    def get_notes(self, prospect_id):

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""

            SELECT id,
                date_creation,
                contenu

            FROM notes

            WHERE prospect_id = ?

            ORDER BY id DESC

        """, (prospect_id,))

        notes = cur.fetchall()

        conn.close()

        return notes

    def add_note(self, prospect_id, date_creation, contenu):

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""

            INSERT INTO notes(

                prospect_id,
                date_creation,
                contenu

            )

            VALUES(?,?,?)

        """, (

            prospect_id,
            date_creation,
            contenu

        ))

        conn.commit()

        conn.close()