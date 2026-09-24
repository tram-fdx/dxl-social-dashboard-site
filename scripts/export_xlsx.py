# -*- coding: utf-8 -*-
"""Xuất dxl-metrics.xlsx từ rollup.json của cả ba báo cáo.

Chạy SAU khi cả ba repo đã chạy scripts/build_rollup.py trong cùng lượt quét:

  python3 scripts/export_xlsx.py \
     --social <đường dẫn repo social> \
     --seo    <đường dẫn repo seo> \
     --audit  <đường dẫn repo audit> \
     --out    dxl-metrics.xlsx

File Excel là ĐẦU RA DẪN XUẤT, cùng nguồn với dashboard (data/rollup.json),
nên hai bên không bao giờ lệch nhau. Không sửa tay — lượt sau ghi đè.
"""
import argparse, json, io, os, datetime, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ap = argparse.ArgumentParser()
ap.add_argument('--social', required=True)
ap.add_argument('--seo', required=True)
ap.add_argument('--audit', required=True)
ap.add_argument('--out', default='dxl-metrics.xlsx')
A = ap.parse_args()
REPOS = [(A.social,'Social'), (A.seo,'SEO'), (A.audit,'Audit')]

FONT='Arial'
H_FILL=PatternFill('solid',fgColor='2C3440'); H_FONT=Font(name=FONT,size=10,bold=True,color='FFFFFF')
SUB=Font(name=FONT,size=9,italic=True,color='6B727C')
BODY=Font(name=FONT,size=10)
BOLD=Font(name=FONT,size=10,bold=True)
TITLE=Font(name=FONT,size=14,bold=True,color='12161C')
G_DAY=PatternFill('solid',fgColor='E6F5ED'); G_WIN=PatternFill('solid',fgColor='FDF1E3'); G_ST=PatternFill('solid',fgColor='EEF1F5')
THIN=Border(bottom=Side('thin',color='E6E9EE'))

roll={}
for repo,label in REPOS:
    roll[label]=json.load(io.open(os.path.join(repo,'data','rollup.json'),encoding='utf-8'))

wb=Workbook(); ws=wb.active; ws.title='Đọc trước'
ws.column_dimensions['A'].width=3; ws.column_dimensions['B'].width=26; ws.column_dimensions['C'].width=104
r=2
ws.cell(r,2,'DX Living — dữ liệu báo cáo theo ngày').font=TITLE; r+=1
ws.cell(r,2,'Xuất ngày %s · nguồn: data/rollup.json của ba repo báo cáo'%datetime.date.today().isoformat()).font=SUB; r+=2
def row(k,v,fill=None):
    global r
    c1=ws.cell(r,2,k); c1.font=BOLD; c1.alignment=Alignment(vertical='top')
    c2=ws.cell(r,3,v); c2.font=BODY; c2.alignment=Alignment(wrap_text=True,vertical='top')
    if fill: c1.fill=fill; c2.fill=fill
    ws.row_dimensions[r].height=None
    r+=1
row('File này là gì','Bản xuất phẳng của dữ liệu đã lưu trong ba báo cáo DX Living, để đọc bằng tay và dựng báo cáo tháng. KHÔNG phải nguồn sự thật.')
row('Nguồn sự thật','data/YYYY-MM-DD.json trong mỗi repo — bất biến, mỗi ngày một file, không bao giờ sửa. File Excel này và dashboard cùng đọc từ data/rollup.json, nên không bao giờ lệch nhau.')
row('Sửa file này thì sao','Không ảnh hưởng gì tới báo cáo. Lần xuất sau sẽ ghi đè.')
r+=1
ws.cell(r,2,'BA LOẠI CHỈ SỐ — đọc kỹ trước khi cộng').font=Font(name=FONT,size=11,bold=True); r+=1
row('day','Số đo của đúng ngày đó. CỘNG DỒN ĐƯỢC. Hiện chỉ Social có (Facebook và Instagram), dựng lại từ chuỗi 28 giá trị lưu sẵn trong mỗi file ngày.',G_DAY)
row('window28','Đã là tổng của 28 ngày trước đó. KHÔNG ĐƯỢC CỘNG — hai ngày liền nhau chồng nhau 27 ngày, cộng lại là đếm trùng nhiều lần. Chỉ so đầu kỳ với cuối kỳ.',G_WIN)
row('state','Giá trị tại thời điểm quét (điểm số, tốc độ, số follower). Không cộng — lấy giá trị cuối kỳ hoặc trung bình.',G_ST)
r+=1
row('Ô trống','Ngày đó không đo chỉ số này. Không suy ra, không điền 0.')
row('Ngày không quét','Không bao giờ được nội suy. Ví dụ không có bản quét 20/09/2026.')
row('Meta điều chỉnh số','Với chuỗi day của Social, mỗi ngày giữ lần đọc MỚI NHẤT — Meta có sửa số về sau.')
r+=2
ws.cell(r,2,'CÁC SHEET').font=Font(name=FONT,size=11,bold=True); r+=1

