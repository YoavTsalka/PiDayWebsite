"""
Pi Day Website Backend App
"""
from flask import Flask, render_template, request, session, redirect, jsonify
import sqlite3
import re
import mmap
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'piday.db')
app.secret_key = 'pi_day_secret_2026'

SENDER_EMAIL = "your_dedicated_email@gmail.com"
SENDER_PASSWORD = "abcd efgh ijkl mnop"
ADMIN_EMAIL = "your_personal_email@gmail.com"

UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def init_db():
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()
    c.execute(
        'CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY, name TEXT, content TEXT, image_filename TEXT, approved INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS facts (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, title TEXT, youtube_id TEXT, description TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS recipes (id INTEGER PRIMARY KEY, title TEXT, ingredients TEXT, steps TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS songs (id INTEGER PRIMARY KEY, title TEXT, youtube_id TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS methods (id INTEGER PRIMARY KEY, title TEXT, content TEXT)')

    def seed_if_empty(table, rows):
        c.execute(f'SELECT COUNT(*) FROM {table}')
        if c.fetchone()[0] == 0:
            for row in rows:
                placeholders = ', '.join(['?'] * len(row))
                c.execute(f'INSERT INTO {table} VALUES (NULL, {placeholders})', row)

    seed_if_empty('facts', [
        ('39 ספרות מספיקות ליקום כולו',
         'כדי לחשב את היקף היקום הנראה כולו ברמת דיוק של אטום מימן בודד, נדרשות בדיוק 39 ספרות אחרי הנקודה העשרונית של פאי.'),
        ('מספר נורמלי',
         'מתמטיקאים משערים שפאי הוא "מספר נורמלי". אם זה נכון, כל רצף מספרים אפשרי קיים איפשהו בתוך פאי.'),
        ('חוק פאי של אינדיאנה',
         'בשנת 1897, בית המחוקקים של אינדיאנה כמעט והעביר חוק שהגדיר את ערכו של פאי כ-3.2 במדויק.')
    ])

    seed_if_empty('videos', [
        ('איך פאי מתחבא בהתנגשויות (3Blue1Brown)', 'HEfHFsfGXjs',
         'הסבר מרתק על כיצד התנגשויות אלסטיות בין שני בלוקים אל מול קיר מחשבות את הספרות של פאי.'),
        ('התגלית ששינתה את פאי (Veritasium)', 'gMlf1ELvRzc',
         'הסיפור על איך אייזק ניוטון השתמש בחדו"א כדי לפרוץ את המחסום ההיסטורי של חישוב פאי.'),
        ('לייצר פאי באמצעות פשטידות', 'ZNiRzZ66YN0',
         'ניסוי משעשע לבדיקת הדיוק של חישוב פאי בעזרת מאות פשטידות פיזיות במעגל ענק.'),
        ('חוק אינדיאנה', 'bFNjA9LOPsg', 'הסיפור המלא על הפעם שבה ניסו לקבוע בחוק שפאי שווה ל-3.2.')
    ])

    seed_if_empty('songs', [
        ('גרסת ה-100 ספרות', '3HRkKznJoZA'),
        ('גרסת ה-200 ספרות', 'd0lXrqjM_m8'),
        ('גרסת ה-300 ספרות', 'xsrJdSaiD9U'),
        ('גרסת ה-400 ספרות (חדש!)', 'q-9PXV0UfkA')
    ])

    seed_if_empty('recipes', [
        ('פאי תפוחים קלאסי',
         'מצרכים לבצק: 300 גרם קמח, 200 גרם חמאה קרה, חצי כוס אבקת סוכר, ביצה, 2 כפות מים קרים.\nמצרכים למלית: 6 תפוחי עץ, 100 גרם סוכר חום, כפית קינמון, 2 כפות קורנפלור, מיץ חצי לימון, 20 גרם חמאה.',
         'במעבד מזון מעבדים את הקמח, החמאה ואבקת הסוכר. מוסיפים ביצה ומים ומעבדים. מחלקים ל-2, ומקררים.\nבסיר קטן מבשלים תפוחים, סוכר, לימון וקינמון. מוסיפים קורנפלור וחמאה ומערבבים עד להסמכה. מצננים.\nמרדדים חלק אחד ומרפדים תבנית פאי. שופכים את המלית פנימה.\nמרדדים את החלק השני ויוצרים רשת עליונה וסמל פאי במרכז.\nאופים בתנור שחומם מראש ל-180 מעלות כ-45 דקות.'),
        ('פיצה פאי (Deep Dish Pizza)',
         'מצרכים לבצק: 500 גרם קמח, כף שמרים, כפית סוכר, כפית מלח, 300 מ"ל מים פושרים, 3 כפות שמן זית, 50 גרם חמאה מומסת.\nמצרכים למלית: רוטב עגבניות, 400 גרם מוצרלה מגורדת, תוספות (פפרוני, פטריות).',
         'לשים קמח, שמרים, סוכר, מלח, מים ושמן זית. מתפיחים שעה.\nמרדדים למלבן, מורחים חמאה מומסת, ומקפלים. מתפיחים 45 דקות.\nמשמנים תבנית עמוקה במיוחד ומרפדים בבצק.\nהסדר הפוך מפיצה רגילה: מניחים שכבה עבה של מוצרלה, מניחים מעל תוספות, ומכסים הכל ברוטב עגבניות.\nאופים ב-220 מעלות למשך 25-30 דקות.')
    ])

    seed_if_empty('methods', [
        ('שיטת המצולעים של ארכימדס',
         'ארכימדס מצא נוסחה שמאפשרת להכפיל את מספר הצלעות באמצעות משפט פיתגורס. הוא עבר מ-6 צלעות ל-96 צלעות. המצולע נצמד למעגל כך שהוא הוכיח שפאי נמצא בדיוק בין 22/7 לבין 223/71.'),
        ('הטור של לייבניץ-גרגורי',
         'לייבניץ מצא את הפיתוח לטור טיילור של פונקציית הארכטנגנס. אם נתחיל ב-1, נחסר שליש, נוסיף חמישית, נחסר שביעית וכו\', התוצאה תהיה בדיוק רבע מפאי.'),
        ('שיטת אייזק ניוטון',
         'ניוטון חתך רבע מעגל והשתמש במשפט הבינום כדי להפוך את הפונקציה לטור אינסופי של חזקות. התוצאה הייתה טור שמתכנס במהירות עצומה.'),
        ('מונטה קרלו',
         'יוצרים ריבוע בגודל 2x2 ובתוכו חוסמים עיגול עם רדיוס 1. המחשב זורק "חצים" באקראי. היחס בין החצים בעיגול לסך החצים ישאף להיות בדיוק π/4.')
    ])

    conn.commit()
    conn.close()


