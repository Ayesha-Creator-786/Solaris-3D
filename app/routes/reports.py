from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response
from flask_login import login_required, current_user
from app.models import SolarData, Report, db, ActivityLog, Alert
from sqlalchemy import func
import datetime
from io import BytesIO

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        # Generate custom report log entry
        report_type = request.form.get('report_type')
        title = request.form.get('title')
        
        today = datetime.date.today()
        if report_type == 'daily':
            start_date = today
            end_date = today
        elif report_type == 'weekly':
            start_date = today - datetime.timedelta(days=7)
            end_date = today
        else: # monthly
            start_date = today - datetime.timedelta(days=30)
            end_date = today

        # Fetch solar records in range
        solar_records = SolarData.query.filter(SolarData.date >= start_date, SolarData.date <= end_date).all()
        
        # Calculate summary numbers
        total_actual = sum(s.solar_output for s in solar_records) if solar_records else 0.0
        total_predicted = sum(s.predicted_output for s in solar_records) if solar_records else 0.0
        avg_efficiency = (total_actual / total_predicted * 100) if total_predicted > 0 else 100.0
        
        # Summary description
        content_summary = (
            f"Generated {report_type.capitalize()} Report: '{title}'. "
            f"Analyzed {len(solar_records)} data samples between {start_date} and {end_date}. "
            f"Total actual output was {round(total_actual, 2)} kW. "
            f"Total predicted output by AI model was {round(total_predicted, 2)} kW. "
            f"Average recorded system efficiency: {round(avg_efficiency, 2)}%."
        )

        new_report = Report(
            report_type=report_type,
            title=title,
            content=content_summary,
            start_date=start_date,
            end_date=end_date,
            user_id=current_user.id
        )
        db.session.add(new_report)

        # Log action
        log = ActivityLog(
            action=f"Created {report_type} report: {title}",
            user_email=current_user.email,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        flash(f"{report_type.capitalize()} report generated and logged successfully!", "success")
        return redirect(url_for('reports.index'))

    # Load recent logged reports
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template('reports.html', reports=reports)


@reports_bp.route('/reports/export/<int:report_id>')
@login_required
def export_pdf(report_id):
    report = Report.query.get_or_404(report_id)
    
    # Retrieve data in that range
    records = SolarData.query.filter(
        SolarData.date >= report.start_date,
        SolarData.date <= report.end_date
    ).order_by(SolarData.date.desc(), SolarData.hour.desc()).all()

    # Create PDF using ReportLab
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()

    # Custom Header Style
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#0d6efd'), # Blue
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        name='H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=15,
        textColor=colors.HexColor('#198754'), # Green
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        name='BodyStyle',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8
    )

    # Document Header
    story.append(Paragraph("SolarIQ Energy Report", title_style))
    story.append(Paragraph(f"Report Title: <b>{report.title}</b>", body_style))
    story.append(Paragraph(f"Type: {report.report_type.capitalize()} Report", body_style))
    story.append(Paragraph(f"Report Period: {report.start_date} to {report.end_date}", body_style))
    story.append(Paragraph(f"Generated On: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}", body_style))
    story.append(Spacer(1, 15))

    # Summary Section
    story.append(Paragraph("Executive Summary", h2_style))
    story.append(Paragraph(report.content, body_style))
    story.append(Spacer(1, 15))

    # Recommendations Section
    story.append(Paragraph("Smart Energy Recommendations", h2_style))
    # Pick suitable recommendations based on efficiency
    total_actual = sum(s.solar_output for s in records)
    total_predicted = sum(s.predicted_output for s in records)
    avg_eff = (total_actual / total_predicted * 100) if total_predicted > 0 else 100.0

    if avg_eff >= 92:
        rec_text = "System is performing with EXCELLENT efficiency. Maintain current configuration. Best window for high energy consuming appliances is still 11 AM - 3 PM."
    elif avg_eff >= 80:
        rec_text = "System performance is GOOD but shows some minor constraints. Ensure there is no new shading from tree growth. Clean panels if output drops gradually."
    else:
        rec_text = "System performance is POOR/MODERATE. Predictive maintenance alert generated: Panels have high probability of dust buildup or cable alignment anomalies. A manual panel inspection and cleaning is highly recommended."
    story.append(Paragraph(rec_text, body_style))
    story.append(Spacer(1, 15))

    # Table of recent readings (limit table to first 30 entries to avoid massive PDF size)
    story.append(Paragraph("Generation Readings Summary Table", h2_style))
    
    # Table headers
    data = [['Date', 'Hour', 'Temp (°C)', 'Irradiance', 'Cloud %', 'Actual (kW)', 'Pred (kW)', 'Efficiency']]
    for r in records[:30]:
        data.append([
            r.date.strftime('%Y-%m-%d'),
            f"{r.hour}:00",
            str(r.temperature),
            str(r.irradiance),
            f"{int(r.cloud_cover)}%",
            f"{r.solar_output} kW",
            f"{r.predicted_output} kW",
            f"{r.efficiency_score}%"
        ])

    table = Table(data, colWidths=[70, 45, 55, 65, 55, 75, 75, 75])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9.5),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8f9fa')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f1f3f5')])
    ]))

    story.append(table)
    
    # Build document
    doc.build(story)
    
    # Get pdf data
    pdf_output = buffer.getvalue()
    buffer.close()
    
    response = make_response(pdf_output)
    response.headers['Content-Disposition'] = f"attachment; filename=solariq_report_{report_id}.pdf"
    response.headers['Content-Type'] = 'application/pdf'
    
    # Log Action
    log = ActivityLog(
        action=f"Exported PDF for report: '{report.title}'",
        user_email=current_user.email,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    return response
