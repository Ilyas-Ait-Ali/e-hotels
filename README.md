# eHotel Website

A web-based hotel booking platform developed using Flask and PostgreSQL. This project allows users to view, search, and book hotels, with additional admin functionalities for managing bookings, hotels, and rooms.

---

## 🛠 Technologies Used

- **Frontend**: HTML5, Bootstrap 5
- **Backend**: Python 3.9+, Flask, Jinja2
- **Database**: PostgreSQL 17
- **ORM**: SQLAlchemy (basic setup)
- **Database Scripts**: Raw SQL (DDL, triggers, views, population)

---

## 🚀 Getting Started

### ✅ Prerequisites

- Python 3.9+
- PostgreSQL 17+
- pgAdmin 4
- `pip` package manager

---

### 🧪 Installation Steps

1. **Clone the Repository**
```bash
git clone https://github.com/Ilyas-Ait-Ali/e-hotel.git
cd e-hotel/backend
```
2. **Create a Virtual Environment**
```bash
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux
```
3. **Install Dependencies**
```bash
pip install -r requirements.txt
```
4. **Create the PostgreSQL Database**
- Open pgAdmin 4.
- Create a new database called ehotels.
- Open the query editor and paste the contents of: schema.sql, constraints.sql, populate.sql, queries.sql, triggers.sql, indexes.sql, views.sql in that exact order, then execute the script.
5. **Update Database Credentials**
Open config.py and replace:
```python
DB_PASSWORD = 'your_own_password'
```
6. **Run the Flask App**
```bash
flask run
```
7. **View in Browser**
http://127.0.0.1:5000

---

## 🙌 Authors

- Ilyas Ait Ali
- Yasmina Baba

---

## 🧾 License
This project is for educational purposes.
