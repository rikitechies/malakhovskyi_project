import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from main import app
from core.models import db, Material, Expense
from datetime import datetime


class TestConstructionApp(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            mat1 = Material(name="Цегла", category="Стіни")
            mat2 = Material(name="Цемент", category="Фундамент")
            db.session.add_all([mat1, mat2])
            db.session.commit()

            test_date = datetime.strptime("2026-05-15", "%Y-%m-%d").date()
            exp1 = Expense(material_id=mat1.id, quantity=1000, total_cost=5000.0, date=test_date)
            db.session.add(exp1)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()


    def test_homepage_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'5000.0', response.data)
        self.assertIn('Цегла'.encode('utf-8'), response.data)

    def test_materials_page_loads(self):
        response = self.client.get('/materials')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Цемент'.encode('utf-8'), response.data)

    def test_add_material(self):
        response = self.client.post('/materials/add', data=dict(
            category="Покрівля",
            name="Черепиця"
        ), follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Черепиця'.encode('utf-8'), response.data)

        with app.app_context():
            mat = Material.query.filter_by(name="Черепиця").first()
            self.assertIsNotNone(mat)

    def test_add_expense(self):
        with app.app_context():
            mat = Material.query.filter_by(name="Цемент").first()
            mat_id = mat.id

        response = self.client.post('/expense/add', data=dict(
            material_id=mat_id,
            quantity=50.5,
            total_cost=2500.0,
            date="2026-06-01"
        ), follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        with app.app_context():
            expenses = Expense.query.all()
            self.assertEqual(len(expenses), 2)
            self.assertEqual(expenses[1].total_cost, 2500.0)

    def test_edit_expense(self):
        with app.app_context():
            exp = Expense.query.first()
            exp_id = exp.id

        response = self.client.post(f'/expense/edit/{exp_id}', data=dict(
            quantity=2000,
            total_cost=10000.0,
            date="2026-05-20"
        ), follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        with app.app_context():
            updated_exp = Expense.query.get(exp_id)
            self.assertEqual(updated_exp.quantity, 2000)
            self.assertEqual(updated_exp.total_cost, 10000.0)

    def test_date_filter(self):
        response_found = self.client.get('/?date_from=2026-05-10&date_to=2026-05-20')
        self.assertIn('5000.0'.encode('utf-8'), response_found.data)

        response_not_found = self.client.get('/?date_from=2026-04-01&date_to=2026-04-30')
        self.assertNotIn('5000.0'.encode('utf-8'), response_not_found.data)
        self.assertIn('Записів не знайдено'.encode('utf-8'), response_not_found.data)

    def test_search_functionality(self):
        response = self.client.get('/?search=Стіни')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Цегла'.encode('utf-8'), response.data)

    def test_excel_export(self):
        response = self.client.get('/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    unittest.main()