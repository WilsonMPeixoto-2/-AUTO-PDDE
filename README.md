# AUTO-PDDE: Otimizador de Prestação de Contas

Esta é uma aplicação web desenvolvida para automatizar e otimizar o processo de prestação de contas do programa PDDE (Programa Dinheiro Direto na Escola) para a 4ª Coordenadoria Regional de Educação (CRE).

A ferramenta permite o upload de múltiplos arquivos PDF (como notas fiscais, extratos, ofícios, etc.), os classifica, extrai informações chave, gera documentos de despacho e, por fim, entrega um pacote `.zip` completo e organizado, pronto para ser inserido em sistemas como o SEI.

## Funcionalidades Principais

- **Upload em Massa:** Arraste e solte ou selecione múltiplos arquivos PDF de uma só vez.
- **Extração Automática de Dados:** A aplicação lê os PDFs e extrai informações essenciais como tipo do PDDE, ano, nome da escola, CNPJ e presidente do CEC usando expressões regulares.
- **Classificação e Agrupamento:** Os arquivos são automaticamente categorizados e agrupados em PDFs consolidados (Instrução, Comprovação de Despesas, etc.).
- **Geração de Documentos:** Cria automaticamente os ofícios de encaminhamento e despachos de análise e aprovação em formato `.docx`.
- **Pacote Final Organizado:** Todos os arquivos gerados, incluindo os PDFs agrupados e os documentos `.docx`, são compactados em um único arquivo `.zip` nomeado de forma padronizada.

## Como Executar Localmente

Para executar a aplicação em sua máquina local, siga os passos abaixo.

### Pré-requisitos

Você precisa ter as seguintes ferramentas de linha de comando instaladas em seu sistema:

- **Python 3.10+**
- **Pandoc:** Para a conversão de HTML para `.docx`.
- **Poppler-utils:** Que inclui a ferramenta `pdfunite` para mesclar PDFs.

Em um sistema baseado em Debian/Ubuntu, você pode instalar o Pandoc e o Poppler com:

```bash
sudo apt-get update
sudo apt-get install pandoc poppler-utils
```

### Passos para Execução

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/WilsonMPeixoto-2/-AUTO-PDDE.git
    cd -AUTO-PDDE
    ```

2.  **Crie um ambiente virtual e instale as dependências Python:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Inicie a aplicação:**
    ```bash
    gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
    ```

4.  **Acesse a aplicação:**
    Abra seu navegador e acesse [http://localhost:5000](http://localhost:5000).

## Deploy na Nuvem com Render

Este projeto está configurado para um deploy fácil e **gratuito** na plataforma [Render](https://render.com/).

Graças ao arquivo `render.yaml` no repositório, o processo é quase todo automático:

1.  **Crie uma conta gratuita no Render** usando seu perfil do GitHub (não é necessário cartão de crédito).
2.  No painel do Render, clique em **New > Blueprint**.
3.  Conecte seu repositório `WilsonMPeixoto-2/-AUTO-PDDE`.
4.  O Render irá ler o arquivo `render.yaml` e pré-configurar o serviço.
5.  Clique em **Create** e aguarde o processo de build e deploy ser concluído.

A aplicação estará disponível em uma URL pública fornecida pelo Render.
