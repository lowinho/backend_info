## 🧠 Backend – API de Análise de Pedidos com Dados Pessoais

O backend é responsável por **processar, analisar e classificar pedidos** (texto ou arquivos) com base na presença de **dados pessoais e sensíveis**, conforme os princípios da **LGPD** e os critérios definidos pela **CGDF**.

Toda a API foi desenvolvida para fins de automatização que permitem a  identificação de pedidos que podem ou não serem classificados como **público**.

## ⚙️ Backend – Instruções de Instalação e Dependências

Esta seção descreve os **pré-requisitos**, **dependências** e o processo necessário para executar o backend da solução de análise de pedidos contendo dados pessoais ou sensíveis.

### 1.1 Pré-requisitos

Antes de iniciar a aplicação, certifique-se de que os seguintes softwares estejam instalados no ambiente:

- **Python 3.9 ou superior**
- **pip** (gerenciador de pacotes do Python)
- **MongoDB** (local ou remoto)  
  - Utilizado para armazenamento dos relatórios de análise
- **Git** (opcional, para clonagem do repositório)

> ℹ️ Recomenda-se o uso de um ambiente virtual (`venv`) para evitar conflitos entre dependências.

---

```bash
# Clone o Repositório
git clone git@github.com:lowinho/backend_info.git
```

### 1.2 Instalação das Dependências

O backend utiliza o arquivo `requirements.txt` para gerenciar todas as bibliotecas necessárias, permitindo a **instalação automatizada** do ambiente.

#### Passo 1 – Criar e ativar o ambiente virtual (opcional, recomendado)

```bash
python -m venv venv
```

Ativar no Linux/Mac:

```bash
source venv/bin/activate
```

Ativar no Windows:

```bash
venv\Scripts\activate
```
#### Passo 2 – Instalar as dependências
```bash
pip install -r requirements.txt
```
#### 1.3 Principais Dependências Utilizadas

As bibliotecas abaixo são utilizadas no backend, organizadas por finalidade:

🌐 Framework da API

* **Flask** – Framework web principal da API

* **flask-cors** – Habilita comunicação entre frontend e backend

* **python-dotenv** – Gerenciamento de variáveis de ambiente

📊 Processamento de Dados

* **pandas** – Leitura e manipulação de dados estruturados

* **openpyxl** – Suporte a arquivos Excel (.xlsx)

🧠 Detecção de Dados Pessoais (NLP)

* **spaCy** – Processamento de linguagem natural para identificação de PII

* **phonenumbers** – Validação e detecção de números telefônicos

🗄️ Banco de Dados

* **pymongo** – Integração com MongoDB

🔐 Segurança e Utilidades

* **cryptography** – Suporte a práticas de segurança e criptografia

* **werkzeug** – Utilitários internos do Flask

* **python-multipart** – Upload de arquivos via formulário

## 🔧 Backend — Instruções de Execução

Esta seção descreve como executar o processador Standalone de Detecção de Dados Pessoais (PII), bem como o formato de entrada e saída dos dados analisados.

### 2. Instruções de Execução
**a) Comandos para Execução**

Após instalar todas as dependências e garantir que o ambiente esteja configurado corretamente, execute o script principal com o comando abaixo:
```bash
python main.py
```

**📌 Observação:**
O script foi desenvolvido para execução standalone, sem necessidade de parâmetros via linha de comando.
O arquivo de entrada é configurado diretamente no código pela variável:
```bash
FILE_NAME = './files/AMOSTRA_e-SIC.xlsx'
```

#### Caso deseje analisar outro arquivo, basta alterar esse caminho.

**b) Formato dos Dados de Entrada e Saída
📥**

### Formato de Entrada

O sistema aceita arquivos nos seguintes formatos:

* **.xlsx (Excel)**

* **.csv**

Requisitos do arquivo:

Deve conter ao menos uma coluna de texto livre, onde serão analisados os possíveis dados pessoais.

Preferencialmente, a coluna deve conter no nome algo semelhante a:

**Texto Mascarado**

Caso não exista uma coluna com esse nome, o sistema tentará identificar automaticamente a coluna de texto mais longa.

Opcionalmente, o arquivo pode conter uma coluna de identificação do registro, como:

**ID, Id, id, Protocolo, protocolo**

📁 Exemplo de estrutura esperada:
```bash
# Exemplo de csv
Protocolo	Texto Mascarado
12345	Solicito informações sobre João Silva, CPF 000.000.000-00...
```
### 📤 Formato de Saída

A saída do processamento ocorre via terminal, por meio de um dashboard textual, contendo:

* 📊 Quantidade total de registros analisados

* ⚠️ Quantidade de registros com dados pessoais identificados

* 📈 Taxa de incidência de PII

* ⏱️ Tempo total de processamento

* 🔍 Detalhamento por tipo de dado pessoal detectado, incluindo:

* CPF

* CNPJ

* Telefones

* E-mails

* Endereços

* Registros Gerais (RG, CNH, NIS, PIS, etc.)

* Dados sensíveis (saúde, menor de idade, raça, gênero, contexto social)

Além disso, o sistema realiza uma classificação automática de risco LGPD, podendo indicar:

**BAIXO**

**ALTO**

**CRÍTICO**

Com base na presença de dados sensíveis ou identificadores oficiais em massa.