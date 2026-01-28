## 🧠 Backend – API de Análise de Pedidos com Dados Pessoais

O backend é responsável por **processar, analisar e classificar pedidos** (texto ou arquivos) com base na presença de **dados pessoais e sensíveis**, conforme os princípios da **LGPD** e os critérios definidos pela **CGDF**.

Toda a API foi desenvolvida para fins de automatização que permitem a  identificação de pedidos que podem ou não serem classificados como **público**.

## 🚀 Como Executar o Projeto

Você pode rodar o backend de duas formas: utilizando via **VENV** (Ambiente virtual Python) ou **DOCKER** (que já configura o banco de dados e a IA automaticamente - Para visualização com **frontend**).

---
### Opção 1 Execução via Terminal (VENV)
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

* Abrir o arquivo report.py na pasta report/ e alterar a variável FILE_NAME para o caminho do seu novo arquivo.
### Para análise Standalone (Terminal):
```bash
# Entre na pasta report
cd report
# Execute o script
python report.py
```
### 5. Formato dos Dados de Entrada e Saída 📥

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

### Opção 2: Via Docker (Recomendado para Integração com Frontend 🐳)


---

Esta opção utiliza **Docker Compose** para orquestrar a API Flask e o banco de dados MongoDB, permitindo que o Frontend se comunique perfeitamente com o backend.

**Pré-requisitos:** Docker e Docker Compose instalados.

1.  **Subir o ambiente:**
    Na pasta raiz do projeto, execute:
    ```bash
    docker compose up --build
    ```

2.  **Serviços Iniciados:**
    * **API Flask:** Rodando em `http://localhost:5000`
    * **MongoDB:** Rodando na porta `27017`
    * **Volumes:** Os dados do banco são persistidos em `mongodb_data` e os arquivos enviados ficam na pasta `./uploads`.

3.  **Destaques da Configuração Docker:**
    * **Multi-stage Build:** A imagem final é otimizada e leve, contendo apenas o necessário para a execução.
    * **Auto-Healthcheck:** O container da API possui verificação automática de integridade.
    * **Segurança:** A aplicação roda com um usuário não-root (`appuser`), seguindo boas práticas de segurança.
    * **Hot Reload:** O volume montado em `.:/app` permite que alterações no código sejam refletidas em tempo real (em modo debug).

E para visualização **(FRONTEND)** basta seguir as intruções do repositório abaixo:

**[Repositório do Frontend](https://github.com/lowinho/frontend_info)**

### Principais Dependências Utilizadas

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