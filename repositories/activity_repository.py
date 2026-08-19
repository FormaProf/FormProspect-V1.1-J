from repositories.base_repository import BaseRepository


class ActivityRepository(BaseRepository):

    def get_activities(self, prospect_id):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, date_creation, type_action, description
            FROM activities
            WHERE prospect_id = ?
            ORDER BY id DESC
        """, (prospect_id,))

        activities = cur.fetchall()
        conn.close()

        return activities

    def add_activity(self, prospect_id, date_creation, type_action, description):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO activities (
                prospect_id,
                date_creation,
                type_action,
                description
            )
            VALUES (?, ?, ?, ?)
        """, (
            prospect_id,
            date_creation,
            type_action,
            description
        ))

        conn.commit()
        conn.close()