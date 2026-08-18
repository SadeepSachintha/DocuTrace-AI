# DocuTrace AI - User Manual

Welcome to **DocuTrace AI**, a state-of-the-art multilingual corporate document search and question-answering assistant, built and designed by **[SS Labz](https://ss-labz.pages.dev/)**.

DocuTrace AI utilizes hybrid semantic retrieval, layout table parsing, query translation, parent-child document chunking, and conversational chat history memory to extract grounded answers from corporate policy documents in multiple languages (English, Sinhala, Tamil).

---

## 1. Getting Started

### Accessing the Dashboard
1. Ensure the database container and FastAPI server are running.
2. Open your web browser and navigate to:
   👉 **[http://localhost:8008/](http://localhost:8008/)**
3. You will be greeted by the dark-mode glassmorphic dashboard interface.

---

## 2. Ingesting Corporate Policies

To ask questions about a policy, you must first ingest the document into the system.

1. **Select a File**:
   - Drag and drop any corporate PDF policy document directly into the dotted upload area in the left sidebar.
   - Alternatively, click on the upload area to open your local file browser and choose a PDF.
2. **Assign Department Tag**:
   - Select the target department context (e.g. *Human Resources*, *Finance*, *Operations*, or *Security*) from the dropdown list.
   - This tag acts as a retrieval boundary, ensuring queries only search relevant departmental documents.
3. **Trigger Ingestion**:
   - Click the **"Upload Policy"** button.
   - Monitor the progress box in the sidebar:
     - **Processing**: The system splits text page-by-page, extracts tables, and calculates dense E5 vector embeddings.
     - **Complete**: A green checkmark confirms indexing success.
     - **De-duplication**: If an identical document has already been ingested, a blue checkmark states `Re-used existing index`, saving time and compute resources.

---

## 3. Querying & Conversational Memory

DocuTrace AI allows you to query policy databases using natural conversational language and hold ongoing multi-turn conversations.

1. **Ask Initial Question**:
   - Type your question in the chat input box at the bottom-right (e.g. `"What is the annual leave carryover policy?"`).
   - The assistant returns the grounded answer with source citations.
2. **Ask Follow-up Questions**:
   - You can ask follow-up questions referencing previous answers without repeating context (e.g. `"How do I request an exception to it?"` or `"Is there a limit on this?"`).
   - The assistant automatically merges your previous chat history and the new question using the LLM to generate a standalone query before executing database retrieval.
3. **Start a New Chat**:
   - Click the **"New Chat"** button inside the header bar next to the badges.
   - This resets your thread ID (`session_id = null`) and clears the message log, allowing you to start a fresh topic.

---

## 4. Viewing Citations

To ensure transparency and absolute truthfulness, DocuTrace AI includes an interactive citations panel:

1. Locate the **"Show Citations (N)"** button directly underneath the assistant's chat bubble response.
2. Click the button to expand the source card list.
3. For each source card, you can view:
   - **Document Info**: Source filename and page number.
   - **Relevance Score**: The computed Cross-Encoder score (or RRF score) indicating exact contextual match alignment.
   - **Exact Matching Snippet**: The precise child chunk segment where the keyword/concept matched.

---

## 5. Troubleshooting & FAQ

* **The upload progress is stuck**: Make sure your file is a valid PDF and the backend container is running. Large files may take slightly longer as the system downloads/runs transformer modules.
* **Why does the answer start with "[MOCK Grounded Response]"?**: This means the OpenAI API Key in your environment is set to mock. The system will retrieve correct documents and print their summaries, but placeholder LLM answers are generated.
* **Are scanned pages supported?**: Yes! Pages with zero characters containing graphics or images are automatically labeled with scanned layout tags so they are searchable.
* **How are tables handled?**: Tables are parsed into standard Markdown formats, preserving column-row relationships so calculations/reconciliations in sheets are preserved.

---

## About SS Labz

**DocuTrace AI** is proudly developed by **[SS Labz](https://ss-labz.pages.dev/)**, dedicated to creating intelligent, localized enterprise solutions. Visit our website at [https://ss-labz.pages.dev/](https://ss-labz.pages.dev/) to discover more systems and products.