@app.route('/')
def home():
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()
    c.execute('SELECT id, name, content, image_filename FROM submissions WHERE approved=1')
    approved_submissions = c.fetchall()
    c.execute('SELECT id, title, content FROM facts')
    facts = c.fetchall()
    c.execute('SELECT id, title, youtube_id, description FROM videos')
    videos = c.fetchall()
    c.execute('SELECT id, title, ingredients, steps FROM recipes')
    recipes = c.fetchall()
    c.execute('SELECT id, title, youtube_id FROM songs')
    songs = c.fetchall()
    c.execute('SELECT id, title, content FROM methods')
    methods = c.fetchall()
    conn.close()

    is_admin = session.get('admin_logged_in', False)
    return render_template('index.html', submissions=approved_submissions, facts=facts, videos=videos, recipes=recipes,
                           songs=songs, methods=methods, is_admin=is_admin)


@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name', 'אנונימי')
    content = request.form.get('content', '')
    file = request.files.get('file')

    filename = ""
    filepath = ""
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    conn = sqlite3.connect('piday.db')
    c = conn.cursor()
    c.execute('INSERT INTO submissions (name, content, image_filename, approved) VALUES (?, ?, ?, 0)',
              (name, content, filename))
    conn.commit()
    conn.close()

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = f"🔔 יום הפאי: יצירה חדשה ממתינה לאישור (מאת: {name})"

        body = f"""
היי מנהל האתר!

התקבלה יצירה חדשה באתר יום הפאי, והיא ממתינה לאישורך.

שם השולח: {name}
האם צורפה תמונה: {'כן (מצורפת למייל)' if filename else 'לא'}

תוכן היצירה:
--------------------------------
{content}
--------------------------------

כדי לאשר את היצירה ולפרסם אותה באתר, היכנס לפאנל הניהול שלך:
http://127.0.0.1:5000/pi_admin
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        if filename and os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                img_data = f.read()
            image = MIMEImage(img_data, name=filename)
            msg.attach(image)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD.replace(" ", ""))
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

    return jsonify({"status": "success"})


@app.route('/save_item/<item_type>', methods=['POST'])
def save_item(item_type):
    if not session.get('admin_logged_in'): return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.get_json()
    item_id = data.get('id')
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()
    if item_type in ['fact', 'method']:
        table = 'facts' if item_type == 'fact' else 'methods'
        if item_id:
            c.execute(f'UPDATE {table} SET title=?, content=? WHERE id=?', (data['title'], data['content'], item_id))
        else:
            c.execute(f'INSERT INTO {table} (title, content) VALUES (?, ?)', (data['title'], data['content']))
    elif item_type in ['video', 'song']:
        table = 'videos' if item_type == 'video' else 'songs'
        url = data['url']
        youtube_id = match.group(1) if (match := re.search(r'(?:v=|youtu\.be/|embed/)([^&?]+)', url)) else url
        if item_type == 'video':
            if item_id:
                c.execute('UPDATE videos SET title=?, youtube_id=?, description=? WHERE id=?',
                          (data['title'], youtube_id, data['description'], item_id))
            else:
                c.execute('INSERT INTO videos (title, youtube_id, description) VALUES (?, ?, ?)',
                          (data['title'], youtube_id, data['description']))
        else:
            if item_id:
                c.execute('UPDATE songs SET title=?, youtube_id=? WHERE id=?', (data['title'], youtube_id, item_id))
            else:
                c.execute('INSERT INTO songs (title, youtube_id) VALUES (?, ?)', (data['title'], youtube_id))
    elif item_type == 'recipe':
        if item_id:
            c.execute('UPDATE recipes SET title=?, ingredients=?, steps=? WHERE id=?',
                      (data['title'], data['ingredients'], data['steps'], item_id))
        else:
            c.execute('INSERT INTO recipes (title, ingredients, steps) VALUES (?, ?, ?)',
                      (data['title'], data['ingredients'], data['steps']))
    elif item_type == 'submission':
        if item_id: c.execute('UPDATE submissions SET name=?, content=? WHERE id=?',
                              (data['name'], data['content'], item_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


@app.route('/delete_item/<item_type>/<int:item_id>', methods=['POST'])
def delete_item(item_type, item_id):
    if not session.get('admin_logged_in'): return jsonify({"status": "error"}), 401
    table_map = {'fact': 'facts', 'video': 'videos', 'recipe': 'recipes', 'submission': 'submissions', 'song': 'songs',
                 'method': 'methods'}
    if item_type not in table_map: return jsonify({"status": "error"}), 400
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()

    if item_type == 'submission':
        c.execute('SELECT image_filename FROM submissions WHERE id=?', (item_id,))
        row = c.fetchone()
        if row and row[0]:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
            if os.path.exists(filepath):
                os.remove(filepath)

    c.execute(f'DELETE FROM {table_map[item_type]} WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


@app.route('/search_pi', methods=['POST'])
def search_pi():
    data = request.get_json()
    query = data.get('query', '')
    if not query.isdigit(): return jsonify({"status": "error", "message": "Invalid input"})
    try:
        with open('static/pi.txt', 'rb') as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            pos = mm.find(query.encode('ascii'))
            mm.close()
            if pos != -1:
                return jsonify({"status": "success", "index": pos})
            else:
                return jsonify({"status": "not_found"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/pi_admin', methods=['GET', 'POST'])
def pi_admin():
    if request.method == 'POST':
        if request.form.get('password') == '3.1415':
            session['admin_logged_in'] = True
            return redirect('/')
        return "Password Incorrect", 401
    if session.get('admin_logged_in'): return redirect('/dashboard')
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'): return redirect('/pi_admin')
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()
    c.execute('SELECT id, name, content, image_filename FROM submissions WHERE approved=0')
    pending = c.fetchall()
    conn.close()
    return render_template('dashboard.html', pending=pending)


@app.route('/approve/<int:sub_id>')
def approve(sub_id):
    if not session.get('admin_logged_in'): return redirect('/pi_admin')
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()
    c.execute('UPDATE submissions SET approved=1 WHERE id=?', (sub_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')


@app.route('/reject/<int:sub_id>')
def reject(sub_id):
    if not session.get('admin_logged_in'): return redirect('/pi_admin')
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()

    c.execute('SELECT image_filename FROM submissions WHERE id=?', (sub_id,))
    row = c.fetchone()
    if row and row[0]:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row[0])
        if os.path.exists(filepath):
            os.remove(filepath)

    c.execute('DELETE FROM submissions WHERE id=?', (sub_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect('/')

@app.route('/api/check_updates')
def check_updates():
    # פונקציה שמחזירה את כמות היצירות המאושרות באתר
    conn = sqlite3.connect('piday.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM submissions WHERE approved=1')
    count = c.fetchone()[0]
    conn.close()
    return jsonify({"approved_count": count})

if __name__ == '__main__':
    init_db()

    app.run(debug=True)
