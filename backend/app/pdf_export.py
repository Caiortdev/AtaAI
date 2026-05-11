import re
import textwrap
from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain import Meeting, Priority


@dataclass(frozen=True)
class PdfLine:
    text: str
    font_size: int = 10
    indent: int = 0
    spacing_after: int = 4


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 54
MARGIN_TOP = 56
MARGIN_BOTTOM = 56
LINE_HEIGHT_MULTIPLIER = 1.35

priority_label: dict[Priority, str] = {
    Priority.critical: "Critica",
    Priority.high: "Alta",
    Priority.medium: "Media",
    Priority.low: "Baixa",
}


def generate_meeting_pdf(meeting: Meeting) -> bytes:
    if meeting.analysis is None:
        raise ValueError("A reuniao ainda nao possui ata para exportar.")

    lines = build_pdf_lines(meeting)
    pages = paginate(lines)
    return build_pdf_document(pages)


def build_pdf_lines(meeting: Meeting) -> list[PdfLine]:
    analysis = meeting.analysis
    if analysis is None:
        return []

    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    participants = ", ".join(meeting.participants) if meeting.participants else "Nao informado"
    lines: list[PdfLine] = [
        PdfLine("Ata de reuniao", font_size=18, spacing_after=12),
        PdfLine(f"Titulo: {meeting.title}", font_size=11),
        PdfLine(f"Cliente: {meeting.client_name or 'Nao informado'}", font_size=11),
        PdfLine(f"Participantes: {participants}", font_size=11),
        PdfLine(f"Gerado em: {generated_at}", font_size=9, spacing_after=14),
        PdfLine("Ata revisada", font_size=14, spacing_after=8),
    ]
    lines.extend(markdown_to_pdf_lines(analysis.minutes_markdown))

    if analysis.tasks:
        lines.append(PdfLine("", spacing_after=6))
        lines.append(PdfLine("Tarefas", font_size=14, spacing_after=8))
        for index, task in enumerate(analysis.tasks, 1):
            priority = priority_label.get(task.priority, task.priority.value)
            status = task.status.replace("_", " ")
            lines.append(
                PdfLine(
                    f"{index}. {task.title} [{priority} / {status}]",
                    font_size=11,
                    spacing_after=5,
                )
            )
            lines.extend(wrap_text(task.description, font_size=10, indent=14))
            lines.extend(wrap_text(f"Motivo: {task.priority_reason}", font_size=9, indent=14))
            if task.owner:
                lines.extend(wrap_text(f"Responsavel: {task.owner}", font_size=9, indent=14))
            if task.due_date:
                lines.extend(wrap_text(f"Prazo: {task.due_date}", font_size=9, indent=14))
            lines.append(PdfLine("", spacing_after=6))

    return lines


def markdown_to_pdf_lines(markdown: str) -> list[PdfLine]:
    lines: list[PdfLine] = []
    for raw_line in markdown.splitlines():
        text = raw_line.strip()
        if not text:
            lines.append(PdfLine("", spacing_after=6))
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)$", text)
        if heading_match:
            level = len(heading_match.group(1))
            font_size = 14 if level == 1 else 12 if level == 2 else 11
            lines.extend(wrap_text(clean_markdown(heading_match.group(2)), font_size=font_size))
            continue

        bullet_match = re.match(r"^[-*]\s+(.+)$", text)
        if bullet_match:
            lines.extend(wrap_text(f"- {clean_markdown(bullet_match.group(1))}", indent=10))
            continue

        lines.extend(wrap_text(clean_markdown(text)))
    return lines


def clean_markdown(value: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text.replace("\\\"", '"')


def wrap_text(text: str, font_size: int = 10, indent: int = 0) -> list[PdfLine]:
    if not text:
        return [PdfLine("", font_size=font_size, indent=indent)]

    max_chars = max(28, int((PAGE_WIDTH - (MARGIN_X * 2) - indent) / (font_size * 0.5)))
    wrapped = textwrap.wrap(text, width=max_chars, break_long_words=False) or [text]
    return [PdfLine(line, font_size=font_size, indent=indent) for line in wrapped]


def paginate(lines: list[PdfLine]) -> list[list[PdfLine]]:
    pages: list[list[PdfLine]] = []
    current_page: list[PdfLine] = []
    y = PAGE_HEIGHT - MARGIN_TOP

    for line in lines:
        height = int(line.font_size * LINE_HEIGHT_MULTIPLIER) + line.spacing_after
        if current_page and y - height < MARGIN_BOTTOM:
            pages.append(current_page)
            current_page = []
            y = PAGE_HEIGHT - MARGIN_TOP
        current_page.append(line)
        y -= height

    if current_page:
        pages.append(current_page)
    return pages or [[PdfLine("Ata sem conteudo.")]]


def build_pdf_document(pages: list[list[PdfLine]]) -> bytes:
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_refs = " ".join(f"{3 + (index * 2)} 0 R" for index in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(pages)} >>".encode("ascii"))

    for index, page_lines in enumerate(pages):
        page_object_number = 3 + (index * 2)
        content_object_number = page_object_number + 1
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
            f"/BaseFont /Helvetica /Encoding /WinAnsiEncoding >> >> >> "
            f"/Contents {content_object_number} 0 R >>"
        )
        content = build_page_content(page_lines)
        stream = (
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"\nendstream"
        )
        objects.append(page.encode("ascii"))
        objects.append(stream)

    return assemble_pdf(objects)


def build_page_content(lines: list[PdfLine]) -> bytes:
    content = bytearray()
    y = PAGE_HEIGHT - MARGIN_TOP
    for line in lines:
        if line.text:
            x = MARGIN_X + line.indent
            content.extend(f"BT /F1 {line.font_size} Tf {x} {y} Td ".encode("ascii"))
            content.extend(encode_pdf_text(line.text))
            content.extend(b" Tj ET\n")
        y -= int(line.font_size * LINE_HEIGHT_MULTIPLIER) + line.spacing_after
    return bytes(content)


def encode_pdf_text(text: str) -> bytes:
    encoded = text.encode("cp1252", errors="replace")
    escaped = bytearray()
    for byte in encoded:
        if byte in (40, 41, 92):
            escaped.append(92)
        escaped.append(byte)
    return b"(" + bytes(escaped) + b")"


def assemble_pdf(objects: list[bytes]) -> bytes:
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def pdf_filename(meeting: Meeting) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", meeting.title.strip()).strip("-").lower()
    return f"ata-{slug or meeting.id}.pdf"