sheets=[]
def add_sheet(name, label, grains, note):
    data=roll[label]
    keys=[k for k in sorted(data['series']) if data['series'][k]['grain'] in grains]
    if not keys: return None
    dates=sorted({p['d'] for k in keys for p in data['series'][k]['points']})
    s=wb.create_sheet(name)
    s.cell(1,1,name).font=TITLE
    s.cell(2,1,note).font=SUB
    s.cell(3,1,'Nguồn: %s/data/rollup.json · %d ngày · %d chỉ số'%(label,len(dates),len(keys))).font=SUB
    hr=5
    s.cell(hr,1,'Ngày').font=H_FONT; s.cell(hr,1).fill=H_FILL
    s.cell(hr-1,1,'grain →').font=SUB
    for j,k in enumerate(keys):
        ser=data['series'][k]; col=j+2
        c=s.cell(hr,col,ser['label']); c.font=H_FONT; c.fill=H_FILL
        c.alignment=Alignment(wrap_text=True,vertical='bottom')
        g=s.cell(hr-1,col,ser['grain']); g.font=Font(name=FONT,size=8,bold=True,color='4A5260')
        g.fill={'day':G_DAY,'window28':G_WIN,'state':G_ST}[ser['grain']]
        g.alignment=Alignment(horizontal='center')
        s.column_dimensions[get_column_letter(col)].width=15
    s.column_dimensions['A'].width=12
    idx={k:{p['d']:p['v'] for p in data['series'][k]['points']} for k in keys}
    for i,d in enumerate(dates):
        rr=hr+1+i
        dc=s.cell(rr,1,datetime.date.fromisoformat(d)); dc.number_format='yyyy-mm-dd'; dc.font=BODY; dc.border=THIN
        for j,k in enumerate(keys):
            v=idx[k].get(d)
            c=s.cell(rr,j+2, v if v is not None else None); c.font=BODY; c.border=THIN
            if v is not None and isinstance(v,float) and v!=int(v): c.number_format='0.00'
            else: c.number_format='#,##0'
    s.freeze_panes=s.cell(hr+1,2)
    sheets.append((name,label,keys,dates,hr))
    return s

add_sheet('Social — theo ngày','Social',{'day'},'Số theo NGÀY THẬT — cộng dồn được. Dựng lại từ chuỗi 28 giá trị trong mỗi file ngày, giữ lần đọc mới nhất cho mỗi ngày.')
add_sheet('Social — 28 ngày','Social',{'window28','state'},'Ảnh chụp cửa sổ 28 ngày và chỉ số trạng thái — KHÔNG cộng dồn. Chỉ so đầu kỳ với cuối kỳ.')
add_sheet('SEO','SEO',{'window28','state'},'GSC/GA4 là cửa sổ 28 ngày trượt; Ahrefs, TTFB, sitemap là trạng thái. KHÔNG cộng dồn.')
add_sheet('Audit','Audit',{'state'},'Mỗi dòng là một lần crawl tại thời điểm. Điểm số và tốc độ — KHÔNG cộng dồn.')

for nm,_,ks,ds,_ in sheets:
    row(nm,'%d dòng × %d chỉ số · %s → %s'%(len(ds),len(ks),ds[0],ds[-1]))

