from flask_testing import TestCase
import tempfile

# TODO
# make temp db
# apply schema
# add fake article data
# add users with rest
# add feed back with rest
class TestFeedbackRoutes(TestCase):
    def create_app(self):
        app = Flask(__name__)
        # add the routes to the app here
        return app

    def test_bad_inlining_route(self):
        response = self.client.get('/feedback/bad_inlining?user_id=123&article_id=456')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), 'Success')
        # check that the feedback was correctly saved in the database
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT format_quality FROM feedback WHERE user_id=123 AND article_id=456')
            result = cur.fetchone()
            self.assertEqual(result, -1)
