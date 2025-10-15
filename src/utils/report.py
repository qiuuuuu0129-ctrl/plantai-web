# src/utils/report.py
# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import mm

def generate_pdf_report(items, outfile, title="PlantAI 报告"):
    c = canvas.Canvas(outfile, pagesize=A4)
    W, H = A4
    c.setTitle(title)

    # 标题
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, (H-20*mm), title)

    # 简单统计
    n = len(items)
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, (H-30*mm), f"数据条目: {n}")

    # 表格（截取前40条）
    headers = ["时间","温度°C","湿度%","光照lux","CO₂ ppm","TVOC ppb","土壤湿度%"]
    data = [headers]
    for r in items[:40]:
        row = [r.get("时间",""),
               str(r.get("温度°C","")),
               str(r.get("湿度%","")),
               str(r.get("光照lux","")),
               str(r.get("CO₂ ppm","")),
               str(r.get("TVOC ppb","")),
               str(r.get("土壤湿度%",""))]
        data.append(row)

    table = Table(data, colWidths=[28*mm,18*mm,18*mm,18*mm,18*mm,18*mm,24*mm])
    table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    table.wrapOn(c, 20*mm, 20*mm)
    table.drawOn(c, 20*mm, H-45*mm- (len(data)*6) )

    c.showPage()
    c.save()
    return outfile
