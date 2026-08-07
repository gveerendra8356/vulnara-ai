import sqlite3

conn = sqlite3.connect('vulnara.db')
c = conn.cursor()
c.execute("UPDATE users SET email = replace(email, '.local', '.com') WHERE email LIKE '%.local'")
conn.commit()
conn.close()
