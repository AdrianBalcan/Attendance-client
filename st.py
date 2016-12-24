from pysqlcipher import dbapi2 as sqlite
import datetime
conn = sqlite.connect('att')
c = conn.cursor()
c.execute("PRAGMA key='0jFr90a'")
try:
    c.execute('''create table config (fingerprints_limit int, devicegroup int, date text)''')
    c.execute("""insert into config values (0,0, '"""+str(datetime.datetime.now())+"""')""")
    conn.commit()
except Exception as e:
    print('str(e)')
c.close()


c = conn.cursor()
c.execute("PRAGMA key='0jFr90a'")
c.execute("SELECT * FROM config;")
print(c.fetchall())
c.close()
