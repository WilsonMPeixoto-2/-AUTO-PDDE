#!/usr/bin/env python3
"""
Simple PDDE web application.

This Flask application allows the user to upload multiple PDF files and provide
basic information (tipo de PDDE, ano, escola, presidente, processo) via a web
form. It will classify and reorder the uploaded PDFs according to predefined
rules, merge them into a single combined PDF as well as separate grouped PDFs,
generate DOCX dispatches with formatted text, and return a ZIP archive
containing all generated files.

Dependencies:
 - Flask (`pip install flask`)
 - Pandoc and pdfunite must be available in the system path.

Usage:
    python app.py

After running, open http://localhost:5000/ in a browser to use the app.
"""
import os
import tempfile
import subprocess
import zipfile
import unicodedata
from flask import Flask, render_template, request, send_file

app = Flask(__name__)


def slugify(value: str) -> str:
    """Normalize string to a filesystem-friendly slug (uppercase, no spaces)."""
    value_norm = unicodedata.normalize('NFKD', value).encode('ASCII', 'ignore').decode()
    value_norm = value_norm.replace(' ', '_').replace('-', '_')
    return ''.join(ch for ch in value_norm if ch.isalnum() or ch == '_').upper()


def determine_order_index(filename: str) -> int:
    """
    Determine an ordering index for a given PDF filename based on common categories
    to reflect the official chronological order shown in SEI. Lower index means earlier in the sequence.
    Categories not matched will be given a high index (100) so they appear last.
    """
    name = filename.lower()
    name_norm = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode()
    order_definitions = [
        (1, ['oficio']),
        (2, ['demonstrativo']),
        (3, ['conciliacao']),
        (4, ['extrato conta corrente', 'extratos conta corrente', 'conta_corrente']),
        (5, ['extrato aplicacao', 'extratos aplicacao', 'extratos aplicacoes', 'aplicacao']),
        (6, ['nf', 'nota', 'comprovante', 'comprovantes', 'orcamento', 'orcamentos', 'pagamento']),
        (7, ['consolidacao', 'pesquisa']),
        (8, ['planejamento', 'ata']),
        (9, ['bb agil', 'bb_agil', 'declaracao', 'agil']),
        (10, ['parecer']),
    ]
    for idx, keywords in order_definitions:
        for kw in keywords:
            if kw.replace(' ', '') in name_norm.replace(' ', ''):
                return idx
    return 100


def merge_pdfs(file_list, output_path):
    """Merge a list of PDFs into a single PDF using pdfunite."""
    if not file_list:
        return
    cmd = ['pdfunite'] + file_list + [output_path]
    subprocess.run(cmd, check=True)


