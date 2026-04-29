import io

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from domain.entities.progress_report import ProgressReport


class ReportGenerator:

    def export_csv(self, report: ProgressReport) -> bytes:
        rows = []
        for w in report.weekly_stats:
            rows.append({
                "week_start": w.week_start.isoformat(),
                "workouts": w.workouts,
                "avg_daily_calories": w.avg_calories,
                "weight_kg": w.weight_kg if w.weight_kg else "",
            })

        df = pd.DataFrame(rows)

        # summary row at the bottom
        summary = {
            "week_start": "TOTAL / SUMMARY",
            "workouts": report.workout_frequency,
            "avg_daily_calories": df["avg_daily_calories"].mean().round(1) if not df.empty else 0,
            "weight_kg": f"{report.weight_change_kg:+.1f} kg change",
        }
        df = pd.concat([df, pd.DataFrame([summary])], ignore_index=True)

        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

    def export_pdf(self, report: ProgressReport, user_name: str = "Client") -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # title
        story.append(Paragraph(f"Progress Report — {user_name}", styles["Title"]))
        story.append(Paragraph(
            f"{report.period_start.isoformat()} to {report.period_end.isoformat()}",
            styles["Normal"]
        ))
        story.append(Spacer(1, 20))

        # summary section
        story.append(Paragraph("Summary", styles["Heading2"]))
        summary_data = [
            ["Metric", "Value"],
            ["Weight Change", f"{report.weight_change_kg:+.2f} kg"],
            ["Total Workouts", str(report.workout_frequency)],
            ["Goal Completion Rate", f"{report.goal_completion_rate:.1f}%"],
        ]
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E75B6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FA")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # weekly breakdown
        if report.weekly_stats:
            story.append(Paragraph("Weekly Breakdown", styles["Heading2"]))
            weekly_data = [["Week Starting", "Workouts", "Avg Calories/Day", "Weight (kg)"]]
            for w in report.weekly_stats:
                weekly_data.append([
                    w.week_start.isoformat(),
                    str(w.workouts),
                    f"{w.avg_calories:.0f}",
                    f"{w.weight_kg:.1f}" if w.weight_kg else "—",
                ])
            weekly_table = Table(weekly_data, colWidths=[130, 80, 130, 100])
            weekly_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E75B6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4FA")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(weekly_table)

        doc.build(story)
        return buf.getvalue()
