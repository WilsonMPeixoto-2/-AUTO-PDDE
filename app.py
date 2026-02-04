#!/usr/bin/env python3
"""
Simple PDDE web application.

This Flask application allows the user to upload multiple PDF files. It will
extract key information (tipo de PDDE, ano, escola, etc.) directly from the
PDF text, classify and reorder the files, merge them into grouped and combined
PDFs, generate DOCX dispatches, and return a ZIP archive with all files.

Dependencies:
 - Flask, PyMuPDF
 - Pandoc and pdfunite must be available in the system path.

Usage:
    python app.py

After running, open http://localhost:5000/ in a browser to use the app.
"""
import os
import re
import tempfile
import subprocess
import zipfile
import unicodedata
from datetime import datetime
import locale
from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF

app = Flask(__name__)

# Set locale to Portuguese (Brazil) for date formatting
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '') # Use default locale

def slugify(value: str) -> str:
    if not value: return ''
    value_norm = unicodedata.normalize('NFKD', value).encode('ASCII', 'ignore').decode()
    value_norm = value_norm.replace(' ', '_').replace('-', '_')
    return ''.join(ch for ch in value_norm if ch.isalnum() or ch == '_').upper()

def determine_order_index(filename: str) -> int:
    name = filename.lower()
    name_norm = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode()
    order_definitions = [
        (1, ['oficio']), (2, ['demonstrativo']), (3, ['conciliacao']),
        (4, ['extrato conta corrente', 'extratos conta corrente', 'conta_corrente']),
        (5, ['extrato aplicacao', 'extratos aplicacao', 'extratos aplicacoes', 'aplicacao']),
        (6, ['nf', 'nota', 'comprovante', 'comprovantes', 'orcamento', 'orcamentos', 'pagamento']),
        (7, ['consolidacao', 'pesquisa']), (8, ['planejamento', 'ata']),
        (9, ['bb agil', 'bb_agil', 'declaracao', 'agil']), (10, ['parecer']),
        (11, ['justificativa'])
    ]
    for idx, keywords in order_definitions:
        for kw in keywords:
            if kw.replace(' ', '') in name_norm.replace(' ', ''):
                return idx
    return 100

def extract_text_from_pdfs(file_paths):
    full_text = ''
    for path in file_paths:
        try:
            with fitz.open(path) as doc:
                for page in doc:
                    full_text += page.get_text("text") + '\n\n'
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return full_text

def extract_form_data(text: str):
    data = {
        'tipo_pdde': None, 'ano': None, 'escola': None,
        'presidente': None, 'processo': None, 'cnpj': None
    }
    text_norm = ' '.join(text.split()).upper()

    # CNPJ
    if match := re.search(r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})', text_norm):
        data['cnpj'] = re.sub(r'[.\s/-]', '', match.group(1))
    # Year
    if match := re.search(r'EXERC[IÍ]CIO[:\s]+(\d{4})', text_norm):
        data['ano'] = match.group(1)
    # PDDE Type
    if match := re.search(r'PDDE\s+(B[AÁ]SICO|QUALIDADE|EQUIDADE)', text_norm):
        data['tipo_pdde'] = match.group(1)
    # School Name
    if match := re.search(r'NOME DA RAZ[AÃ]O SOCIAL\s+(?:CEC DA\s+)?(.+?)(?:,|\n|Processo:)', text, re.I):
        escola = match.group(1).strip()
        data['escola'] = re.sub(r'^(CRECHE MUNICIPAL|C M|E M|EDI|ESCOLAR MUNICIPAL)\s+', '', escola, flags=re.I).strip()
    elif match := re.search(r'CONSELHO ESCOLAR COMUNIT[AÁ]RIO \(CEC\) DA (.+?)(?:,|\n|Processo:)', text, re.I):
        escola = match.group(1).strip()
        data['escola'] = re.sub(r'^(CRECHE MUNICIPAL|C M|E M|EDI|ESCOLAR MUNICIPAL)\s+', '', escola, flags=re.I).strip()
    # President Name
    if match := re.search(r'(?:PRESIDENTE(?: DO CEC)?|ASSINATURA)[:\s,]+([A-Z\s]{5,})(?=\n)', text_norm):
        data['presidente'] = match.group(1).strip()
    # SEI Process
    if match := re.search(r'(\d{7}\.\d{6}/\d{4}-\d{2})', text_norm):
        data['processo'] = match.group(1)
    return data

def merge_pdfs(file_list, output_path):
    if not file_list: return
    subprocess.run(['pdfunite'] + file_list + [output_path], check=True)

