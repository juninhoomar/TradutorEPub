
# Tradutor DOCX AI

Uma aplicação web simples para traduzir documentos `.docx` mantendo a formatação original, utilizando IA (Gemini/OpenRouter).

## Como Executar Localmente

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure as variáveis de ambiente em `.env`:
   ```
   OPENROUTER_API_KEY=sua_chave_aqui
   MODEL_NAME=google/gemini-2.0-flash-001
   ```

3. Execute o servidor:
   ```bash
   python web_app.py
   ```

4. Acesse `http://localhost:5000`.

## Deploy no Coolify (ou Docker)

Para garantir que os arquivos traduzidos e o histórico de tarefas sejam mantidos mesmo após reinicializações do servidor, é **essencial** configurar volumes persistentes.

### Volumes Necessários

Configure os seguintes volumes no seu serviço Coolify/Docker:

1. **/app/translated**: Para armazenar os arquivos traduzidos.
2. **/app/tasks.json**: Para persistir o status das tarefas (opcional, mas recomendado). 
   * Nota: Como `tasks.json` é um arquivo, você pode mapear o diretório pai `/app` se preferir, ou apenas garantir que o arquivo não seja sobrescrito se mapear como arquivo único.
   * **Recomendação**: Mapeie um volume para `/app/data` e altere o código para salvar o `tasks.json` lá, ou simplesmente mapeie `/app/translated` que é o mais crítico. O sistema foi atualizado para recuperar o download se o arquivo existir em `/app/translated`, mesmo se o `tasks.json` for perdido.

### Configuração Recomendada

No Coolify, adicione um Volume Persistente:
- **Mount Path**: `/app/translated`

Isso garantirá que seus arquivos traduzidos não sejam perdidos quando você fizer um novo deploy ou reiniciar o serviço.