def create_dispatch_html(tipo_pdde, ano, escola, presidente, processo):
    """
    Generate HTML strings for the three dispatches based on the provided information.
    The HTML uses inline CSS for justification, line spacing, and bolding key information.
    """
    # Common style for paragraphs
    p_style = "text-align: justify; line-height: 1.5; font-family: Arial; font-size: 12pt;"

    # Dispatch 1
    dispatch1 = f"""
<!DOCTYPE html>
<html><body>
<p style="{p_style}">
À Gerência de Administração – E/CRE04/GAD,<br/><br/>
Encaminho a presente prestação de contas e declaro, para os devidos fins, a autenticidade dos documentos anexados.<br/><br/>
Rio de Janeiro, {{DATA_POR_EXTENSO}}.
</p>
</body></html>"""

    # Dispatch 2
    dispatch2 = f"""
<!DOCTYPE html>
<html><body>
<p style="{p_style}">
À Srª COORDENADORA DA 4ª CRE,<br/><br/>
Após análise da documentação apresentada, informo que a prestação de contas referente ao Programa Dinheiro Direto na Escola – PDDE <strong>{tipo_pdde}/{ano}</strong>, vinculada ao Conselho Escolar Comunitário (CEC) da <strong>{escola}</strong>, sob a presidência de <strong>{presidente}</strong>, encontra-se em <strong>condições de aprovação</strong>, por atender às normatizações e orientações vigentes do Fundo Nacional de Desenvolvimento da Educação – FNDE, aplicáveis à matéria.<br/><br/>
Rio de Janeiro, {{DATA_POR_EXTENSO}}.
</p>
<p style="font-family: Arial; font-size: 12pt;">
<strong>BIANCA BARRETO DA FONSECA COELHO</strong><br/>
<strong>Gerente II</strong><br/>
<strong>Matrícula: 1993567</strong>
</p>
</body></html>"""

    # Dispatch 3
    dispatch3 = f"""
<!DOCTYPE html>
<html><body>
<p style="{p_style}">
<strong>PUBLIQUE-SE.</strong><br/><br/>
Processo: {processo}<br/><br/>
Aprovo a prestação de contas referente ao Programa Dinheiro Direto na Escola – PDDE <strong>{tipo_pdde}/{ano}</strong>, do Conselho Escolar Comunitário (CEC) da <strong>{escola}</strong>, sob a presidência de <strong>{presidente}</strong>.<br/><br/>
Rio de Janeiro, {{DATA_POR_EXTENSO}}.
</p>
<p style="font-family: Arial; font-size: 12pt;">
<strong>FATIMA DAS GRACAS LIMA BARROS</strong><br/>
<strong>COORDENADOR I</strong><br/>
<strong>Matrícula: 2025591</strong><br/>
<strong>E/4a.CRE</strong>
</p>
</body></html>"""

    return dispatch1, dispatch2, dispatch3


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process():
    # Retrieve form fields
    tipo_pdde = request.form.get('tipo_pdde', 'BASICO').upper().strip()
    ano = request.form.get('ano', '2025').strip()
    escola = request.form.get('escola', 'UNDEFINED').strip()
    presidente = request.form.get('presidente', 'NOME PRESIDENTE').strip()
    processo = request.form.get('processo', '').strip()
    # Normalize names for file naming
    name_base = f"PDDE_{slugify(tipo_pdde)}_{slugify(ano)}_{slugify(escola)}"

    # Create a temporary directory to work in
    with tempfile.TemporaryDirectory() as tmpdir:
        uploads_dir = os.path.join(tmpdir, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)

        # Save uploaded files
        files = []
        for f in request.files.getlist('pdfs'):
            if f and f.filename.lower().endswith('.pdf'):
                path = os.path.join(uploads_dir, f.filename)
                f.save(path)
                files.append(path)

        if not files:
            return "Nenhum PDF enviado.", 400

        # Classify files into groups and assign order
        group_files = {1: [], 2: [], 3: [], 4: []}
        combined_order = []
        for path in files:
            fname = os.path.basename(path)
            # Classification (reuse determine_order_index for ordering but group separately)
            # Use simple heuristics as in pdde_app_basic
            lower = fname.lower()
            if 'oficio' in lower or 'justificativa' in lower:
                group_files[1].append(path)
            elif any(k in lower for k in ['nf', 'nota', 'orcamento', 'pagamento', 'comprovante']):
                group_files[2].append(path)
            elif any(k in lower for k in ['extrato', 'extratos', 'conciliacao', 'bb', 'aplicacao']):
                group_files[3].append(path)
            else:
                group_files[4].append(path)
            # Combined order list with index
            combined_order.append((determine_order_index(fname), path))

        # Sort combined order
        combined_order = [p for _, p in sorted(combined_order, key=lambda x: (x[0], os.path.basename(x[1])))]

        # Output directory
        outdir = os.path.join(tmpdir, 'out')
        os.makedirs(outdir, exist_ok=True)

        # Merge PDFs by group and combined order
        # Group names
        group_names = {
            1: f"01_PECAS_INSTRUCAO_{name_base}.pdf",
            2: f"02_COMPROVACAO_DESPESA_{name_base}.pdf",
            3: f"03_EXTRATOS_CONCILIACAO_{name_base}.pdf",
            4: f"04_ATAS_RELATORIOS_CEC_{name_base}.pdf",
        }
        for gnum, paths in group_files.items():
            if paths:
                # Sort within group using order index
                sorted_paths = sorted(paths, key=lambda p: (determine_order_index(os.path.basename(p)), os.path.basename(p)))
                merge_pdfs(sorted_paths, os.path.join(outdir, group_names[gnum]))

        # Combined file
        combined_name = f"00_PACOTE_COMPLETO_{name_base}.pdf"
        merge_pdfs(combined_order, os.path.join(outdir, combined_name))

        # Generate dispatches in DOCX format using Pandoc
        dispatch1_html, dispatch2_html, dispatch3_html = create_dispatch_html(tipo_pdde, ano, escola, presidente, processo)
        # Date replacement (use current date in extended form)
        from datetime import datetime
        data_por_extenso = datetime.now().strftime("%d de %B de %Y")
        dispatch1_html = dispatch1_html.replace("{{DATA_POR_EXTENSO}}", data_por_extenso)
        dispatch2_html = dispatch2_html.replace("{{DATA_POR_EXTENSO}}", data_por_extenso)
        dispatch3_html = dispatch3_html.replace("{{DATA_POR_EXTENSO}}", data_por_extenso)
        # Write HTML to temp files
        html_paths = []
        for i, html in enumerate([dispatch1_html, dispatch2_html, dispatch3_html], start=1):
            html_path = os.path.join(tmpdir, f'despacho_{i}.html')
            with open(html_path, 'w', encoding='utf-8') as hf:
                hf.write(html)
            docx_path = os.path.join(outdir, f'despacho_{i}_{name_base}.docx')
            # Convert to DOCX via pandoc
            subprocess.run(['pandoc', html_path, '-f', 'html', '-t', 'docx', '-o', docx_path], check=True)
            html_paths.append(html_path)

        # Create ZIP archive
        zip_path = os.path.join(tmpdir, f'pacote_{name_base}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add PDFs
            for pdf in os.listdir(outdir):
                zf.write(os.path.join(outdir, pdf), arcname=pdf)
        # Return the ZIP file
        return send_file(zip_path, as_attachment=True, download_name=os.path.basename(zip_path))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)