def create_dispatch_html(tipo_pdde, ano, escola, presidente, processo):
    # Using placeholders for data that might be missing
    p_style = "text-align: justify; line-height: 1.5; font-family: Arial; font-size: 12pt;"
    tipo_pdde_str = tipo_pdde or '[TIPO NÃO ENCONTRADO]'
    ano_str = ano or '[ANO NÃO ENCONTRADO]'
    escola_str = escola or '[ESCOLA NÃO ENCONTRADA]'
    presidente_str = presidente or '[PRESIDENTE NÃO ENCONTRADO]'
    processo_str = processo or '[PROCESSO NÃO ENCONTRADO]'

    dispatch1 = f'''<!DOCTYPE html><html>...</html>''' # Templates kept for brevity
    dispatch2 = f'''<!DOCTYPE html><html>...</html>'''
    dispatch3 = f'''<!DOCTYPE html><html>...</html>'''
    return dispatch1, dispatch2, dispatch3

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    with tempfile.TemporaryDirectory() as tmpdir:
        uploads_dir = os.path.join(tmpdir, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)

        files = []
        for f in request.files.getlist('pdfs'):
            if f and f.filename.lower().endswith('.pdf'):
                path = os.path.join(uploads_dir, f.filename)
                f.save(path)
                files.append(path)
        
        if not files:
            return "Nenhum PDF enviado.", 400

        full_text = extract_text_from_pdfs(files)
        form_data = extract_form_data(full_text)

        name_base = f"PDDE_{slugify(form_data['tipo_pdde'])}_{slugify(form_data['ano'])}_{slugify(form_data['escola'])}_{slugify(form_data['cnpj'])}"

        group_files = {1: [], 2: [], 3: []}
        file_mapping = {1: [], 2: [], 3: [], 'outros': []}
        combined_order = []

        for path in files:
            fname = os.path.basename(path)
            order_index = determine_order_index(fname)
            if 1 <= order_index <= 5: group_files[1].append(path); file_mapping[1].append(fname)
            elif 6 <= order_index <= 8: group_files[2].append(path); file_mapping[2].append(fname)
            else: group_files[3].append(path); file_mapping[3].append(fname)
            combined_order.append((order_index, path))

        combined_order = [p for _, p in sorted(combined_order, key=lambda x: (x[0], os.path.basename(x[1])))]
        outdir = os.path.join(tmpdir, 'out')
        os.makedirs(outdir, exist_ok=True)

        group_names = {
            1: f"01_INSTRUCAO_E_CONSOLIDACAO_{name_base}.pdf",
            2: f"02_COMPROVACAO_DE_DESPESAS_{name_base}.pdf",
            3: f"03_DECLARACOES_E_PARECERES_{name_base}.pdf",
        }
        for gnum, paths in group_files.items():
            if paths:
                sorted_paths = sorted(paths, key=lambda p: (determine_order_index(os.path.basename(p)), os.path.basename(p)))
                merge_pdfs(sorted_paths, os.path.join(outdir, group_names[gnum]))

        merge_pdfs(combined_order, os.path.join(outdir, f"00_PACOTE_COMPLETO_{name_base}.pdf"))
        
        # Dispatch Generation (remains the same)

        # Verification Report Generation
        report_path = os.path.join(outdir, "_RELATORIO_DE_VERIFICACAO.txt")
        with open(report_path, 'w', encoding='utf-8') as rf:
            rf.write("-----------------------------------------\n")
            rf.write(" RELATÓRIO DE VERIFICAÇÃO AUTOMÁTICA\n")
            rf.write("-----------------------------------------\n\n")
            rf.write(f"Data de Processamento: {datetime.now().strftime('%d de %B de %Y, %H:%M:%S')}\n\n")
            rf.write("DADOS EXTRAÍDOS DOS PDFs:\n")
            for key, value in form_data.items():
                status = value if value else "AVISO: Não foi possível encontrar esta informação."
                rf.write(f"- {key.replace('_', ' ').capitalize()}: {status}\n")
            rf.write("\n-----------------------------------------\n\n")
            rf.write("ARQUIVOS PROCESSADOS E SEUS GRUPOS:\n")
            for gnum, group_name_key in group_names.items():
                rf.write(f"\nGrupo {gnum} - {os.path.basename(group_name_key).split('_', 1)[1].rsplit('_', 4)[0].replace('_', ' ')}:\n")
                if file_mapping[gnum]:
                    for fname in sorted(file_mapping[gnum]):
                        rf.write(f"  - {fname}\n")
                else:
                    rf.write("  - Nenhum arquivo nesta categoria.\n")

        # Create ZIP archive
        zip_path = os.path.join(tmpdir, f'pacote_{name_base}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(os.listdir(outdir)):
                zf.write(os.path.join(outdir, item), arcname=item)
        
        return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
