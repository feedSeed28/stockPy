import pymysql, os, sys
from pymysql.cursors import SSCursor

conn = pymysql.connect(host='localhost',port=3306,user='admin',password='ZggDLAXkkHXFwQVM',database='stock_data',charset='utf8mb4')
cur = conn.cursor()
cur.execute('SHOW TABLES')
tables = [t[0] for t in cur.fetchall() if t[0] != 'alembic_version']
cur.close()

out = os.path.join(os.path.dirname(__file__), '..', '..', 'stock_data_dump.sql')

with open(out, 'w', encoding='utf8') as f:
    f.write('SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n\n')
    
    for table in tables:
        # Use fresh connection + SSCursor for each table
        tconn = pymysql.connect(host='localhost',port=3306,user='admin',password='ZggDLAXkkHXFwQVM',database='stock_data',charset='utf8mb4')
        tcur = tconn.cursor()
        tcur.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = tcur.fetchone()[0]
        tcur.close()
        tconn.close()
        
        if count == 0:
            print(f'  {table}: 0 rows, skipped')
            continue
        
        # Stream with SSCursor
        sconn = pymysql.connect(host='localhost',port=3306,user='admin',password='ZggDLAXkkHXFwQVM',database='stock_data',charset='utf8mb4',
                                cursorclass=SSCursor)
        scur = sconn.cursor()
        scur.execute(f"SELECT * FROM `{table}`")
        cols = [d[0] for d in scur.description]
        col_str = "`,`".join(cols)
        
        f.write(f"INSERT INTO `{table}` (`{col_str}`) VALUES\n")
        first = True
        written = 0
        batch = []
        
        for row in scur:
            vals = []
            for v in row:
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float)):
                    vals.append(str(v))
                elif isinstance(v, bytes):
                    vals.append("'" + v.decode('utf8','replace').replace("\\","\\\\").replace("'","\'") + "'")
                else:
                    sv = str(v).replace("\\","\\\\").replace("'","\'")
                    vals.append("'"+sv+"'")
            batch.append("(" + ",".join(vals) + ")")
            
            if len(batch) >= 500:
                if not first:
                    f.write(",\n")
                f.write(",\n".join(batch))
                first = False
                written += len(batch)
                batch = []
                if written % 500000 == 0:
                    print(f'  {table}: {written:,} / {count:,}')
        
        if batch:
            if not first:
                f.write(",\n")
            f.write(",\n".join(batch))
            written += len(batch)
        
        f.write(";\n\n")
        scur.close()
        sconn.close()
        print(f'  {table}: {written:,} rows done')

    f.write('SET FOREIGN_KEY_CHECKS=1;\n')

size_mb = os.path.getsize(out) / 1024 / 1024
print(f'\nDone! {out} ({size_mb:.0f} MB)')
