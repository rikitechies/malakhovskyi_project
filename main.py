import os
import webbrowser
import threading
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from core.models import db, Material, Expense
import pandas as pd
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.secret_key = "super_secret_key_for_flash_messages"

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)



@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()

    query = Expense.query.join(Material)

    if search_query:
        query = query.filter(
            db.or_(
                Material.name.ilike(f'%{search_query}%'),
                Material.category.ilike(f'%{search_query}%')
            )
        )

    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= date_from)
        except ValueError:
            pass

    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= date_to)
        except ValueError:
            pass

    expenses = query.order_by(Expense.date.desc()).all()

    total_sum = sum(exp.total_cost for exp in expenses)

    materials = Material.query.all()

    return render_template('index.html',
                           expenses=expenses,
                           materials=materials,
                           total_sum=total_sum,
                           search_query=search_query,
                           date_from=date_from_str,
                           date_to=date_to_str)


@app.route('/expense/add', methods=['POST'])
def add_expense():
    material_id = request.form.get('material_id')
    quantity = float(request.form.get('quantity', 0))
    total_cost = float(request.form.get('total_cost', 0))
    date_str = request.form.get('date')

    if not material_id or quantity <= 0 or total_cost <= 0:
        flash("Помилка: Заповніть всі поля коректно.", "danger")
        return redirect(url_for('index'))

    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

    new_expense = Expense(material_id=material_id, quantity=quantity, total_cost=total_cost, date=date_obj)
    db.session.add(new_expense)
    db.session.commit()

    flash("Витрату успішно додано!", "success")
    return redirect(url_for('index'))


@app.route('/expense/edit/<int:id>', methods=['POST'])
def edit_expense(id):
    expense = Expense.query.get_or_404(id)

    quantity = float(request.form.get('quantity', 0))
    total_cost = float(request.form.get('total_cost', 0))
    date_str = request.form.get('date')

    if quantity > 0 and total_cost > 0:
        expense.quantity = quantity
        expense.total_cost = total_cost
        if date_str:
            expense.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        db.session.commit()
        flash("Запис про витрату оновлено.", "success")
    else:
        flash("Некоректні дані для оновлення.", "danger")

    return redirect(url_for('index'))


@app.route('/expense/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    flash("Запис про витрату видалено.", "info")
    return redirect(url_for('index'))


@app.route('/materials')
def materials():
    items = Material.query.order_by(Material.category, Material.name).all()
    return render_template('materials.html', materials=items)


@app.route('/materials/add', methods=['POST'])
def add_material():
    name = request.form.get('name').strip()
    category = request.form.get('category').strip()

    if Material.query.filter_by(name=name).first():
        flash(f"Матеріал '{name}' вже існує в базі!", "danger")
    elif name and category:
        new_mat = Material(name=name, category=category)
        db.session.add(new_mat)
        db.session.commit()
        flash(f"Матеріал '{name}' додано.", "success")
    else:
        flash("Назва та категорія не можуть бути порожніми.", "warning")

    return redirect(url_for('materials'))


@app.route('/materials/delete/<int:id>', methods=['POST'])
def delete_material(id):
    mat = Material.query.get_or_404(id)
    db.session.delete(mat)
    db.session.commit()
    flash("Матеріал видалено. Усі пов'язані витрати також видалено.", "info")
    return redirect(url_for('materials'))


@app.route('/export')
def export_excel():
    expenses = Expense.query.join(Material).order_by(Expense.date.desc()).all()

    data = []
    for exp in expenses:
        data.append({
            "Дата": exp.date.strftime("%Y-%m-%d"),
            "Категорія": exp.material.category,
            "Назва матеріалу": exp.material.name,
            "Кількість": exp.quantity,
            "Загальна вартість (грн)": exp.total_cost
        })

    df = pd.DataFrame(data)
    export_path = os.path.join(basedir, 'data', 'report.xlsx')
    df.to_excel(export_path, index=False, engine='openpyxl')

    return send_file(export_path, as_attachment=True,
                     download_name=f"Звіт_витрат_{datetime.now().strftime('%Y%m%d')}.xlsx")



def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")


if __name__ == '__main__':
    with app.app_context():
        os.makedirs(os.path.join(basedir, 'data'), exist_ok=True)
        db.create_all()

    threading.Timer(1.0, open_browser).start()

    app.run(debug=False)