# ---- Tổng hợp tháng: dùng CÔNG THỨC tham chiếu sheet dữ liệu ----
ms=wb.create_sheet('Tổng hợp tháng')
ms.cell(1,1,'Tổng hợp theo tháng').font=TITLE
ms.cell(2,1,'Mọi ô dưới đây là CÔNG THỨC trỏ về các sheet dữ liệu — sửa dữ liệu thì số này tự đổi.').font=SUB
ms.cell(3,1,'Chỉ chuỗi grain "day" mới được CỘNG (SUMIFS). window28 và state lấy GIÁ TRỊ NGÀY QUÉT CUỐI CÙNG của tháng (INDEX).').font=SUB
ms.column_dimensions['A'].width=34
mr=5
day_sheet=[s for s in sheets if s[0]=='Social — theo ngày']
if day_sheet:
    nm,label,keys,dates,hr=day_sheet[0]
    months=sorted({d[:7] for d in dates})
    ms.cell(mr,1,'CỘNG ĐƯỢC — số theo ngày thật (Social)').font=Font(name=FONT,size=11,bold=True)
    ms.cell(mr,1).fill=G_DAY; mr+=1
    ms.cell(mr,1,'Chỉ số').font=H_FONT; ms.cell(mr,1).fill=H_FILL
    for j,mo in enumerate(months):
        c=ms.cell(mr,j+2,mo); c.font=H_FONT; c.fill=H_FILL; c.alignment=Alignment(horizontal='center')
        ms.column_dimensions[get_column_letter(j+2)].width=13
    mr+=1
    q="'"+nm+"'"
    n=len(dates); first=hr+1; last=hr+n
    for i,k in enumerate(keys):
        col=get_column_letter(i+2)
        ms.cell(mr,1,roll[label]['series'][k]['label']).font=BODY
        for j,mo in enumerate(months):
            y,m=int(mo[:4]),int(mo[5:7])
            start=datetime.date(y,m,1).isoformat()
            end=(datetime.date(y+(m==12),(m%12)+1,1)-datetime.timedelta(days=1)).isoformat()
            f='=SUMIFS({q}!{c}{f}:{c}{l},{q}!$A${f}:$A${l},">="&DATE({y},{m},1),{q}!$A${f}:$A${l},"<="&DATE({y2},{m2},{d2}))'.format(
                q=q,c=col,f=first,l=last,y=y,m=m,
                y2=int(end[:4]),m2=int(end[5:7]),d2=int(end[8:10]))
            cc=ms.cell(mr,j+2,f); cc.font=BODY; cc.number_format='#,##0'; cc.border=THIN
        mr+=1
    mr+=1
for nm,label,keys,dates,hr in sheets:
    if nm=='Social — theo ngày': continue
    months=sorted({d[:7] for d in dates})
    ms.cell(mr,1,'KHÔNG CỘNG — %s (lấy ngày quét cuối tháng)'%nm).font=Font(name=FONT,size=11,bold=True)
    ms.cell(mr,1).fill=G_WIN; mr+=1
    ms.cell(mr,1,'Chỉ số').font=H_FONT; ms.cell(mr,1).fill=H_FILL
    for j,mo in enumerate(months):
        c=ms.cell(mr,j+2,mo); c.font=H_FONT; c.fill=H_FILL; c.alignment=Alignment(horizontal='center')
    mr+=1
    q="'"+nm+"'"
    lastrow={}
    for i,d in enumerate(dates):
        lastrow[d[:7]]=hr+1+i      # dòng của ngày quét cuối cùng trong tháng
    for i,k in enumerate(keys):
        col=get_column_letter(i+2)
        ms.cell(mr,1,roll[label]['series'][k]['label']).font=BODY
        for j,mo in enumerate(months):
            rr=lastrow[mo]
            cc=ms.cell(mr,j+2,'={q}!{c}{r}'.format(q=q,c=col,r=rr))
            cc.font=BODY; cc.number_format='#,##0.##'; cc.border=THIN
        mr+=1
    mr+=1

out=A.out
wb.save(out)
print('wrote',out,os.path.getsize(out),'bytes')
print('sheets:',wb.sheetnames)
