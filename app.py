story = [Paragraph(escape(t["report"]), styles["CyberMain"]),
             Paragraph(escape(t["title"]), styles["CyberSub"]),
             HRFlowable(width="100%", thickness=1.2, color=cyan, spaceAfter=7*mm)]

    photo_label = "Photographs" if lang == "en" else "छायाचित्रे"
    rows = [
        [t["date"], program["date"]],
        [t["station"], program["station"]],
        [t["place"], program["place"]],
        [t["name"], program["name"]],
        [t["attendees"], str(program["attendees"])],
        [t["details"], program["details"] or "—"],
        [photo_label, str(len(photos))],
    ]
    data = [[Paragraph(escape(str(label)), styles["CyberLabel"]),
             Paragraph(escape(str(value)).replace("\n", "<br/>"), styles["CyberValue"])] for label, value in rows]
    table = Table(data, colWidths=[43*mm, 124*mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
        ("BACKGROUND", (0,0), (0,-1), pale),
        ("BOX", (0,0), (-1,-1), 0.8, colors.HexColor("#b9d0e8")),
        ("INNERGRID", (0,0), (-1,-1), 0.45, colors.HexColor("#d8e5f2")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.extend([table, Spacer(1, 7*mm)])
    # Dimensional summary tile.
    summary = Table([[Paragraph(f'<font color="{blue.hexval()}"><b>{escape(t["attendees"])}</b></font>', styles["CyberLabel"]),
                      Paragraph(f'<font size="18"><b>{int(program["attendees"]):,}</b></font>', styles["CyberValue"]),
                      Paragraph(f'<font color="{blue.hexval()}"><b>{escape(photo_label)}</b></font>', styles["CyberLabel"]),
                      Paragraph(f'<font size="18"><b>{len(photos)}</b></font>', styles["CyberValue"])]],
                    colWidths=[35*mm, 48*mm, 35*mm, 49*mm])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#e4f2ff")),
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#8bbde8")),
        ("LINEBEFORE", (1,0), (1,0), 0.8, colors.HexColor("#b1d5f3")),
        ("LINEBEFORE", (2,0), (2,0), 0.8, colors.HexColor("#b1d5f3")),
        ("LINEBEFORE", (3,0), (3,0), 0.8, colors.HexColor("#b1d5f3")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.extend([summary, Spacer(1, 6*mm), Paragraph(escape(t["page_info"]), styles["CyberTiny"])])

    if photos:
        # Keep program information on page 1. Put up to four photographs
        # on each following page in a neat 2-by-2 gallery.
        valid_photos = []
        for photo in photos:
            path = os.path.join(UPLOAD_FOLDER, photo["filename"])
            if os.path.isfile(path):
                valid_photos.append((photo, path))

        for page_start in range(0, len(valid_photos), 4):
            if page_start == 0:
                story.append(PageBreak())
            else:
                story.append(PageBreak())
            story.extend([
                Paragraph(escape(t["photo_page"]), styles["CyberPhotoTitle"]),
                Paragraph("PHOTO EVIDENCE GALLERY  •  PROGRAM ATTACHMENTS", styles["CyberTiny"]),
                Spacer(1, 4*mm),
            ])
            batch = valid_photos[page_start:page_start + 4]
            cards = []
            for offset, (photo, path) in enumerate(batch, start=page_start + 1):
                try:
                    img = Image(path)
                    img._restrictSize(75*mm, 78*mm)
                    card = Table(
                        [[img], [Paragraph(f"{escape(photo_label)} {offset:02d}", styles["CyberPhotoCaption"])]],
                        colWidths=[78*mm], rowHeights=None, hAlign="CENTER"
                    )
                    card.setStyle(TableStyle([
                        ("BACKGROUND", (0,0), (-1,-1), colors.white),
                        ("BOX", (0,0), (-1,-1), 1.2, colors.HexColor("#8bbde8")),
                        ("LINEBELOW", (0,0), (-1,0), 3, cyan),
                        ("ALIGN", (0,0), (-1,-1), "CENTER"),
                        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                        ("LEFTPADDING", (0,0), (-1,-1), 5),
                        ("RIGHTPADDING", (0,0), (-1,-1), 5),
                        ("TOPPADDING", (0,0), (-1,-1), 5),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                    ]))
                    cards.append(card)
                except Exception:
                    app.logger.exception("Could not add photograph to PDF report")

            # Pad the final row if only one or two photographs remain.
            while len(cards) < 4:
                cards.append("")
            gallery_rows = [[cards[0], cards[1]], [cards[2], cards[3]]]
            gallery = Table(gallery_rows, colWidths=[82*mm, 82*mm], hAlign="CENTER")
            gallery.setStyle(TableStyle([
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("LEFTPADDING", (0,0), (-1,-1), 2),
                ("RIGHTPADDING", (0,0), (-1,-1), 2),
                ("TOPPADDING", (0,0), (-1,-1), 3),
                ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            story.append(gallery)

    story.extend([Spacer(1, 4*mm), Paragraph(escape(t["report_generated"]) + ": " + datetime.now().strftime("%Y-%m-%d %H:%M"), styles["CyberTiny"])])
    doc.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"program_report_{program_id}.pdf")

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="SAMEORIGIN"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Cache-Control"]="no-store"
    return response

@app.errorhandler(413)
def too_large(error):
    return "The complete upload request is too large. The current application limit is 50 MB total for the form and all photographs. Please choose smaller/compressed photos.",413

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)),debug=False)
