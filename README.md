## 🧠 Backend – API de Análise de Pedidos com Dados Pessoais

O backend é responsável por **processar, analisar e classificar pedidos** (texto ou arquivos) com base na presença de **dados pessoais e sensíveis**, conforme os princípios da **LGPD** e os critérios definidos pela **CGDF**.

Toda a API foi desenvolvida para fins de automatização que permitem a  identificação de pedidos que podem ou não serem classificados como **público**.

## ⚙️ Backend – Instruções de Instalação e Dependências

Esta seção descreve os **pré-requisitos**, **dependências** e o processo necessário para executar o backend da solução de análise de pedidos contendo dados pessoais ou sensíveis.

### Pré-requisitos

Antes de iniciar a aplicação, certifique-se de que os seguintes softwares estejam instalados no ambiente:

- **Python 3.9 ou superior**
- **pip** (gerenciador de pacotes do Python)
- **MongoDB** (local ou remoto)  
  - Utilizado para armazenamento dos relatórios de análise
- **Git** (opcional, para clonagem do repositório)

## 📥 Início Rápido

### 1. Clone o Repositório
```bash
git clone git@github.com:lowinho/backend_info.git
```
### Entre na pasta do projeto
```bash
cd backend_info
```
## Execução via Docker (Docker Compose)

**Pré-requisitos**

Comando para Executar
Abra o seu terminal na pasta do projeto e execute o seguinte comando:
```bash
docker compose up --build
```
O que este comando faz:

* **--build:** Força o Docker a construir a imagem da sua API usando o Dockerfile (instala dependências, baixa o modelo do SpaCy, etc).

* **up:** Sobe os containers do MongoDB e da API conectando-os na rede lgpd_network.

Nota: Na primeira vez, isso pode demorar alguns minutos pois ele precisará baixar as imagens base e instalar as bibliotecas do Python.

## 🚀 Execução via Terminal (VENV)
O projeto utiliza um arquivo **requirements.txt** para gerenciar todas as dependências, garantindo que o ambiente de execução seja idêntico ao de desenvolvimento.

* Criar e ativar o ambiente virtual (Recomendado)
O uso de um ambiente virtual (VENV) evita conflitos entre as bibliotecas do seu sistema e as do projeto.

### Criar o ambiente (Universal):
```bash
python -m venv venv
```
### Ativar o ambiente:
* No Linux / Mac:
```bash
source venv/bin/activate
```
* No Windows:
```bash
.\venv\Scripts\activate
```
### 2. Instalar as dependências
Com o ambiente devidamente ativo, instale os pacotes necessários:
```bash
pip install -r requirements.txt
```

### 3. Baixar o modelo de IA (Processamento de Nomes)
**ESTA ETAPA É OBRIGATÓRIA.** O sistema utiliza Processamento de Linguagem Natural (NLP) para identificar nomes próprios. Para isso, é necessário baixar o modelo treinado do SpaCy:
```bash
python -m spacy download pt_core_news_lg
```
**Nota:** Caso o comando acima falhe devido a restrições de rede ou firewall, instale diretamente via URL:
```bash
pip install https://github.com/explosion/spacy-models/releases/download/pt_core_news_lg-3.7.0/pt_core_news_lg-3.7.0-py3-none-any.whl
```
### 4. Rodar o Projeto
Após a configuração, você pode executar os scripts principais de acordo com a sua necessidade:


📍 Observação Importante: Por padrão, o script está configurado para ler o arquivo no caminho:
```bash
./files/AMOSTRA_e-SIC.xlsx.
```
Caso queira testar um arquivo diferente, você tem duas opções:

* Colocar o seu arquivo na pasta ./files/ com o nome AMOSTRA_e-SIC.xlsx.

* Abrir o arquivo report.py e alterar a variável FILE_NAME para o caminho do seu novo arquivo.
### Para análise Standalone (Terminal):
```bash
# Entre na pasta report
cd report
# Execute o script
python report.py
```
* **Para iniciar o servidor da API (Backend):**
```bash
python app.py
```
### 5. Principais Dependências Utilizadas

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


### 6. Formato dos Dados de Entrada e Saída 📥

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