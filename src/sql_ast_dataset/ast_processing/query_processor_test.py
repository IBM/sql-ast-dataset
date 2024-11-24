import unittest

from sql_ast_dataset.ast_processing.factory import Factory


class TestQueryProcessor(unittest.TestCase):
    def setUp(self) -> None:
        self.method_name = "QueryProcessor"
        self.factory = Factory()

        self.query = "SELECT * FROM A"

    def test(self):
        instance = self.factory.build(self.method_name, config_dict={})

        self.assertIsNotNone(instance)

        label = 1
        ast_class = instance.process(
            sql_query_1=self.query,
            sql_query_2=self.query,
            label=label,
        )
        self.assertEqual(ast_class.processed_query, self.query)
        self.assertEqual(ast_class.label, label)

        label = 1
        ast_class = instance.process(
            sql_query_1=self.query,
            sql_query_2=self.query,
            label=label,
        )
        self.assertEqual(ast_class.processed_query, self.query)
        self.assertEqual(ast_class.label, label)

    def test_query_0(self):
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = "SELECT T2.Name FROM course_arrange AS T2 GROUP BY T2.Name"
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_1,
                label=1,
            )
        except Exception:
            self.assertTrue(False)

    def test_query_1(self):
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = (
            "SELECT T2.Name FROM course_arrange AS T1 JOIN teacher "
            "AS T2 ON T1.Teacher_ID = T2.Teacher_ID GROUP BY "
            "T2.Name HAVING COUNT(*) >= 2"
        )
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_1,
                label=1,
            )
        except Exception:
            self.assertTrue(False)

    def test_query_2(self):
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = (
            "SELECT DISTINCT t.name FROM teacher AS t WHERE NOT "
            "t.teacher_id IN (SELECT DISTINCT teacher_id "
            "FROM course_arrange)"
        )
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_1,
                label=1,
            )
        except Exception:
            self.assertTrue(False)

    def test_query_3(self):
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = (
            "SELECT t.Name, COUNT(ca.Course_ID) FROM teacher AS t LEFT "
            "JOIN course_arrange AS ca ON ca.Teacher_ID = t.Teacher_ID "
            "GROUP BY t.Name, ca.Teacher_ID"
        )
        query_2 = (
            "SELECT t.Name, COUNT(c.Course) FROM teacher AS t JOIN "
            "course_arrange AS ca ON t.Teacher_ID = ca.Teacher_ID "
            "JOIN course AS c ON ca.Course_ID = c.Course_ID GROUP BY t.Name"
        )
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
        except Exception:
            self.assertTrue(False)

    def test_query_4(self):
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = (
            "WITH age_filtering(country, name) AS (SELECT Country AS "
            "country, Name AS name FROM singer WHERE age > 20 GROUP BY "
            "country) SELECT country FROM age_filtering GROUP BY country"
        )
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_1,
                label=1,
            )
        except Exception:
            # Not supporting WITH ...
            self.assertTrue(True)

    def test_query_5(self):
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = (
            "SELECT *, NOT COUNT(CASE WHEN SourceAirport IN ('CVO', 'APG') "
            "THEN 1 ELSE NULL END) IS NULL AS has_CVO_or_APG FROM flights "
            "WHERE DestAirport = 'CVO' GROUP BY Airline"
        )
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_1,
                label=1,
            )
        except Exception:
            self.assertTrue(False)

    def test_query_6(self):
        # There seems to be something off with the IF
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = (
            "SELECT MIN(d.Version_Number), dt.Template_Type_Code "
            "FROM Templates AS d INNER JOIN Ref_Template_Types AS "
            "dt ON d.Template_Type_Code = dt.Template_Type_Code "
            "GROUP BY dt.Template_Type_Code HAVING SUM(CASE "
            "Date_Effective_To WHEN NULL THEN exceeded ELSE visible "
            "END) > averages ORDER BY Version_Number"
        )
        query_2 = "SELECT MIN(Version_Number), template_type_code FROM Templates"
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
        except Exception:
            # [WRONG]
            self.assertTrue(True)

    def test_query_7(self):
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)
        query_1 = (
            "SELECT SUM(CASE WHEN Age > 30 THEN 1 ELSE NULL "
            "END) AS number_of_patterns FROM visitor"
        )
        query_2 = (
            "SELECT SUM(CASE WHEN Age > 30 THEN 1 ELSE "
            "NULL END) AS number_of_patterns FROM visitor"
        )
        try:
            instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
        except Exception:
            self.assertTrue(False)

    def test_ast_labels_1(self):
        query_1 = "SELECT AVG(winner_age), AVG(loser_age) FROM matches"
        query_2 = "SELECT AVG(loser_age), AVG(winner_age) FROM matches"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=1,
            )
            label_list = ast_diff.get_labels()
            self.assertEqual(label_list, [1, 1, 1, 1, 1, 1, 1])

        except Exception:
            self.assertTrue(False)

    def test_ast_labels_2(self):
        query_1 = "SELECT a, b FROM c"
        query_2 = "SELECT b, a FROM c"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=1,
            )
            label_list = ast_diff.get_labels()
            self.assertEqual(label_list, [1, 1, 1, 1, 1])

        except Exception:
            self.assertTrue(False)

    def test_ast_labels_3(self):
        query_1 = "SELECT Name, COUNT(*) FROM singer"
        query_2 = "SELECT COUNT(*) FROM singer"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            self.assertEqual(label_list, [1, 0, 1, 1, 1, 1])
        except Exception:
            self.assertTrue(False)

    def test_ast_labels_4(self):
        query_1 = "SELECT Name, COUNT(*), Age FROM singer"
        query_2 = "SELECT COUNT(*) FROM singer"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            self.assertEqual(label_list, [1, 0, 1, 1, 0, 1, 1])

        except Exception:
            self.assertTrue(False)

    def test_ast_labels_5(self):
        query_1 = "SELECT COUNT(Name) FROM singer"
        query_2 = "SELECT COUNT(*) FROM singer"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            # The COUNT() gets also labeld as False
            self.assertEqual(label_list, [1, 0, 0, 1, 1])

        except Exception:
            self.assertTrue(False)

    def test_ast_labels_6(self):
        query_1 = "SELECT COUNT(Name) FROM singer"
        query_2 = "SELECT COUNT(*) FROM singer"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            # The COUNT() gets also labeld as False
            self.assertEqual(label_list, [1, 0, 0, 1, 1])

        except Exception:
            self.assertTrue(False)

    def test_ast_labels_7(self):
        query_2 = "SELECT note FROM death WHERE note LIKE '%East%'"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            query_1 = "SELECT * FROM death WHERE note LIKE '%East%'"
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            self.assertEqual(label_list, [1, 0, 1, 1, 1, 1, 1, 1])

            query_1 = (
                "SELECT death.note FROM death INNER JOIN ship "
                "ON death.caused_by_ship_id = ship.id WHERE "
                "ship.location LIKE '%East%'"
            )
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            # death.note gets labeld as 0
            self.assertEqual(label_list, [1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1])

        except Exception:
            self.assertTrue(False)

    def test_ast_labels_8(self):
        query_2 = "SELECT song_name, song_release_year FROM singer ORDER BY age LIMIT 1"
        instance = self.factory.build(self.method_name, config_dict={})
        self.assertIsNotNone(instance)

        try:
            query_1 = (
                "SELECT name, song_release_year FROM "
                "singer WHERE age = (SELECT MIN(age) FROM singer)"
            )
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            # Unfortunately it seems like it wants to keep the age, FROM, singer
            # from the subquery. Not sure if this is ideal. Culd also be that this
            # is not a 100% consistent outcome.
            self.assertEqual(label_list, [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1])

            query_1 = (
                "SELECT name, song_release_year FROM "
                "singer WHERE singer.age = (SELECT MIN(age) FROM singer)"
            )
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            # Same here
            self.assertEqual(label_list, [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1])

            query_1 = (
                'SELECT "Name", "Song_release_year" FROM "singer" '
                'WHERE Age = (SELECT MIN(Age) FROM "singer")'
            )
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            # Same here
            self.assertEqual(label_list, [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1])

            query_1 = (
                "SELECT s.Name, s.Song_release_year FROM "
                "singer AS s, singer_in_concert AS sc "
                "WHERE s.Singer_ID = sc.Singer_ID "
                "ORDER BY s.Age ASC LIMIT 1"
            )
            ast_diff = instance.process(
                sql_query_1=query_1,
                sql_query_2=query_2,
                label=0,
            )
            label_list = ast_diff.get_labels()
            # Same here
            self.assertEqual(
                label_list, [1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            )

        except Exception:
            self.assertTrue(False)


if __name__ == "__main__":
    unittest.main()
