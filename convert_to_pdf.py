#!/usr/bin/env python3
"""
Convert PROJECT_DOCUMENTATION.md to PDF
"""

from fpdf import FPDF
import re
import os

def sanitize_text(text):
    """Replace box-drawing characters with ASCII alternatives"""
    replacements = {
        '┌': '+', '┐': '+', '└': '+', '┘': '+',
        '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
        '─': '-', '│': '|',
        '▓': '#', '▼': 'v', '►': '>',
        '◄': '<', '▲': '^', '●': '*', '○': 'o',
        '✅': '[x]', '✓': '[x]',
        '→': '->', '←': '<-', '↓': 'v', '↑': '^',
        '—': '-', '–': '-', '"': '"', '"': '"',
        ''': "'", ''': "'", '…': '...',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font('DejaVu', '', 'C:/Windows/Fonts/arial.ttf')
        self.add_font('DejaVu', 'B', 'C:/Windows/Fonts/arialbd.ttf')
        self.add_font('DejaVu', 'I', 'C:/Windows/Fonts/ariali.ttf')
        
    def header(self):
        self.set_font('DejaVu', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, 'CAMEROON HOUSE IMMATRICULATION SYSTEM - Technical Design Document', 0, new_x='LMARGIN', new_y='NEXT', align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, align='C')

    def chapter_title(self, title, level=1):
        if level == 1:
            self.set_font('DejaVu', 'B', 16)
            self.set_text_color(0, 51, 102)
        elif level == 2:
            self.set_font('DejaVu', 'B', 14)
            self.set_text_color(0, 76, 153)
        elif level == 3:
            self.set_font('DejaVu', 'B', 12)
            self.set_text_color(51, 102, 153)
        else:
            self.set_font('DejaVu', 'B', 11)
            self.set_text_color(76, 114, 152)
        
        self.ln(5)
        self.multi_cell(0, 8, sanitize_text(title))
        self.ln(3)

    def body_text(self, text):
        self.set_font('DejaVu', '', 10)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 6, sanitize_text(text))
        self.ln(2)

    def code_block(self, text):
        self.set_font('DejaVu', '', 8)
        self.set_fill_color(245, 245, 245)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 5, sanitize_text(text), fill=True)
        self.ln(3)

    def table_row(self, cells, is_header=False):
        if is_header:
            self.set_font('DejaVu', 'B', 9)
            self.set_fill_color(0, 51, 102)
            self.set_text_color(255, 255, 255)
        else:
            self.set_font('DejaVu', '', 9)
            self.set_fill_color(255, 255, 255)
            self.set_text_color(0, 0, 0)
        
        col_width = (self.w - 20) / len(cells) if cells else self.w - 20
        for cell in cells:
            self.cell(col_width, 7, sanitize_text(str(cell)[:30]), 1, new_x='RIGHT', new_y='TOP', align='L', fill=True)
        self.ln()


def parse_markdown_to_pdf(md_file, pdf_file):
    """Parse markdown and create PDF"""
    
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    in_code_block = False
    code_content = []
    in_table = False
    table_rows = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip empty lines
        if not line.strip():
            if in_table and table_rows:
                # End table
                for idx, row in enumerate(table_rows):
                    if idx > 1:  # Skip separator row
                        cells = [c.strip() for c in row.split('|')[1:-1] if c.strip()]
                        if cells:
                            pdf.table_row(cells, is_header=(idx == 0))
                table_rows = []
                in_table = False
            i += 1
            continue
        
        # Code blocks
        if line.strip().startswith('```'):
            if in_code_block:
                pdf.code_block('\n'.join(code_content))
                code_content = []
            in_code_block = not in_code_block
            i += 1
            continue
        
        if in_code_block:
            code_content.append(line)
            i += 1
            continue
        
        # Headers
        if line.startswith('#'):
            level = len(line.split()[0])
            title = line.lstrip('#').strip()
            pdf.chapter_title(title, level)
            i += 1
            continue
        
        # Tables
        if '|' in line and not line.strip().startswith('```'):
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append(line)
            i += 1
            continue
        
        # Process table if we were in one
        if in_table and table_rows:
            for idx, row in enumerate(table_rows):
                if '---' in row:
                    continue
                cells = [c.strip() for c in row.split('|')[1:-1] if c.strip() or row.count('|') > 2]
                if cells:
                    pdf.table_row(cells, is_header=(idx == 0))
            table_rows = []
            in_table = False
        
        # Bold text removal for clean display
        clean_line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
        clean_line = re.sub(r'\*(.*?)\*', r'\1', clean_line)
        clean_line = re.sub(r'`(.*?)`', r'\1', clean_line)
        
        # Regular text
        if clean_line.strip() and not clean_line.startswith('---'):
            # Check for bullet points
            if clean_line.strip().startswith('- ') or clean_line.strip().startswith('* '):
                pdf.body_text('  * ' + clean_line.strip()[2:])
            elif re.match(r'^\d+\.', clean_line.strip()):
                pdf.body_text('  ' + clean_line.strip())
            else:
                pdf.body_text(clean_line)
        
        i += 1
    
    # Save PDF
    pdf.output(pdf_file)
    print(f"PDF created successfully: {pdf_file}")


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_file = os.path.join(script_dir, 'PROJECT_DOCUMENTATION.md')
    pdf_file = os.path.join(script_dir, 'PROJECT_DOCUMENTATION.pdf')
    
    parse_markdown_to_pdf(md_file, pdf_file)
